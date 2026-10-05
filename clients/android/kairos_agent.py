#!/usr/bin/env python3
"""
Kairos Android Client Agent (Termux / Pydroid / Background Daemon)
Periodically inspects foreground package and syncs with private Kairos backend.
"""

import sys
import time
import subprocess
import json
import urllib.request
import urllib.error

# CHANGE THIS TO YOUR COMPUTER'S LAN IP (Shown on Kairos PC Dashboard)
KAIROS_SERVER = "http://192.168.1.107:5050"
DEVICE_ID = "android-phone"
DEVICE_NAME = "我的 Android 手機"
INTERVAL_SECONDS = 5.0

def get_current_app_android():
    """Detect foreground app on Android via Termux or ADB API."""
    try:
        # Method 1: Termux / dumpsys
        out = subprocess.check_output(
            ["dumpsys", "window", "windows"], 
            stderr=subprocess.DEVNULL, 
            timeout=2
        ).decode('utf-8', errors='ignore')
        
        for line in out.splitlines():
            if "mCurrentFocus" in line or "mFocusedApp" in line:
                parts = line.strip().split()
                for p in parts:
                    if "/" in p and not p.startswith("u0"):
                        pkg = p.split("/")[0].replace("{", "").replace("}", "")
                        return pkg
    except Exception:
        pass
    
    # Method 2: Fallback to generic Android activity
    return "com.android.launcher"

def report_to_kairos(pkg_name, duration):
    url = f"{KAIROS_SERVER}/api/client/report"
    payload = {
        "device_id": DEVICE_ID,
        "device_name": DEVICE_NAME,
        "device_type": "android",
        "app_name": pkg_name,
        "window_title": pkg_name,
        "duration_sec": duration,
        "is_idle": False
    }
    
    req = urllib.request.Request(
        url,
        data=json.dumps(payload).encode('utf-8'),
        headers={'Content-Type': 'application/json'},
        method='POST'
    )
    
    try:
        with urllib.request.urlopen(req, timeout=3) as resp:
            data = json.loads(resp.read().decode('utf-8'))
            if data.get("is_blocked"):
                print(f"[Kairos Blocked] {pkg_name} 已受限！原因：{data.get('reason')}")
                # Play Android vibration or notification via termux-vibrate / termux-notification
                subprocess.run(["termux-vibrate", "-d", "500"], stderr=subprocess.DEVNULL)
                subprocess.run(["termux-notification", "--title", "⏳ Kairos 專注鎖定", "--content", data.get("reason", "分心限制")], stderr=subprocess.DEVNULL)
            else:
                print(f"[Kairos Synced] {pkg_name} (+{duration}s)")
    except Exception as e:
        print(f"[Kairos Sync Error] 無法連線至伺服器 ({e})")

def main():
    print("=" * 50)
    print(f"⏳ Kairos Android 客戶端正在運行...")
    print(f"中央伺服器：{KAIROS_SERVER}")
    print("=" * 50)

    last_pkg = ""
    while True:
        pkg = get_current_app_android()
        report_to_kairos(pkg, INTERVAL_SECONDS)
        time.sleep(INTERVAL_SECONDS)

if __name__ == "__main__":
    if len(sys.argv) > 1:
        KAIROS_SERVER = sys.argv[1].rstrip("/")
    main()
