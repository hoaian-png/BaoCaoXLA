@echo off
chcp 65001 >nul
title KHỞI CHẠY TỰ ĐỘNG ĐỒ ÁN XỬ LÝ ẢNH (DÀNH CHO MÁY MỚI / MÁY KHÁC)
cd /d "%~dp0"

echo ==============================================================================
echo      HỆ THỐNG NHẬN DIỆN VÀ ĐẾM XE TRONG BÃI ĐỖ XE (YOLOv8 ^& OPENCV)
echo ==============================================================================
echo.
echo [1/3] Đang kiểm tra môi trường Python trên máy tính của bạn...

python --version >nul 2>&1
if %errorlevel% neq 0 (
    echo.
    echo ❌ MÁY BẠN CHƯA CÀI PYTHON HOẶC CHƯA BẬT PATH!
    echo 👉 Vui lòng tải và cài đặt Python từ: https://www.python.org/downloads/
    echo ⚠️ LƯU Ý KHI CÀI: Nhớ tích chọn ô "[x] Add Python to PATH" ở bước đầu tiên!
    echo.
    pause
    start https://www.python.org/downloads/
    exit /b
)

for /f "tokens=*" %%i in ('python --version') do set PY_VER=%%i
echo ✅ Đã phát hiện: %PY_VER%

echo.
echo [2/3] Đang kiểm tra và tự động cài đặt các thư viện cần thiết...
echo     (Quá trình này chỉ chạy 1 lần duy nhất trong lần đầu tiên)
echo.

pip install ultralytics opencv-python pillow flask numpy --quiet --disable-pip-version-check

echo ✅ Môi trường đã sẵn sàng 100%!
echo.
echo [3/3] Đang khởi chạy chương trình xử lý ảnh (main.py)...
echo ==============================================================================
echo.

python main.py

echo.
echo Chương trình đã kết thúc. Nhấn phím bất kỳ để đóng cửa sổ.
pause >nul
