# 📋 Kairos iPad / iOS 使用與自動化干預指南

Apple 的 iOS / iPadOS 系統具備嚴格的沙盒保護，第三方 App 無法在背景任意截取其他應用程式的前台焦點。  
因此，Kairos 為 iPad 設計了兼具 **高顏值 PWA 隨身控制台** 與 **iOS 捷徑 (Shortcuts) 原生防繞過連動** 的雙重解決方案。

---

## 方案 1：iPad PWA 獨立控制台 (即開即用)

1. 確認 iPad 與電腦連線至相同的 **Wi-Fi** 網路。
2. 在 iPad 上使用 **Safari** 瀏覽器開啟 Kairos 控制台：
   👉 `http://192.168.1.107:5050` (請依電腦顯示的 IP 為準)
3. 點擊 Safari 右上角（或下方）的 **「分享 (Share)」按鈕 ➔ 選擇「加入主畫面 (Add to Home Screen)」**。
4. iPad 桌面上將生成專屬的 **Kairos** App 圖示！點開即為沉浸式深色全螢幕控制台，零網址列遮擋。

---

## 方案 2：iPadOS 捷徑自動化 — 開啟分心 App 即刻驗證與防繞過

這是目前 iPad 上最原生且免越獄的防分心攔截機制：

### 設定步驟（只需 2 分鐘）：
1. 在 iPad 上打開內建的 **「捷徑 (Shortcuts)」** App。
2. 切換到底部的 **「自動化 (Automation)」** 標籤 ➔ 點擊右上角 `+` 新增自動化。
3. 選擇 **「App」**：
   - 設定為「當開啟」：勾選你想限制的 App（例如：YouTube, 串流影音, 遊戲）。
   - 勾選 **「立即執行 (Run Immediately)」**，關閉「執行前詢問」。
4. 點擊下一步，加入動作：
   - 動作 1：搜尋並加入 **「取得 URL 的內容 (Get Contents of URL)」**：
     - URL 填入：`http://192.168.1.107:5050/api/client/report`
     - 方法選擇：`POST`
     - 請求內文 (JSON)：
       ```json
       {
         "device_id": "my-ipad",
         "device_name": "我的 iPad",
         "device_type": "ipad",
         "app_name": "YouTube",
         "duration_sec": 30
       }
       ```
   - 動作 2：加入 **「從輸入取得字典值 (Get Dictionary Value)」**，鍵填入：`is_blocked`。
   - 動作 3：加入 **「如果 (If)」** 條件：
     - 如果 `is_blocked` 等於 `1` 或 `true`：
       - 加入動作：**「前往主畫面 (Go to Home Screen)」** (自動跳出該 App，強制關閉！)
       - 加入動作：**「顯示通知 (Show Notification)」**，提示「⏳ Kairos：專注時段已鎖定此應用！」
5. 完成儲存！現在只要電腦處於番茄鐘專注時段，在 iPad 開啟分心 App 就會被自動彈回主畫面！
