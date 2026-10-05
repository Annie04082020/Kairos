import re
from typing import Dict, Any, List, Optional
from kairos.database import get_rules, get_today_app_usage

class RuleEngine:
    def __init__(self):
        self._rules_cache: List[Dict[str, Any]] = []
        self.reload_rules()

    def reload_rules(self):
        self._rules_cache = [r for r in get_rules() if r.get("is_enabled", 1) == 1]

    def match(self, app_name: str, window_title: str) -> Dict[str, Any]:
        """
        Matches active window and process against rules.
        Priority: Title rules (specific website/doc) > App rules > Heuristic defaults.
        """
        app_lower = (app_name or "").lower().strip()
        title_lower = (window_title or "").lower().strip()

        # 1. Match title rules first (e.g. youtube, github, figma)
        for r in self._rules_cache:
            if r["pattern_type"] == "title":
                pat = r["pattern"].lower()
                if pat in title_lower:
                    return {
                        "category": r["category"],
                        "tags": r["tags"],
                        "productivity_score": r["productivity_score"],
                        "daily_limit_minutes": r["daily_limit_minutes"],
                        "block_action": r["block_action"],
                        "rule_id": r["id"],
                        "matched_by": "title"
                    }
            elif r["pattern_type"] == "regex":
                try:
                    if re.search(r["pattern"], title_lower, re.IGNORECASE) or re.search(r["pattern"], app_lower, re.IGNORECASE):
                        return {
                            "category": r["category"],
                            "tags": r["tags"],
                            "productivity_score": r["productivity_score"],
                            "daily_limit_minutes": r["daily_limit_minutes"],
                            "block_action": r["block_action"],
                            "rule_id": r["id"],
                            "matched_by": "regex"
                        }
                except re.error:
                    pass

        # 2. Match app rules (e.g. code.exe, steam.exe, discord.exe)
        for r in self._rules_cache:
            if r["pattern_type"] == "app":
                pat = r["pattern"].lower()
                # support exact match or matching base without .exe
                if pat == app_lower or pat == app_lower.replace(".exe", "") or app_lower.startswith(pat):
                    return {
                        "category": r["category"],
                        "tags": r["tags"],
                        "productivity_score": r["productivity_score"],
                        "daily_limit_minutes": r["daily_limit_minutes"],
                        "block_action": r["block_action"],
                        "rule_id": r["id"],
                        "matched_by": "app"
                    }

        # 3. Fallback Heuristics
        if any(term in title_lower for term in ["stackoverflow", "github", "gitlab", "documentation", "api reference", "developer"]):
            return {
                "category": "Development",
                "tags": "research,dev",
                "productivity_score": 2,
                "daily_limit_minutes": 0,
                "block_action": "none",
                "rule_id": None,
                "matched_by": "heuristic"
            }

        # Default Neutral
        return {
            "category": "Uncategorized",
            "tags": "general",
            "productivity_score": 0,
            "daily_limit_minutes": 0,
            "block_action": "none",
            "rule_id": None,
            "matched_by": "default"
        }

    def check_limit(self, app_name: str, rule_match: Dict[str, Any]) -> Dict[str, Any]:
        """
        Checks whether the app has exceeded its daily quota.
        """
        daily_limit_minutes = rule_match.get("daily_limit_minutes", 0)
        block_action = rule_match.get("block_action", "none")

        if daily_limit_minutes <= 0 or block_action == "none":
            return {"is_over_limit": False}

        limit_sec = daily_limit_minutes * 60
        used_sec = get_today_app_usage(app_name)

        if used_sec >= limit_sec:
            over_minutes = round((used_sec - limit_sec) / 60, 1)
            return {
                "is_over_limit": True,
                "limit_sec": limit_sec,
                "used_sec": used_sec,
                "over_minutes": over_minutes,
                "block_action": block_action,
                "category": rule_match.get("category", "")
            }

        return {"is_over_limit": False, "remaining_sec": limit_sec - used_sec}

# Global singleton
engine = RuleEngine()
