import sys
import uvicorn
import webbrowser
import threading
import time

from kairos.config import HOST, PORT
from kairos.database import init_db
from kairos.tracker import tracker
from kairos.api import get_server_lan_ip

def open_browser():
    time.sleep(1.2)
    webbrowser.open(f"http://127.0.0.1:{PORT}")

def main():
    lan_ip = get_server_lan_ip()
    print("=" * 65)
    print("   ⏳ KAIROS — 私有自建專注守護與時間統計系統 (跨平台版)   ")
    print("   100% 本地儲存 · 零第三方追蹤 · 支援 Windows / iPad / Android   ")
    print("=" * 65)

    # 1. Initialize SQLite Database
    print("[Kairos] 正在初始化本地資料庫 (SQLite)...")
    init_db()

    # 2. Start native window tracker daemon
    print("[Kairos] 正在啟動背景焦點與進程追蹤守護進程...")
    tracker.start()

    # 3. Connection URLs
    print("\n" + "-" * 65)
    print(f"  💻 電腦本地儀表板：   http://127.0.0.1:{PORT}")
    print(f"  📱 iPad / Android 連結： http://{lan_ip}:{PORT}")
    print("  (請確保 iPad 與手機連線至相同的 Wi-Fi 區域網路)")
    print("-" * 65 + "\n")

    threading.Thread(target=open_browser, daemon=True).start()

    # 4. Start FastAPI server on 0.0.0.0 for LAN access
    try:
        uvicorn.run(
            "kairos.api:app",
            host=HOST,
            port=PORT,
            reload=False,
            log_level="info"
        )
    except KeyboardInterrupt:
        print("\n[Kairos] 收到退出信號，正在安全停止追蹤線程...")
    finally:
        tracker.stop()
        print("[Kairos] 已停止運作。所有數據已安全保存至本地。")

if __name__ == "__main__":
    main()
