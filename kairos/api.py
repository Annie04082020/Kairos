import datetime
from fastapi import FastAPI, HTTPException
from fastapi.staticfiles import StaticFiles
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import Optional, List, Dict, Any

from kairos.config import STATIC_DIR
from kairos.tracker import tracker
from kairos.pomodoro import pomodoro
from kairos.blocker import blocker
from kairos.engine import engine
import socket
from kairos.database import (
    get_today_summary,
    get_weekly_trends,
    get_rules,
    add_rule,
    update_rule,
    delete_rule,
    get_recent_interventions,
    get_connection,
    register_or_update_device,
    get_registered_devices,
    record_activity,
    batch_insert_sync_data,
    get_categories,
    get_category_by_id,
    add_category,
    update_category,
    delete_category
)

def get_server_lan_ip() -> str:
    s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    try:
        s.connect(('8.8.8.8', 80))
        ip = s.getsockname()[0]
    except Exception:
        ip = '127.0.0.1'
    finally:
        s.close()
    return ip

app = FastAPI(title="Kairos Focus & Usage Engine", version="1.0.0")

@app.on_event("startup")
def on_startup():
    from kairos.database import init_db
    init_db()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Pydantic Models
class RuleCreateRequest(BaseModel):
    pattern_type: str  # 'app', 'title', 'regex'
    pattern: str
    category: str
    tags: str = ""
    productivity_score: int = 0
    daily_limit_minutes: int = 0
    block_action: str = "none"  # 'none', 'soft_warn', 'strict_lock'

class RuleUpdateRequest(BaseModel):
    category: str
    tags: str = ""
    productivity_score: int = 0
    daily_limit_minutes: int = 0
    block_action: str = "none"
    is_enabled: int = 1

class CategoryCreateRequest(BaseModel):
    name: str
    display_name: str
    color: str = "#38bdf8"
    icon: str = "📁"
    default_score: int = 0

class CategoryUpdateRequest(BaseModel):
    display_name: str
    color: str = "#38bdf8"
    icon: str = "📁"
    default_score: int = 0
    name: Optional[str] = None

class PomodoroStartRequest(BaseModel):
    mode: str = "focus"
    duration_minutes: int = 25

class SnoozeRequest(BaseModel):
    app_name: str
    minutes: int = 5

class ClientReportRequest(BaseModel):
    device_id: str
    device_name: str
    device_type: str  # 'android', 'ipad', 'ios', 'windows'
    app_name: str
    window_title: str = ""
    duration_sec: float = 5.0
    is_idle: bool = False

class SyncPushRequest(BaseModel):
    device_id: str
    device_name: str
    device_type: str
    events: List[Dict[str, Any]]
    pomodoros: List[Dict[str, Any]] = []

# Routes
@app.post("/api/sync/push")
def sync_push_data(req: SyncPushRequest):
    """Allows iPad / Android / GitHub Pages to batch sync offline recorded events to server."""
    inserted = batch_insert_sync_data(
        device_id=req.device_id,
        device_name=req.device_name,
        device_type=req.device_type,
        events=req.events,
        pomodoros=req.pomodoros
    )
    return {
        "status": "success",
        "inserted_count": inserted,
        "server_time": str(datetime.datetime.now())
    }

@app.get("/api/sync/pull")
def sync_pull_data():
    """Allows mobile devices to pull latest rules and cloud stats."""
    return {
        "rules": get_rules(),
        "today_summary": get_today_summary(),
        "pomodoro": pomodoro.get_state(),
        "server_time": str(datetime.datetime.now())
    }

@app.get("/api/network/lan-ip")
def get_network_info():
    lan_ip = get_server_lan_ip()
    return {
        "lan_ip": lan_ip,
        "port": 5050,
        "url": f"http://{lan_ip}:5050"
    }

@app.get("/api/devices")
def list_devices():
    return {"devices": get_registered_devices()}

