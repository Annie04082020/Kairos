import sqlite3
import datetime
from typing import List, Dict, Any, Optional
from kairos.config import DB_PATH, DEFAULT_RULES

def get_connection() -> sqlite3.Connection:
    conn = sqlite3.connect(str(DB_PATH), check_same_thread=False)
    conn.row_factory = sqlite3.Row
    return conn

def init_db():
    conn = get_connection()
    with conn:
        cursor = conn.cursor()
        
        # 1. Events Table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS events (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                timestamp DATETIME DEFAULT CURRENT_TIMESTAMP,
                date_str TEXT NOT NULL,
                hour INTEGER NOT NULL,
                app_name TEXT NOT NULL,
                window_title TEXT NOT NULL,
                duration_sec REAL NOT NULL,
                category TEXT NOT NULL,
                tags TEXT NOT NULL,
                productivity_score INTEGER NOT NULL,
                is_idle INTEGER DEFAULT 0
            )
        """)
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_events_date ON events(date_str)")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_events_app ON events(app_name)")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_events_category ON events(category)")

        # 2. Rules Table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS rules (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                pattern_type TEXT NOT NULL, -- 'app', 'title', 'regex'
                pattern TEXT NOT NULL,
                category TEXT NOT NULL,
                tags TEXT NOT NULL,
                productivity_score INTEGER NOT NULL,
                daily_limit_minutes INTEGER DEFAULT 0,
                block_action TEXT DEFAULT 'none', -- 'none', 'soft_warn', 'strict_lock'
                is_enabled INTEGER DEFAULT 1,
                created_at DATETIME DEFAULT CURRENT_TIMESTAMP
            )
        """)

        # 3. Pomodoro Sessions Table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS pomodoro_sessions (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                start_time DATETIME NOT NULL,
                end_time DATETIME,
                mode TEXT NOT NULL, -- 'focus', 'short_break', 'long_break'
                duration_minutes INTEGER NOT NULL,
                completed INTEGER DEFAULT 0,
                interrupted_reason TEXT
            )
        """)

        # 4. Interventions Table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS interventions (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                timestamp DATETIME DEFAULT CURRENT_TIMESTAMP,
                app_name TEXT NOT NULL,
                window_title TEXT NOT NULL,
                action_taken TEXT NOT NULL,
                reason TEXT
            )
        """)

        # 5. Settings Table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS settings (
                key TEXT PRIMARY KEY,
                value TEXT NOT NULL
            )
        """)

        # 6. Devices Table (Multi-device: Windows, Android, iPad/iOS)
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS devices (
                device_id TEXT PRIMARY KEY,
                device_name TEXT NOT NULL,
                device_type TEXT NOT NULL, -- 'windows', 'android', 'ipad', 'ios'
                last_seen DATETIME DEFAULT CURRENT_TIMESTAMP,
                ip_address TEXT
            )
        """)

        # 7. Categories Table (Custom Categories Support)
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS categories (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT UNIQUE NOT NULL,
                display_name TEXT NOT NULL,
                color TEXT DEFAULT '#38bdf8',
                icon TEXT DEFAULT '📁',
                default_score INTEGER DEFAULT 0,
                is_system INTEGER DEFAULT 0,
                created_at DATETIME DEFAULT CURRENT_TIMESTAMP
            )
        """)

        # Seed default categories if empty
        cursor.execute("SELECT COUNT(*) FROM categories")
        if cursor.fetchone()[0] == 0:
            default_cats = [
                ("Development", "開發工作", "#38bdf8", "💻", 2, 1),
                ("Productivity", "高專注生產力", "#10b981", "⚡", 1, 1),
                ("Communication", "通訊通話", "#c084fc", "💬", 0, 1),
                ("Social Media", "社群網路", "#fb923c", "📱", -2, 1),
                ("Entertainment", "影音娛樂", "#fb7185", "🎬", -1, 1),
                ("Gaming", "遊戲電玩", "#f43f5e", "🎮", -2, 1),
                ("Study & Research", "研讀與筆記", "#34d399", "📚", 2, 0),
                ("Finance", "財經投資", "#facc15", "📈", 1, 0),
                ("Design & Creative", "設計創作", "#e879f9", "🎨", 2, 0),
                ("Utilities", "系統工具", "#94a3b8", "🛠️", 0, 1),
                ("Uncategorized", "未分類", "#64748b", "📁", 0, 1)
            ]
            for cat in default_cats:
                cursor.execute("""
                    INSERT OR IGNORE INTO categories (name, display_name, color, icon, default_score, is_system)
                    VALUES (?, ?, ?, ?, ?, ?)
                """, cat)
            conn.commit()

        # Schema Migration: Add device columns to events if not exists
        cursor.execute("PRAGMA table_info(events)")
        existing_cols = [row[1] for row in cursor.fetchall()]
        if "device_id" not in existing_cols:
            cursor.execute("ALTER TABLE events ADD COLUMN device_id TEXT DEFAULT 'local-windows'")
        if "device_type" not in existing_cols:
            cursor.execute("ALTER TABLE events ADD COLUMN device_type TEXT DEFAULT 'windows'")
        if "client_uuid" not in existing_cols:
            cursor.execute("ALTER TABLE events ADD COLUMN client_uuid TEXT")
            cursor.execute("CREATE UNIQUE INDEX IF NOT EXISTS idx_events_client_uuid ON events(client_uuid)")

        # Register default local windows device
        cursor.execute("""
            INSERT OR REPLACE INTO devices (device_id, device_name, device_type, last_seen, ip_address)
            VALUES ('local-windows', '本機電腦 (Windows)', 'windows', CURRENT_TIMESTAMP, '127.0.0.1')
        """)

        # Seed default rules if table is empty
        cursor.execute("SELECT COUNT(*) FROM rules")
        if cursor.fetchone()[0] == 0:
            for rule in DEFAULT_RULES:
                cursor.execute("""
                    INSERT INTO rules (pattern_type, pattern, category, tags, productivity_score, daily_limit_minutes, block_action)
                    VALUES (?, ?, ?, ?, ?, ?, ?)
                """, (
                    rule["pattern_type"],
                    rule["pattern"].lower(),
                    rule["category"],
                    rule["tags"],
                    rule["productivity_score"],
                    rule["daily_limit_minutes"],
                    rule["block_action"]
                ))
            conn.commit()

        # Seed default settings if empty
        defaults = {
            "focus_duration_min": "25",
            "short_break_min": "5",
            "long_break_min": "15",
            "strict_mode_focus": "true",
            "allow_snooze_times": "2",
            "snooze_duration_min": "5"
        }
        for k, v in defaults.items():
            cursor.execute("INSERT OR IGNORE INTO settings (key, value) VALUES (?, ?)", (k, v))
        conn.commit()

def get_categories() -> List[Dict[str, Any]]:
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM categories ORDER BY is_system DESC, id ASC")
    return [dict(row) for row in cursor.fetchall()]

def get_category_by_id(cat_id: int) -> Optional[Dict[str, Any]]:
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM categories WHERE id = ?", (cat_id,))
    row = cursor.fetchone()
    return dict(row) if row else None

def add_category(
    name: str,
    display_name: str,
    color: str = "#38bdf8",
    icon: str = "📁",
    default_score: int = 0
) -> int:
    conn = get_connection()
    with conn:
        cursor = conn.cursor()
        cursor.execute("""
            INSERT INTO categories (name, display_name, color, icon, default_score, is_system)
            VALUES (?, ?, ?, ?, ?, 0)
        """, (name.strip(), display_name.strip(), color.strip(), icon.strip() or "📁", default_score))
        return cursor.lastrowid

def update_category(
    cat_id: int,
    display_name: str,
    color: str,
    icon: str,
    default_score: int,
    name: Optional[str] = None
) -> bool:
    conn = get_connection()
    with conn:
        cursor = conn.cursor()
        if name:
            cursor.execute("""
                UPDATE categories
                SET name = ?, display_name = ?, color = ?, icon = ?, default_score = ?
                WHERE id = ?
            """, (name.strip(), display_name.strip(), color.strip(), icon.strip(), default_score, cat_id))
        else:
            cursor.execute("""
                UPDATE categories
                SET display_name = ?, color = ?, icon = ?, default_score = ?
                WHERE id = ?
            """, (display_name.strip(), color.strip(), icon.strip(), default_score, cat_id))
        return cursor.rowcount > 0

def delete_category(cat_id: int) -> bool:
    conn = get_connection()
    with conn:
        cursor = conn.cursor()
        cursor.execute("SELECT is_system, name FROM categories WHERE id = ?", (cat_id,))
        row = cursor.fetchone()
        if not row:
            return False
        if row["is_system"] == 1:
            raise ValueError("系統核心預設分類不可刪除")
        
        cat_name = row["name"]
        # Update any rules using this category to 'Uncategorized'
        cursor.execute("UPDATE rules SET category = 'Uncategorized' WHERE category = ?", (cat_name,))
        # Delete category
        cursor.execute("DELETE FROM categories WHERE id = ?", (cat_id,))
        return True


def register_or_update_device(device_id: str, device_name: str, device_type: str, ip_address: str = ""):
    conn = get_connection()
    with conn:
        conn.execute("""
            INSERT INTO devices (device_id, device_name, device_type, last_seen, ip_address)
            VALUES (?, ?, ?, CURRENT_TIMESTAMP, ?)
            ON CONFLICT(device_id) DO UPDATE SET
                device_name = excluded.device_name,
                device_type = excluded.device_type,
                last_seen = CURRENT_TIMESTAMP,
                ip_address = excluded.ip_address
        """, (device_id, device_name, device_type, ip_address))

def get_registered_devices() -> List[Dict[str, Any]]:
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM devices ORDER BY last_seen DESC")
    return [dict(row) for row in cursor.fetchall()]

def record_activity(
    app_name: str,
    window_title: str,
    duration_sec: float,
    category: str,
    tags: str,
    productivity_score: int,
    is_idle: bool = False,
    device_id: str = "local-windows",
    device_type: str = "windows"
):
    if duration_sec <= 0.05:
        return
    now = datetime.datetime.now()
    date_str = now.strftime("%Y-%m-%d")
    hour = now.hour
    
    conn = get_connection()
    with conn:
        conn.execute("""
            INSERT INTO events (date_str, hour, app_name, window_title, duration_sec, category, tags, productivity_score, is_idle, device_id, device_type)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            date_str,
            hour,
            app_name,
            window_title,
            round(duration_sec, 2),
            category,
            tags,
            productivity_score,
            1 if is_idle else 0,
            device_id,
            device_type
        ))

