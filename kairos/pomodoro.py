import time
import datetime
from typing import Dict, Any, Optional
from kairos.database import get_connection

class PomodoroController:
    def __init__(self):
        self.mode = "idle"  # 'idle', 'focus', 'short_break', 'long_break'
        self.is_running = False
        self.duration_seconds = 25 * 60
        self.remaining_seconds = 25 * 60
        self.focus_count_today = 0
        self.current_db_id: Optional[int] = None
        self.strict_mode = True  # Auto-block distracting apps during focus
        self._load_today_completed_count()

    def _load_today_completed_count(self):
        try:
            date_str = datetime.date.today().strftime("%Y-%m-%d")
            conn = get_connection()
            cursor = conn.cursor()
            cursor.execute("""
                SELECT COUNT(*) FROM pomodoro_sessions
                WHERE mode = 'focus' AND completed = 1 AND DATE(start_time) = ?
            """, (date_str,))
            self.focus_count_today = cursor.fetchone()[0] or 0
        except Exception:
            self.focus_count_today = 0

    def start(self, mode: str = "focus", duration_minutes: int = 25):
        self.mode = mode
        self.duration_seconds = duration_minutes * 60
        self.remaining_seconds = self.duration_seconds
        self.is_running = True

        # Record in DB
        try:
            conn = get_connection()
            with conn:
                cursor = conn.cursor()
                cursor.execute("""
                    INSERT INTO pomodoro_sessions (start_time, mode, duration_minutes, completed)
                    VALUES (?, ?, ?, 0)
                """, (datetime.datetime.now(), mode, duration_minutes))
                self.current_db_id = cursor.lastrowid
        except Exception as e:
            print(f"[Pomodoro] Error saving session start: {e}")

    def pause(self):
        self.is_running = False

    def resume(self):
        if self.mode != "idle":
            self.is_running = True

    def reset(self):
        if self.current_db_id and self.is_running and self.mode == "focus":
            try:
                conn = get_connection()
                with conn:
                    conn.execute("""
                        UPDATE pomodoro_sessions
                        SET end_time = ?, interrupted_reason = 'User Reset'
                        WHERE id = ?
                    """, (datetime.datetime.now(), self.current_db_id))
            except Exception:
                pass
        self.mode = "idle"
        self.is_running = False
        self.duration_seconds = 25 * 60
        self.remaining_seconds = 25 * 60
        self.current_db_id = None

    def skip(self):
        """Skip current session and transition to next logical mode."""
        if self.mode == "focus":
            self.start(mode="short_break", duration_minutes=5)
        else:
            self.start(mode="focus", duration_minutes=25)

    def tick(self, delta_sec: float = 1.0):
        if not self.is_running or self.mode == "idle":
            return

        self.remaining_seconds -= delta_sec
        if self.remaining_seconds <= 0:
            self._handle_completed()

    def _handle_completed(self):
        self.is_running = False
        self.remaining_seconds = 0
        
        # Update DB
        if self.current_db_id:
            try:
                conn = get_connection()
                with conn:
                    conn.execute("""
                        UPDATE pomodoro_sessions
                        SET end_time = ?, completed = 1
                        WHERE id = ?
                    """, (datetime.datetime.now(), self.current_db_id))
            except Exception as e:
                print(f"[Pomodoro] Error marking completed: {e}")

        # Beep notification
        try:
            import winsound
            winsound.Beep(1000, 500)
            winsound.Beep(1300, 400)
        except Exception:
            pass

        # Switch state
        if self.mode == "focus":
            self.focus_count_today += 1
            if self.focus_count_today % 4 == 0:
                self.start(mode="long_break", duration_minutes=15)
            else:
                self.start(mode="short_break", duration_minutes=5)
        else:
            self.mode = "idle"
            self.duration_seconds = 25 * 60
            self.remaining_seconds = 25 * 60

    def get_state(self) -> Dict[str, Any]:
        return {
            "mode": self.mode,
            "is_running": self.is_running,
            "duration_seconds": self.duration_seconds,
            "remaining_seconds": max(0, int(self.remaining_seconds)),
            "focus_count_today": self.focus_count_today,
            "strict_mode": self.strict_mode,
            "progress_percent": round(((self.duration_seconds - self.remaining_seconds) / max(1, self.duration_seconds)) * 100, 1) if self.duration_seconds else 0
        }

# Global singleton
pomodoro = PomodoroController()