@app.post("/api/client/report")
def report_client_activity(req: ClientReportRequest):
    """
    Receives activity updates from mobile clients (Android app / iOS Shortcut automation).
    Matches rules, records usage, and responds with real-time blocking/warning instructions.
    """
    # 1. Register/Update device heartbeat
    register_or_update_device(
        device_id=req.device_id,
        device_name=req.device_name,
        device_type=req.device_type
    )

    # 2. Match rules
    match_res = engine.match(req.app_name, req.window_title)
    category = match_res["category"]
    tags = match_res["tags"]
    prod_score = match_res["productivity_score"]

    # 3. Record activity to database
    record_activity(
        app_name=req.app_name,
        window_title=req.window_title or req.app_name,
        duration_sec=req.duration_sec,
        category=category,
        tags=tags,
        productivity_score=prod_score,
        is_idle=req.is_idle,
        device_id=req.device_id,
        device_type=req.device_type
    )

    # 4. Check Pomodoro & Limits for Mobile Client
    is_blocked = False
    block_action = "none"
    reason = ""

    # Check Pomodoro focus lock
    if pomodoro.mode == "focus" and pomodoro.is_running and pomodoro.strict_mode and prod_score < 0:
        is_blocked = True
        block_action = "strict_lock"
        reason = f"番茄鐘專注進行中 ({pomodoro.remaining_seconds // 60}m 剩餘)！"
    else:
        # Check quota limit
        limit_res = engine.check_limit(req.app_name, match_res)
        if limit_res.get("is_over_limit", False):
            is_blocked = True
            block_action = limit_res.get("block_action", "soft_warn")
            reason = f"今日配額已超額 {limit_res.get('over_minutes', 0)} 分鐘！"

    return {
        "status": "recorded",
        "app_name": req.app_name,
        "category": category,
        "is_blocked": is_blocked,
        "block_action": block_action,
        "reason": reason,
        "pomodoro": pomodoro.get_state()
    }

@app.get("/api/client/policy")
def get_client_policy():
    """Lightweight endpoint for mobile clients to query current focus policy & rules."""
    return {
        "pomodoro": pomodoro.get_state(),
        "rules": get_rules()
    }

@app.get("/api/status")
def get_live_status(device_type: Optional[str] = None):
    today = get_today_summary(device_filter=device_type)
    return {
        "active_window": tracker.current_window,
        "pomodoro": pomodoro.get_state(),
        "server_lan_ip": get_server_lan_ip(),
        "today_stats": {
            "total_active_sec": today["total_active_sec"],
            "total_idle_sec": today["total_idle_sec"],
            "focus_score": today["focus_score"],
            "productivity": today["productivity"]
        }
    }

@app.get("/api/stats/today")
def get_today_stats(device_type: Optional[str] = None):
    return get_today_summary(device_filter=device_type)

@app.get("/api/stats/weekly")
def get_weekly_stats():
    return {"trends": get_weekly_trends()}

@app.get("/api/rules")
def list_rules():
    return {"rules": get_rules()}

@app.post("/api/rules")
def create_rule(req: RuleCreateRequest):
    new_id = add_rule(
        pattern_type=req.pattern_type,
        pattern=req.pattern,
        category=req.category,
        tags=req.tags,
        productivity_score=req.productivity_score,
        daily_limit_minutes=req.daily_limit_minutes,
        block_action=req.block_action
    )
    engine.reload_rules()
    return {"status": "success", "id": new_id}

@app.put("/api/rules/{rule_id}")
def edit_rule(rule_id: int, req: RuleUpdateRequest):
    update_rule(
        rule_id=rule_id,
        category=req.category,
        tags=req.tags,
        productivity_score=req.productivity_score,
        daily_limit_minutes=req.daily_limit_minutes,
        block_action=req.block_action,
        is_enabled=req.is_enabled
    )
    engine.reload_rules()
    return {"status": "success"}

@app.delete("/api/rules/{rule_id}")
def remove_rule(rule_id: int):
    delete_rule(rule_id)
    engine.reload_rules()
    return {"status": "success"}