def batch_insert_sync_data(device_id: str, device_name: str, device_type: str, events: List[Dict[str, Any]], pomodoros: List[Dict[str, Any]] = None) -> int:
    """Inserts batch of synced events and pomodoros from iPad / Android, ignoring duplicate UUIDs."""
    register_or_update_device(device_id, device_name, device_type)
    conn = get_connection()
    inserted_count = 0
    with conn:
        cursor = conn.cursor()
        for ev in events:
            date_str = ev.get("date_str") or (ev.get("timestamp", "")[:10]) or datetime.date.today().strftime("%Y-%m-%d")
            hour = ev.get("hour") if ev.get("hour") is not None else 12
            uuid_key = ev.get("client_uuid") or f"{device_id}_{ev.get('timestamp')}_{ev.get('app_name')}_{ev.get('duration_sec')}"
            try:
                cursor.execute("""
                    INSERT OR IGNORE INTO events 
                    (date_str, hour, app_name, window_title, duration_sec, category, tags, productivity_score, is_idle, device_id, device_type, client_uuid)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """, (
                    date_str,
                    hour,
                    ev.get("app_name", "Unknown"),
                    ev.get("window_title", ""),
                    float(ev.get("duration_sec", 0)),
                    ev.get("category", "Uncategorized"),
                    ev.get("tags", ""),
                    int(ev.get("productivity_score", 0)),
                    1 if ev.get("is_idle") else 0,
                    device_id,
                    device_type,
                    uuid_key
                ))
                if cursor.rowcount > 0:
                    inserted_count += 1
            except Exception as e:
                print(f"[Sync] Error inserting event: {e}")

        # Insert synced pomodoro sessions if any
        if pomodoros:
            for p in pomodoros:
                try:
                    cursor.execute("""
                        INSERT INTO pomodoro_sessions (start_time, end_time, mode, duration_minutes, completed)
                        VALUES (?, ?, ?, ?, ?)
                    """, (
                        p.get("start_time") or datetime.datetime.now(),
                        p.get("end_time") or datetime.datetime.now(),
                        p.get("mode", "focus"),
                        int(p.get("duration_minutes", 25)),
                        1 if p.get("completed") else 0
                    ))
                except Exception:
                    pass
    return inserted_count

