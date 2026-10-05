# 🤖 Kairos Android 行動端使用指南

Kairos 支援兩種在 Android 手機上使用的方式：

---

## 方式 1：PWA 行動控制台 (推薦，零安裝)

1. 確認手機與電腦連線至相同的 **Wi-Fi** 區域網路。
2. 用手機瀏覽器 (Chrome / Edge) 開啟電腦控制台網址（例如：`http://192.168.1.107:5050`）。
3. 點選瀏覽器右上角選單 `⋮`，選擇 **「安裝應用程式」** 或 **「加到主畫面」**。
4. Kairos 即會以全螢幕原生 App 形式出現在您的 Android 桌面，您可以隨身：
   - 遠端啟動 / 暫停番茄鐘。
   - 即時監控電腦當前活躍程式。
   - 隨時調整每日使用上限與封鎖規則。

---

## 方式 2：Android 應用程式使用時間自動回傳 (進階)

若希望將 Android 手機上的 App 使用時間也同步彙整到 Kairos 中央 SQLite 資料庫：

### 透過 Termux 執行守護腳本
1. 在手機上下載安裝 [Termux](https://f-droid.org/packages/com.termux/)。
2. 在 Termux 中執行：
   ```bash
   pkg update && pkg install python -y
   ```
3. 下載或傳輸 `kairos_agent.py` 至手機，執行：
   ```bash
   python kairos_agent.py http://192.168.1.107:5050
   ```
4. 腳本每 5 秒將前台活躍 App 上報給 Kairos 後端，並在超額或專注時段觸發震動通知警示！