# Categories Endpoints (Custom Categories CRUD)
@app.get("/api/categories")
def list_categories():
    return {"categories": get_categories()}

@app.post("/api/categories")
def create_category(req: CategoryCreateRequest):
    try:
        new_id = add_category(
            name=req.name,
            display_name=req.display_name,
            color=req.color,
            icon=req.icon,
            default_score=req.default_score
        )
        return {"status": "success", "id": new_id}
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))

@app.put("/api/categories/{cat_id}")
def edit_category(cat_id: int, req: CategoryUpdateRequest):
    try:
        updated = update_category(
            cat_id=cat_id,
            display_name=req.display_name,
            color=req.color,
            icon=req.icon,
            default_score=req.default_score,
            name=req.name
        )
        if not updated:
            raise HTTPException(status_code=404, detail="分類不存在")
        return {"status": "success"}
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))

@app.delete("/api/categories/{cat_id}")
def remove_category(cat_id: int):
    try:
        deleted = delete_category(cat_id)
        if not deleted:
            raise HTTPException(status_code=404, detail="分類不存在")
        return {"status": "success"}
    except ValueError as ve:
        raise HTTPException(status_code=403, detail=str(ve))
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


@app.post("/api/pomodoro/start")
def start_pomodoro(req: PomodoroStartRequest):
    pomodoro.start(mode=req.mode, duration_minutes=req.duration_minutes)
    return pomodoro.get_state()

@app.post("/api/pomodoro/pause")
def pause_pomodoro():
    pomodoro.pause()
    return pomodoro.get_state()

@app.post("/api/pomodoro/resume")
def resume_pomodoro():
    pomodoro.resume()
    return pomodoro.get_state()

@app.post("/api/pomodoro/reset")
def reset_pomodoro():
    pomodoro.reset()
    return pomodoro.get_state()

@app.post("/api/pomodoro/skip")
def skip_pomodoro():
    pomodoro.skip()
    return pomodoro.get_state()

@app.post("/api/pomodoro/toggle-strict")
def toggle_strict_mode():
    pomodoro.strict_mode = not pomodoro.strict_mode
    return {"strict_mode": pomodoro.strict_mode}

@app.post("/api/interventions/snooze")
def snooze_app(req: SnoozeRequest):
    success = blocker.request_snooze(req.app_name, req.minutes)
    if not success:
        raise HTTPException(status_code=400, detail="今日延長次數已達上限 (最多 2 次)")
    return {"status": "snoozed", "app_name": req.app_name, "minutes": req.minutes}

@app.get("/api/interventions/recent")
def list_interventions():
    return {"interventions": get_recent_interventions(15)}


@app.get("/api/export")
def export_data():
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM events ORDER BY id DESC LIMIT 5000")
    events = [dict(r) for r in cursor.fetchall()]
    return {
        "export_time": str(datetime.datetime.now()),
        "total_records": len(events),
        "events": events
    }

# StayFree Bridge Endpoints (Dedicated for iPad / iOS data import)
from kairos.stayfree_bridge import stayfree_bridge


class StayFreeSyncRequest(BaseModel):
    target_creators: Optional[List[str]] = None

class StayFreeToggleRequest(BaseModel):
    enabled: bool

@app.get("/api/stayfree/status")
def get_stayfree_status():
    return stayfree_bridge.get_status()

@app.post("/api/stayfree/sync")
def trigger_stayfree_sync(req: Optional[StayFreeSyncRequest] = None):
    creators = req.target_creators if req else None
    return stayfree_bridge.sync_ipad_sessions(target_creators=creators)

@app.post("/api/stayfree/toggle-auto")
def toggle_stayfree_auto(req: StayFreeToggleRequest):
    stayfree_bridge.auto_sync_enabled = req.enabled
    return {"auto_sync_enabled": stayfree_bridge.auto_sync_enabled}


# Mount Web Dashboard Frontend
import os
if os.path.exists(str(STATIC_DIR)):
    app.mount("/", StaticFiles(directory=str(STATIC_DIR), html=True), name="static")
