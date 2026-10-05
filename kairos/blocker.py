import time
import threading
import ctypes
from typing import Dict, Any, Optional
from kairos.database import log_intervention

user32 = ctypes.windll.user32

class Blocker:
    def __init__(self):
        self.snoozed_apps: Dict[str, float] = {}  # app_name -> expiry_timestamp
        self.snooze_counts: Dict[str, int] = {}   # app_name -> count_today
        self.max_snoozes_per_day = 2
        self.overlay_active = False
        self.last_warned_app: Optional[str] = None
        self.last_warned_time: float = 0

    def is_snoozed(self, app_name: str) -> bool:
        app_lower = app_name.lower()
        if app_lower in self.snoozed_apps:
            if time.time() < self.snoozed_apps[app_lower]:
                return True
            else:
                del self.snoozed_apps[app_lower]
        return False

    def request_snooze(self, app_name: str, minutes: int = 5) -> bool:
        """Allows snoozing an app for N minutes if daily limit not exceeded."""
        app_lower = app_name.lower()
        current_count = self.snooze_counts.get(app_lower, 0)
        if current_count >= self.max_snoozes_per_day:
            return False
        
        self.snooze_counts[app_lower] = current_count + 1
        self.snoozed_apps[app_lower] = time.time() + (minutes * 60)
        log_intervention(app_name, "", "snooze_5m", f"Snoozed for {minutes}m ({self.snooze_counts[app_lower]}/{self.max_snoozes_per_day})")
        return True

    def minimize_window(self, hwnd: int):
        try:
            if hwnd:
                # SW_MINIMIZE = 6, SW_FORCEMINIMIZE = 11
                user32.ShowWindow(hwnd, 6)
        except Exception as e:
            print(f"[Blocker] Error minimizing window: {e}")

    def trigger_soft_warning(self, app_name: str, title: str, reason: str):
        """Soft warning notification via desktop sound or console/dashboard event."""
        now = time.time()
        # Rate limit soft warning sound to once every 60 seconds per app
        if self.last_warned_app == app_name and (now - self.last_warned_time) < 60:
            return
        
        self.last_warned_app = app_name
        self.last_warned_time = now
        log_intervention(app_name, title, "soft_warn", reason)
        # Windows beep for gentle acoustic cue: 750Hz, 200ms
        try:
            import winsound
            winsound.Beep(750, 200)
        except Exception:
            pass

    def trigger_strict_lock(self, hwnd: int, app_name: str, title: str, reason: str):
        """Strict intervention: Minimize distracting window & pop cooldown overlay."""
        if self.is_snoozed(app_name):
            return

        # 1. Minimize offending window immediately
        self.minimize_window(hwnd)
        log_intervention(app_name, title, "strict_lock", reason)

        # 2. Show native countdown modal in separate daemon thread if not already showing
        if not self.overlay_active:
            t = threading.Thread(target=self._show_overlay_window, args=(app_name, reason), daemon=True)
            t.start()

    def _show_overlay_window(self, app_name: str, reason: str):
        self.overlay_active = True
        try:
            import tkinter as tk
            from tkinter import ttk

            root = tk.Tk()
            root.title("Kairos 專注守護")
            root.attributes("-topmost", True)
            root.geometry("540x360")
            root.configure(bg="#0B0F19")
            root.resizable(False, False)

            # Center window on screen
            root.update_idletasks()
            w = 540
            h = 360
            x = (root.winfo_screenwidth() // 2) - (w // 2)
            y = (root.winfo_screenheight() // 2) - (h // 2)
            root.geometry(f"{w}x{h}+{x}+{y}")

            # Styling
            header = tk.Label(
                root, 
                text="⏳ KAIROS 專注干預", 
                font=("Segoe UI", 16, "bold"), 
                fg="#00E5FF", 
                bg="#0B0F19"
            )
            header.pack(pady=(25, 5))

            sub = tk.Label(
                root, 
                text=f"目標應用程式已遭鎖定：{app_name}", 
                font=("Segoe UI", 11), 
                fg="#E2E8F0", 
                bg="#0B0F19"
            )
            sub.pack(pady=5)

            reason_lbl = tk.Label(
                root, 
                text=f"原因：{reason}", 
                font=("Segoe UI", 10), 
                fg="#94A3B8", 
                bg="#0B0F19",
                wraplength=480
            )
            reason_lbl.pack(pady=5)

            remaining_sec = [45]  # 45 seconds cooldown
            timer_lbl = tk.Label(
                root, 
                text=f"強制冷卻倒數：{remaining_sec[0]} 秒", 
                font=("Segoe UI", 14, "bold"), 
                fg="#F43F5E", 
                bg="#0B0F19"
            )
            timer_lbl.pack(pady=15)

            def tick():
                if remaining_sec[0] > 0:
                    remaining_sec[0] -= 1
                    timer_lbl.config(text=f"強制冷卻倒數：{remaining_sec[0]} 秒")
                    root.after(1000, tick)
                else:
                    timer_lbl.config(text="冷卻結束，請保持專注！", fg="#10B981")
                    close_btn.config(state="normal", text="關閉提示", bg="#10B981", fg="#FFFFFF")

            btn_frame = tk.Frame(root, bg="#0B0F19")
            btn_frame.pack(pady=15)

            # Snooze button (if allowed)
            app_lower = app_name.lower()
            current_snooze = self.snooze_counts.get(app_lower, 0)
            
            def handle_snooze():
                if self.request_snooze(app_name, 5):
                    root.destroy()

            if current_snooze < self.max_snoozes_per_day:
                snooze_btn = tk.Button(
                    btn_frame,
                    text=f"延長 5 分鐘 (剩餘 {self.max_snoozes_per_day - current_snooze} 次)",
                    command=handle_snooze,
                    bg="#1E293B",
                    fg="#38BDF8",
                    font=("Segoe UI", 10),
                    padx=10,
                    pady=6,
                    relief="flat"
                )
                snooze_btn.pack(side="left", padx=10)

            close_btn = tk.Button(
                btn_frame,
                text="冷卻中...",
                state="disabled",
                command=root.destroy,
                bg="#334155",
                fg="#94A3B8",
                font=("Segoe UI", 10, "bold"),
                padx=15,
                pady=6,
                relief="flat"
            )
            close_btn.pack(side="left", padx=10)

            root.after(1000, tick)
            root.mainloop()
        except Exception as e:
            print(f"[Blocker] Error in overlay window: {e}")
        finally:
            self.overlay_active = False

# Global singleton
blocker = Blocker()
