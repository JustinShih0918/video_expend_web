#!/bin/bash

# ==========================================
#      AI Video Expand - Unified Installer
# ==========================================

echo "[Setup] 初始化安裝..."

# 1. 偵測作業系統 (OS Detection)
OS="$(uname -s)"
case "${OS}" in
    CYGWIN*|MINGW*|MSYS*) IS_WIN=true ;;
    *) IS_WIN=false ;;
esac

if [ "$IS_WIN" = true ]; then
    echo "偵測到環境: Windows (Git Bash)"
else
    echo "偵測到環境: Mac / Linux"
fi

# ------------------------------------------
# 2. 檢查必要工具
# ------------------------------------------
echo "[1/3] 檢查系統工具..."

# 檢查 Python
if command -v python3 &> /dev/null; then
    PY_CMD=python3
elif command -v python &> /dev/null; then
    PY_CMD=python
else
    echo "[ERROR] 找不到 Python！請先安裝 Python 3.9+。"
    exit 1
fi
echo "Python found ($PY_CMD)"

# 檢查 Node.js
if ! command -v npm &> /dev/null; then
    echo "[ERROR] 找不到 npm！請先安裝 Node.js LTS 版本。"
    exit 1
fi
echo "Node.js (npm) found"

# 檢查 FFmpeg (Windows 無法自動安裝，只能檢查)
if ! command -v ffmpeg &> /dev/null; then
    if [ "$IS_WIN" = true ]; then
        echo "[WARNING] 未偵測到 FFmpeg。"
        echo "   請務必手動下載 FFmpeg 並將 bin 資料夾加入環境變數 Path。"
    else
        echo "未偵測到 FFmpeg，嘗試透過 Homebrew 安裝..."
        if command -v brew &> /dev/null; then
            brew install ffmpeg
        else
            echo "[ERROR] 請先安裝 Homebrew 或手動安裝 FFmpeg。"
            exit 1;
        fi
    fi
else
    echo "FFmpeg found"
fi

# ------------------------------------------
# 3. 設定後端 (Python)
# ------------------------------------------
echo "[2/3] 設定後端環境 (backend)..."
cd backend

# 建立虛擬環境
if [ ! -d ".venv" ]; then
    echo "   建立虛擬環境 (.venv)..."
    $PY_CMD -m venv .venv
else
    echo "   虛擬環境已存在"
fi

# 啟動虛擬環境 (處理路徑差異)
if [ "$IS_WIN" = true ]; then
    source .venv/Scripts/activate
else
    source .venv/bin/activate
fi

echo "   安裝 Python 套件 (requirements.txt)..."
# 升級 pip 並安裝依賴
python -m pip install --upgrade pip > /dev/null 2>&1
python -m pip install -r requirements.txt

echo "   後端設定完成"

# ------------------------------------------
# 4. 設定前端 (Node.js)
# ------------------------------------------
echo "[3/3] 設定前端環境 (frontend)..."
cd ../frontend

if [ ! -d "node_modules" ]; then
    echo "   正在下載前端套件 (npm install)..."
    echo "      (這通常需要幾分鐘，請稍候)"
    npm install
else
    echo "   node_modules 已存在 (若需更新請刪除該資料夾重跑腳本)"
fi

echo "   前端設定完成"

# ------------------------------------------
# 5. 結束
# ------------------------------------------
echo ""
echo "==================================="
echo "   安裝全部完成！"
echo "   請執行 ./run.sh 來啟動專案"
echo "======================================"