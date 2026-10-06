import os
import json
import sqlite3
import datetime
import threading
import time
from typing import Dict, Any, List, Optional
from pathlib import Path

from kairos.database import batch_insert_sync_data, register_or_update_device, get_connection
from kairos.engine import engine

# Common StayFree desktop paths on Windows
STAYFREE_STORE_PATH = Path(os.path.expandvars(
    r"%LOCALAPPDATA%\Packages\37081StayFreeApps.StayFree3_fqhk48m1tsma0\LocalCache\Roaming\StayFree"
))
STAYFREE_ROAMING_PATH = Path(os.path.expandvars(r"%APPDATA%\StayFree"))

class StayFreeBridge:
    def __init__(self):
        self._bg_thread = None
        self._stop_event = threading.Event()
        self.auto_sync_enabled = True
        self.sync_interval_seconds = 600  # 10 minutes
        self.last_sync_time = None
        self.last_imported_count = 0

    def find_stayfree_dir(self) -> Optional[Path]:
        """Locates the StayFree directory on Windows."""
        if STAYFREE_STORE_PATH.exists() and (STAYFREE_STORE_PATH / "config.db").exists():
            return STAYFREE_STORE_PATH
        if STAYFREE_ROAMING_PATH.exists() and (STAYFREE_ROAMING_PATH / "config.db").exists():
            return STAYFREE_ROAMING_PATH
        return None

    def get_status(self) -> Dict[str, Any]:
        """Inspects StayFree local databases and returns device group and sync status."""
        sf_dir = self.find_stayfree_dir()
        if not sf_dir:
            return {
                "installed": False,
                "message": "未檢測到本機 StayFree 桌面版安裝路徑",
                "device_group": None,
                "device_count": 0,
                "platforms_found": [],
                "last_sync_time": self.last_sync_time,
                "last_imported_count": self.last_imported_count,
                "auto_sync_enabled": self.auto_sync_enabled
            }

        config_db_path = sf_dir / "config.db"
        device_group = None
        device_count = 0
        platforms = set()
        creators = set()
        cached_count = 0

        try:
            # Use URI with mode=ro to avoid any lock contention with running StayFree app
            conn = sqlite3.connect(f"file:{config_db_path.as_posix()}?mode=ro", uri=True)
            cur = conn.cursor()
            
            cur.execute("SELECT key, value FROM config WHERE key IN ('device-group', 'device-count-in-device-group', 'api-sessions-repo-find-sessions-cache')")
            rows = dict(cur.fetchall())
            conn.close()

            if "device-group" in rows:
                try:
                    dg_data = json.loads(rows["device-group"])
                    device_group = dg_data.get("key")
                except Exception:
                    device_group = rows["device-group"]

            if "device-count-in-device-group" in rows:
                try:
                    device_count = int(rows["device-count-in-device-group"])
                except Exception:
                    device_count = 0

            if "api-sessions-repo-find-sessions-cache" in rows:
                try:
                    cache_json = json.loads(rows["api-sessions-repo-find-sessions-cache"])
                    for batch in cache_json.values():
                        items = batch.get("value", [])
                        cached_count += len(items)
                        for it in items:
                            if "platform" in it:
                                platforms.add(it["platform"])
                            if "createdBy" in it:
                                creators.add(it["createdBy"])
                except Exception:
                    pass

        except Exception as e:
            return {
                "installed": True,
                "error": f"讀取 StayFree 快取時發生異常: {str(e)}",
                "device_group": None,
                "device_count": 0,
                "platforms_found": [],
                "last_sync_time": self.last_sync_time,
                "last_imported_count": self.last_imported_count,
                "auto_sync_enabled": self.auto_sync_enabled
            }

        return {
            "installed": True,
            "path": str(sf_dir),
            "device_group": device_group,
            "device_count": device_count,
            "platforms_found": sorted(list(platforms)),
            "creators_found": sorted(list(creators)),
            "cached_sessions_count": cached_count,
            "last_sync_time": self.last_sync_time,
            "last_imported_count": self.last_imported_count,
            "auto_sync_enabled": self.auto_sync_enabled
        }

    def sync_ipad_sessions(self, target_creators: Optional[List[str]] = None) -> Dict[str, Any]:
        """
        Parses iPad / iOS sessions synced into StayFree desktop SQLite cache,
        categorizes them with Kairos rules engine, and idempotently inserts them into Kairos SQLite.
        """
        sf_dir = self.find_stayfree_dir()
        if not sf_dir:
            return {"success": False, "message": "未檢測到本機 StayFree"}

        config_db_path = sf_dir / "config.db"
        if not config_db_path.exists():
            return {"success": False, "message": "StayFree config.db 不存在"}

        extracted_events = []
        platforms_detected = set()

        try:
            conn = sqlite3.connect(f"file:{config_db_path.as_posix()}?mode=ro", uri=True)
            cur = conn.cursor()
            cur.execute("SELECT value FROM config WHERE key = 'api-sessions-repo-find-sessions-cache'")
            row = cur.fetchone()
            conn.close()

            if not row or not row[0]:
                return {"success": True, "imported_count": 0, "message": "StayFree 尚無遠端裝置同步快取"}

            cache_json = json.loads(row[0])
            for batch in cache_json.values():
                items = batch.get("value", [])
                for it in items:
                    platform = str(it.get("platform", "")).lower()
                    creator = str(it.get("createdBy", ""))
                    platforms_detected.add(platform)

                    # Identification criteria for iPad / iOS:
                    # 1. Platform is explicitly 'ios' or 'ipad' or 'apple'
                    # 2. Or creator matches user-designated target_creators
                    # 3. If target_creators is not specified and platform is 'ios' / 'ipad'
                    is_ipad = False
                    if platform in ("ios", "ipad", "apple"):
                        is_ipad = True
                    elif target_creators and creator in target_creators:
                        is_ipad = True

                    if not is_ipad:
                        continue

                    started_ms = it.get("startedAt")
                    ended_ms = it.get("endedAt")
                    if not started_ms or not ended_ms or ended_ms <= started_ms:
                        continue

                    duration_sec = (ended_ms - started_ms) / 1000.0
                    # Skip unrealistic spikes or under 1 sec
                    if duration_sec < 1.0 or duration_sec > 86400:
                        continue

                    start_dt = datetime.datetime.fromtimestamp(started_ms / 1000.0)
                    date_str = start_dt.strftime("%Y-%m-%d")
                    hour = start_dt.hour
                    app_id = str(it.get("appId", "Unknown")).strip()

                    # Clean app name for readability (e.g. if bundle ID)
                    app_name = app_id
                    if app_name.startswith("com.apple."):
                        app_name = app_name.replace("com.apple.", "").capitalize()
                    elif "." in app_name and len(app_name.split(".")) > 2:
                        # e.g. tw.net.pic.m.openpoint or com.google.chrome
                        parts = app_name.split(".")
                        app_name = parts[-1].capitalize() if parts[-1] else app_name

                    # Run Kairos rules engine to assign category, tags, score
                    match_res = engine.match(app_name, app_id)

                    session_id = it.get("id") or f"{started_ms}_{app_id}"
                    uuid_key = f"stayfree_ipad_{session_id}"

                    extracted_events.append({
                        "date_str": date_str,
                        "hour": hour,
                        "app_name": app_name,
                        "window_title": f"iPad · {app_name}",
                        "duration_sec": duration_sec,
                        "category": match_res["category"],
                        "tags": match_res["tags"] or "ipad,stayfree",
                        "productivity_score": match_res["productivity_score"],
                        "is_idle": False,
                        "client_uuid": uuid_key
                    })

        except Exception as e:
            return {"success": False, "error": f"讀取或解析 StayFree 快取時失敗: {str(e)}"}

        # Register iPad device in Kairos
        register_or_update_device(
            device_id="ipad-stayfree",
            device_name="iPad (StayFree 橋接)",
            device_type="ipad"
        )

        inserted_count = 0
        if extracted_events:
            inserted_count = batch_insert_sync_data(
                device_id="ipad-stayfree",
                device_name="iPad (StayFree 橋接)",
                device_type="ipad",
                events=extracted_events,
                pomodoros=[]
            )

        now_str = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        self.last_sync_time = now_str
        self.last_imported_count = inserted_count

        return {
            "success": True,
            "imported_count": inserted_count,
            "total_scanned_ipad_events": len(extracted_events),
            "platforms_detected": sorted(list(platforms_detected)),
            "sync_time": now_str
        }

    def _sync_loop(self):
        """Periodic background sync loop."""
        while not self._stop_event.is_set():
            # Wait for interval or stop event
            if self._stop_event.wait(self.sync_interval_seconds):
                break
            if self.auto_sync_enabled:
                try:
                    res = self.sync_ipad_sessions()
                    if res.get("imported_count", 0) > 0:
                        print(f"[StayFree Bridge] 自動定時同步成功，匯入 {res['imported_count']} 筆 iPad 使用事件。")
                except Exception as e:
                    print(f"[StayFree Bridge] 自動背景同步發生異常: {e}")

    def start_background_daemon(self):
        """Starts background auto-sync thread."""
        if self._bg_thread and self._bg_thread.is_alive():
            return
        self._stop_event.clear()
        self._bg_thread = threading.Thread(target=self._sync_loop, daemon=True, name="StayFreeBridgeThread")
        self._bg_thread.start()
        print("[StayFree Bridge] 已啟動 StayFree iPad 背景定時橋接守護 (每 10 分鐘自動檢測)...")

    def stop_background_daemon(self):
        """Stops background thread gracefully."""
        self._stop_event.set()
        if self._bg_thread and self._bg_thread.is_alive():
            self._bg_thread.join(timeout=2.0)

# Global singleton
stayfree_bridge = StayFreeBridge()
