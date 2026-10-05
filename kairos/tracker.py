import time
import threading
import ctypes
from ctypes import wintypes
from typing import Dict, Any, Optional
import psutil

from kairos.config import POLL_INTERVAL_SECONDS, IDLE_THRESHOLD_SECONDS
from kairos.database import record_activity
from kairos.engine import engine
from kairos.blocker import blocker
from kairos.pomodoro import pomodoro

user32 = ctypes.windll.user32
kernel32 = ctypes.windll.kernel32

class LASTINPUTINFO(ctypes.Structure):
    _fields_ = [
        ("cbSize", ctypes.c_uint),
        ("dwTime", ctypes.c_uint),
    ]

def get_idle_seconds() -> float:
    try:
        lii = LASTINPUTINFO()
        lii.cbSize = ctypes.sizeof(LASTINPUTINFO)
        if user32.GetLastInputInfo(ctypes.byref(lii)):
            millis = kernel32.GetTickCount() - lii.dwTime
            return max(0.0, millis / 1000.0)
    except Exception:
        pass
    return 0.0

def get_foreground_info() -> Dict[str, Any]:
    hwnd = user32.GetForegroundWindow()
    if not hwnd:
        return {"hwnd": 0, "app_name": "Desktop / Idle", "title": "桌面或系統待命", "pid": 0}

    # Get window title
    length = user32.GetWindowTextLengthW(hwnd)
    title = ""
    if length > 0:
        buff = ctypes.create_unicode_buffer(length + 1)
        user32.GetWindowTextW(hwnd, buff, length + 1)
        title = buff.value

    # Get PID and Process Name
    pid = wintypes.DWORD()
    user32.GetWindowThreadProcessId(hwnd, ctypes.byref(pid))
    app_name = "Unknown"
    if pid.value:
        try:
            p = psutil.Process(pid.value)
            app_name = p.name()
        except (psutil.NoSuchProcess, psutil.AccessDenied):
            app_name = f"Process_{pid.value}"

    return {
        "hwnd": hwnd,
        "app_name": app_name,
        "title": title or app_name,
        "pid": pid.value
    }

class WindowTracker:
    def __init__(self):
        self.running = False
        self._thread: Optional[threading.Thread] = None
        self.current_window = {
            "app_name": "Kairos",
            "title": "初始化中...",
            "category": "System",
            "tags": "kairos",
            "productivity_score": 0,
            "is_idle": False,
            "session_seconds": 0.0,
            "is_over_limit": False
        }
        self._proc_cache: Dict[int, str] = {}

    def start(self):
        if self.running:
            return
        self.running = True
        self._thread = threading.Thread(target=self._loop, daemon=True)
        self._thread.start()

    def stop(self):
        self.running = False

    def _loop(self):
        last_app = ""
        last_title = ""
        session_start = time.time()

        while self.running:
            start_loop = time.time()
            try:
                # 1. Update Pomodoro
                pomodoro.tick(POLL_INTERVAL_SECONDS)

                # 2. Check user idle state
                idle_sec = get_idle_seconds()
                is_idle = idle_sec >= IDLE_THRESHOLD_SECONDS

                # 3. Get foreground window
                fg = get_foreground_info()
                hwnd = fg["hwnd"]
                app_name = fg["app_name"]
                title = fg["title"]

                # 4. Match Rules & Categorize
                match_res = engine.match(app_name, title)
                category = match_res["category"]
                tags = match_res["tags"]
                prod_score = match_res["productivity_score"]

                # 5. Check Focus & Limits
                is_over_limit = False
                
                # Rule A: In active Pomodoro Focus Mode, block distraction apps immediately
                if pomodoro.mode == "focus" and pomodoro.is_running and pomodoro.strict_mode and prod_score < 0:
                    is_over_limit = True
                    blocker.trigger_strict_lock(
                        hwnd, 
                        app_name, 
                        title, 
                        reason=f"番茄鐘專注進行中 ({pomodoro.remaining_seconds // 60}m 剩餘)！已依嚴格防護策略鎖定分心程式。"
                    )
                else:
                    # Rule B: Check daily usage quota
                    limit_res = engine.check_limit(app_name, match_res)
                    if limit_res.get("is_over_limit", False):
                        is_over_limit = True
                        act = limit_res.get("block_action", "none")
                        if act == "strict_lock":
                            blocker.trigger_strict_lock(
                                hwnd,
                                app_name,
                                title,
                                reason=f"今日配額已超額 {limit_res.get('over_minutes', 0)} 分鐘！"
                            )
                        elif act == "soft_warn":
                            blocker.trigger_soft_warning(
                                app_name,
                                title,
                                reason=f"今日使用時間已超額 {limit_res.get('over_minutes', 0)} 分鐘。"
                            )

                # 6. Record to database
                record_activity(
                    app_name=app_name,
                    window_title=title,
                    duration_sec=POLL_INTERVAL_SECONDS,
                    category=category,
                    tags=tags,
                    productivity_score=prod_score,
                    is_idle=is_idle
                )

                # 7. Update current session state for API
                if app_name != last_app or title != last_title:
                    last_app = app_name
                    last_title = title
                    session_start = time.time()

                self.current_window = {
                    "app_name": app_name,
                    "title": title,
                    "category": category,
                    "tags": tags,
                    "productivity_score": prod_score,
                    "is_idle": is_idle,
                    "session_seconds": round(time.time() - session_start, 1),
                    "is_over_limit": is_over_limit
                }

            except Exception as e:
                print(f"[Tracker] Error in loop: {e}")

            # Maintain steady interval
            elapsed = time.time() - start_loop
            sleep_time = max(0.1, POLL_INTERVAL_SECONDS - elapsed)
            time.sleep(sleep_time)

# Global singleton
tracker = WindowTracker()