def get_today_app_usage(app_name: str, device_type: Optional[str] = None) -> float:
    """Returns today's cumulative usage in seconds for a specific app (excluding idle)."""
    date_str = datetime.date.today().strftime("%Y-%m-%d")
    conn = get_connection()
    cursor = conn.cursor()
    if device_type and device_type != "all":
        cursor.execute("""
            SELECT COALESCE(SUM(duration_sec), 0)
            FROM events
            WHERE date_str = ? AND LOWER(app_name) = LOWER(?) AND is_idle = 0 AND device_type = ?
        """, (date_str, app_name, device_type))
    else:
        cursor.execute("""
            SELECT COALESCE(SUM(duration_sec), 0)
            FROM events
            WHERE date_str = ? AND LOWER(app_name) = LOWER(?) AND is_idle = 0
        """, (date_str, app_name))
    row = cursor.fetchone()
    return float(row[0]) if row else 0.0

def get_rules() -> List[Dict[str, Any]]:
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM rules ORDER BY id DESC")
    return [dict(row) for row in cursor.fetchall()]

def add_rule(
    pattern_type: str,
    pattern: str,
    category: str,
    tags: str,
    productivity_score: int,
    daily_limit_minutes: int,
    block_action: str
) -> int:
    conn = get_connection()
    with conn:
        cursor = conn.cursor()
        cursor.execute("""
            INSERT INTO rules (pattern_type, pattern, category, tags, productivity_score, daily_limit_minutes, block_action)
            VALUES (?, ?, ?, ?, ?, ?, ?)
        """, (
            pattern_type,
            pattern.strip().lower(),
            category.strip(),
            tags.strip(),
            productivity_score,
            daily_limit_minutes,
            block_action
        ))
        return cursor.lastrowid

