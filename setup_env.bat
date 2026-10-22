@echo off
chcp 65001 >nul
echo ========================================================
echo   CÀI ĐẶT MÔI TRƯỜNG AI VIDEO TRANSLATOR & DUBBING
echo ========================================================
echo.

REM 1. Kiểm tra Python
python --version >nul 2>&1
if %errorlevel% neq 0 (
    echo [LỖI] Chưa tìm thấy Python. Vui lòng cài Python 3.10 - 3.12 từ python.org
    pause
    exit /b 1
)
echo [OK] Đã tìm thấy Python.

REM 2. Kiểm tra FFmpeg
ffmpeg -version >nul 2>&1
if %errorlevel% neq 0 (
    echo [CẢNH BÁO] Chưa cài FFmpeg trên PATH!
    echo Đang tự động tải FFmpeg essentials...
    curl -L -o ffmpeg.zip https://www.gyan.dev/ffmpeg/builds/ffmpeg-release-essentials.zip
    echo Hãy giải nén ffmpeg.zip và thêm thư mục bin vào PATH hệ thống!
) else (
    echo [OK] Đã tìm thấy FFmpeg.
)

REM 3. Cài đặt các gói pip
echo.
echo Đang cài đặt các thư viện Python cần thiết...
pip install -r requirements.txt

echo.
echo ========================================================
echo [HOÀN TẤT] Môi trường đã sẵn sàng!
echo Chạy thử: python examples/example_download.py
echo ========================================================
pause
