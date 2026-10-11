@echo off
chcp 65001 >nul
title Hệ Thống Nhận Diện Xe Bãi Đỗ - Smart Parking

echo ====================================================================
echo    🚗 ĐỒ ÁN XỬ LÝ ẢNH - HỆ THỐNG NHẬN DIỆN VÀ ĐẾM XE BÃI ĐỖ
echo ====================================================================
echo.
echo [1/2] Đang khởi động máy chủ Flask Local...
echo [2/2] Trình duyệt sẽ tự động mở sau vài giây...
echo.

start "" http://127.0.0.1:5000
python app.py

pause
