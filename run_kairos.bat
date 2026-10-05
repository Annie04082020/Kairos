@echo off
chcp 65001 >nul
title Kairos - 專注守護與時間統計系統

echo ========================================================
echo   ⏳ KAIROS (自建版 StayFree 跨平台專注系統)
echo   100%% 本地儲存 · 支援 Windows / iPad / Android
echo ========================================================
echo.

cd /d "%~dp0"

echo [1/2] 正在檢查 Python 執行環境...
python --version >nul 2>&1
if %errorlevel% neq 0 (
    echo [錯誤] 找不到 Python！請確保已安裝 Python 3.10+ 並加入 PATH 環境變數。
    pause
    exit /b 1
)

echo [2/2] 正在啟動 Kairos 守護進程與 Web 控制台...
echo.
echo 控制台即將於瀏覽器開啟：http://127.0.0.1:5050
echo 按 Ctrl + C 可安全停止服務。
echo.

python -m kairos.main
pause
