import os
from pathlib import Path

# Paths
BASE_DIR = Path(__file__).resolve().parent.parent
DATA_DIR = BASE_DIR / "data"
DATA_DIR.mkdir(parents=True, exist_ok=True)
DB_PATH = DATA_DIR / "kairos.db"
STATIC_DIR = BASE_DIR / "web"

# Server Settings (0.0.0.0 enables LAN access for iPad, Android, and other devices)
HOST = "0.0.0.0"
PORT = 5050
POLL_INTERVAL_SECONDS = 1.0
IDLE_THRESHOLD_SECONDS = 180  # 3 minutes of no user activity marks idle

# Productivity Score Scale
# +2: Deep Work / Code / Design
# +1: Productive Communication / Notes
#  0: Neutral / System
# -1: Distracting
# -2: Highly Distracting / Addictive
SCORE_VERY_PRODUCTIVE = 2
SCORE_PRODUCTIVE = 1
SCORE_NEUTRAL = 0
SCORE_DISTRACTING = -1
SCORE_VERY_DISTRACTING = -2

# Default Seed Rules (App names lowercase, Title pattern lowercase regex or substring)
DEFAULT_RULES = [
    # Work & Development (+2)
    {"pattern_type": "app", "pattern": "code.exe", "category": "Development", "tags": "coding,vscode", "productivity_score": 2, "daily_limit_minutes": 0, "block_action": "none"},
    {"pattern_type": "app", "pattern": "pycharm64.exe", "category": "Development", "tags": "coding,python", "productivity_score": 2, "daily_limit_minutes": 0, "block_action": "none"},
    {"pattern_type": "app", "pattern": "devenv.exe", "category": "Development", "tags": "coding,visualstudio", "productivity_score": 2, "daily_limit_minutes": 0, "block_action": "none"},
    {"pattern_type": "app", "pattern": "windowsterminal.exe", "category": "Development", "tags": "terminal,devops", "productivity_score": 2, "daily_limit_minutes": 0, "block_action": "none"},
    {"pattern_type": "app", "pattern": "powershell.exe", "category": "Development", "tags": "terminal,shell", "productivity_score": 2, "daily_limit_minutes": 0, "block_action": "none"},
    {"pattern_type": "app", "pattern": "cmd.exe", "category": "Development", "tags": "terminal,shell", "productivity_score": 2, "daily_limit_minutes": 0, "block_action": "none"},
    {"pattern_type": "title", "pattern": "github.com", "category": "Development", "tags": "git,dev", "productivity_score": 2, "daily_limit_minutes": 0, "block_action": "none"},
    {"pattern_type": "title", "pattern": "stack overflow", "category": "Development", "tags": "research,dev", "productivity_score": 2, "daily_limit_minutes": 0, "block_action": "none"},
    {"pattern_type": "title", "pattern": "chatgpt", "category": "Productivity", "tags": "ai,assistant", "productivity_score": 1, "daily_limit_minutes": 0, "block_action": "none"},
    {"pattern_type": "title", "pattern": "claude", "category": "Productivity", "tags": "ai,assistant", "productivity_score": 1, "daily_limit_minutes": 0, "block_action": "none"},

    # Communication (+1)
    {"pattern_type": "app", "pattern": "slack.exe", "category": "Communication", "tags": "chat,work", "productivity_score": 1, "daily_limit_minutes": 0, "block_action": "none"},
    {"pattern_type": "app", "pattern": "teams.exe", "category": "Communication", "tags": "chat,work", "productivity_score": 1, "daily_limit_minutes": 0, "block_action": "none"},
    {"pattern_type": "app", "pattern": "discord.exe", "category": "Communication", "tags": "chat,community", "productivity_score": 0, "daily_limit_minutes": 90, "block_action": "soft_warn"},
    {"pattern_type": "app", "pattern": "telegram.exe", "category": "Communication", "tags": "chat", "productivity_score": 0, "daily_limit_minutes": 60, "block_action": "soft_warn"},
    {"pattern_type": "app", "pattern": "line.exe", "category": "Communication", "tags": "chat", "productivity_score": 0, "daily_limit_minutes": 60, "block_action": "soft_warn"},

    # Entertainment & Social Media (-1, -2)
    {"pattern_type": "title", "pattern": "youtube", "category": "Entertainment", "tags": "video,streaming", "productivity_score": -1, "daily_limit_minutes": 60, "block_action": "soft_warn"},
    {"pattern_type": "title", "pattern": "netflix", "category": "Entertainment", "tags": "movies,streaming", "productivity_score": -2, "daily_limit_minutes": 45, "block_action": "strict_lock"},
    {"pattern_type": "title", "pattern": "twitch", "category": "Entertainment", "tags": "stream,gaming", "productivity_score": -2, "daily_limit_minutes": 45, "block_action": "strict_lock"},
    {"pattern_type": "title", "pattern": "facebook", "category": "Social Media", "tags": "social", "productivity_score": -2, "daily_limit_minutes": 30, "block_action": "strict_lock"},
    {"pattern_type": "title", "pattern": "instagram", "category": "Social Media", "tags": "social", "productivity_score": -2, "daily_limit_minutes": 30, "block_action": "strict_lock"},
    {"pattern_type": "title", "pattern": "threads.net", "category": "Social Media", "tags": "social", "productivity_score": -2, "daily_limit_minutes": 25, "block_action": "strict_lock"},
    {"pattern_type": "title", "pattern": "twitter", "category": "Social Media", "tags": "social", "productivity_score": -2, "daily_limit_minutes": 30, "block_action": "strict_lock"},
    {"pattern_type": "title", "pattern": "x.com", "category": "Social Media", "tags": "social", "productivity_score": -2, "daily_limit_minutes": 30, "block_action": "strict_lock"},
    {"pattern_type": "title", "pattern": "reddit", "category": "Social Media", "tags": "forum,casual", "productivity_score": -1, "daily_limit_minutes": 40, "block_action": "soft_warn"},
    {"pattern_type": "title", "pattern": "bilibili", "category": "Entertainment", "tags": "video,anime", "productivity_score": -2, "daily_limit_minutes": 45, "block_action": "strict_lock"},

    # Gaming (-2)
    {"pattern_type": "app", "pattern": "steam.exe", "category": "Gaming", "tags": "game,launcher", "productivity_score": -2, "daily_limit_minutes": 60, "block_action": "soft_warn"},
    {"pattern_type": "app", "pattern": "epicgameslauncher.exe", "category": "Gaming", "tags": "game,launcher", "productivity_score": -2, "daily_limit_minutes": 60, "block_action": "soft_warn"},
    {"pattern_type": "app", "pattern": "riotclientservices.exe", "category": "Gaming", "tags": "game", "productivity_score": -2, "daily_limit_minutes": 45, "block_action": "strict_lock"},
    {"pattern_type": "app", "pattern": "league of legends.exe", "category": "Gaming", "tags": "game,moba", "productivity_score": -2, "daily_limit_minutes": 45, "block_action": "strict_lock"},
    {"pattern_type": "app", "pattern": "genshinimpact.exe", "category": "Gaming", "tags": "game,rpg", "productivity_score": -2, "daily_limit_minutes": 45, "block_action": "strict_lock"}
]
