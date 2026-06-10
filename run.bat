@echo off
title YouTube Auto Clipper
cd /d "%~dp0"
cls

echo ============================================
echo    YOUTUBE AUTO CLIPPER - 6 SHORTS DAILY
echo ============================================
echo.

:: Check Python
where py >nul 2>nul
if %errorlevel% neq 0 (
    echo [ERROR] Python not found! Install Python from python.org
    pause
    exit /b 1
)

:: Check yt-dlp
py -c "import yt_dlp" 2>nul
if %errorlevel% neq 0 (
    echo [SETUP] Installing yt-dlp...
    py -m pip install yt-dlp
)

:: Check Flask (for status display)
py -c "import flask" 2>nul
if %errorlevel% neq 0 (
    echo [SETUP] Installing Flask...
    py -m pip install flask
)

:: Check Google API (for upload)
py -c "import googleapiclient" 2>nul
if %errorlevel% neq 0 (
    echo [SETUP] Installing Google API...
    py -m pip install google-api-python-client google-auth-oauthlib
)

:: Check ffmpeg
ffmpeg -version >nul 2>nul
if %errorlevel% neq 0 (
    echo [WARNING] ffmpeg not found. Video clipping won't work.
    echo Install from: https://ffmpeg.org/download.html
    echo.
)

:: Check client_secret.json
if not exist "client_secret.json" (
    echo [WARNING] client_secret.json not found! YouTube upload will be SKIPPED.
    echo Clips will still be created in the 'clips' folder.
    echo Get it from: https://console.cloud.google.com
    echo.
)

echo [STARTING] Pipeline will now run...
echo [INFO] Finding trending video, checking safety, clipping into 6 shorts.
echo [INFO] This may take several minutes. Do not close this window.
echo.
echo Press CTRL+C at any time to stop.
echo ============================================
echo.

:: Run the pipeline
py daily_pipeline.py

echo.
echo ============================================
if %errorlevel% equ 0 (
    echo [DONE] Pipeline completed successfully!
) else (
    echo [DONE] Pipeline finished with some issues.
)
echo Check 'clips' folder for output.
echo ============================================
echo.
pause