def update_rule(
    rule_id: int,
    category: str,
    tags: str,
    productivity_score: int,
    daily_limit_minutes: int,
    block_action: str,
    is_enabled: int
):
    conn = get_connection()
    with conn:
        conn.execute("""
            UPDATE rules
            SET category = ?, tags = ?, productivity_score = ?, daily_limit_minutes = ?, block_action = ?, is_enabled = ?
            WHERE id = ?
        """, (category, tags, productivity_score, daily_limit_minutes, block_action, is_enabled, rule_id))

def delete_rule(rule_id: int):
    conn = get_connection()
    with conn:
        conn.execute("DELETE FROM rules WHERE id = ?", (rule_id,))

def get_today_summary(device_filter: Optional[str] = None) -> Dict[str, Any]:
    date_str = datetime.date.today().strftime("%Y-%m-%d")
    conn = get_connection()
    cursor = conn.cursor()

    dev_clause = ""
    params_base = [date_str]
    if device_filter and device_filter != "all":
        dev_clause = " AND device_type = ?"
        params_base.append(device_filter)

    # Total active time
    cursor.execute(f"""
        SELECT COALESCE(SUM(duration_sec), 0)
        FROM events
        WHERE date_str = ? AND is_idle = 0{dev_clause}
    """, tuple(params_base))
    total_active_sec = float(cursor.fetchone()[0])

    # Total idle time
    cursor.execute(f"""
        SELECT COALESCE(SUM(duration_sec), 0)
        FROM events
        WHERE date_str = ? AND is_idle = 1{dev_clause}
    """, tuple(params_base))
    total_idle_sec = float(cursor.fetchone()[0])

    # Productivity Breakdown
    # Score groups: Productive (>=1), Neutral (0), Distracting (<0)
    cursor.execute(f"""
        SELECT 
            CASE 
                WHEN productivity_score > 0 THEN 'productive'
                WHEN productivity_score = 0 THEN 'neutral'
                ELSE 'distracting'
            END AS score_type,
            COALESCE(SUM(duration_sec), 0) as total_sec
        FROM events
        WHERE date_str = ? AND is_idle = 0{dev_clause}
        GROUP BY score_type
    """, tuple(params_base))
    productivity_map = {"productive": 0.0, "neutral": 0.0, "distracting": 0.0}
    for row in cursor.fetchall():
        productivity_map[row["score_type"]] = float(row["total_sec"])

    # Calculate Focus Score (0 - 100)
    focus_score = 50.0
    if total_active_sec > 60:
        prod_time = productivity_map["productive"]
        dist_time = productivity_map["distracting"]
        neut_time = productivity_map["neutral"]
        # Formula: weighted score normalized to 0-100
        score_val = (prod_time * 1.0 + neut_time * 0.5 - dist_time * 0.8) / total_active_sec
        focus_score = max(0.0, min(100.0, score_val * 100))

    # Top Apps Today
    cursor.execute(f"""
        SELECT 
            app_name,
            category,
            COALESCE(SUM(duration_sec), 0) as total_sec,
            AVG(productivity_score) as avg_score
        FROM events
        WHERE date_str = ? AND is_idle = 0{dev_clause}
        GROUP BY app_name
        ORDER BY total_sec DESC
        LIMIT 15
    """, tuple(params_base))
    top_apps = []
    for row in cursor.fetchall():
        top_apps.append({
            "app_name": row["app_name"],
            "category": row["category"],
            "total_sec": float(row["total_sec"]),
            "avg_score": round(float(row["avg_score"] or 0), 1),
            "percentage": round((float(row["total_sec"]) / (total_active_sec or 1)) * 100, 1)
        })

    # Category Breakdown
    cursor.execute(f"""
        SELECT 
            category,
            COALESCE(SUM(duration_sec), 0) as total_sec
        FROM events
        WHERE date_str = ? AND is_idle = 0{dev_clause}
        GROUP BY category
        ORDER BY total_sec DESC
    """, tuple(params_base))
    categories = [
        {"category": row["category"], "total_sec": float(row["total_sec"])}
        for row in cursor.fetchall()
    ]

    # Tag Breakdown
    cursor.execute(f"""
        SELECT tags, duration_sec
        FROM events
        WHERE date_str = ? AND is_idle = 0 AND tags != ''{dev_clause}
    """, tuple(params_base))
    tag_times: Dict[str, float] = {}
    for row in cursor.fetchall():
        tags_raw = row["tags"]
        duration = float(row["duration_sec"])
        for tag in tags_raw.split(","):
            tag_clean = tag.strip()
            if tag_clean:
                tag_times[tag_clean] = tag_times.get(tag_clean, 0.0) + duration
    
    sorted_tags = sorted([{"tag": k, "total_sec": v} for k, v in tag_times.items()], key=lambda x: x["total_sec"], reverse=True)[:10]

    # Hourly distribution for today (0 - 23)
    cursor.execute(f"""
        SELECT hour, COALESCE(SUM(duration_sec), 0) as total_sec
        FROM events
        WHERE date_str = ? AND is_idle = 0{dev_clause}
        GROUP BY hour
        ORDER BY hour ASC
    """, tuple(params_base))
    hourly_dict = {i: 0.0 for i in range(24)}
    for row in cursor.fetchall():
        hourly_dict[row["hour"]] = round(float(row["total_sec"]), 1)
    hourly_series = [{"hour": h, "seconds": hourly_dict[h]} for h in range(24)]

    return {
        "date": date_str,
        "total_active_sec": round(total_active_sec, 1),
        "total_idle_sec": round(total_idle_sec, 1),
        "focus_score": round(focus_score, 1),
        "productivity": productivity_map,
        "top_apps": top_apps,
        "categories": categories,
        "tags": sorted_tags,
        "hourly_distribution": hourly_series
    }

def get_weekly_trends() -> List[Dict[str, Any]]:
    """Returns past 7 days daily active seconds and focus score."""
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("""
        SELECT 
            date_str,
            COALESCE(SUM(duration_sec), 0) as total_sec,
            AVG(productivity_score) as avg_score
        FROM events
        WHERE is_idle = 0
        GROUP BY date_str
        ORDER BY date_str DESC
        LIMIT 7
    """)
    rows = cursor.fetchall()
    results = []
    for row in reversed(rows):
        results.append({
            "date": row["date_str"],
            "total_sec": float(row["total_sec"]),
            "avg_score": round(float(row["avg_score"] or 0), 2)
        })
    return results

def get_recent_interventions(limit: int = 10) -> List[Dict[str, Any]]:
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("""
        SELECT * FROM interventions ORDER BY id DESC LIMIT ?
    """, (limit,))
    return [dict(row) for row in cursor.fetchall()]

def log_intervention(app_name: str, window_title: str, action_taken: str, reason: str):
    conn = get_connection()
    with conn:
        conn.execute("""
            INSERT INTO interventions (app_name, window_title, action_taken, reason)
            VALUES (?, ?, ?, ?)
        """, (app_name, window_title, action_taken, reason))
