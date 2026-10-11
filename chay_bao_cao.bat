@echo off
chcp 65001 >nul
title CHƯƠNG TRÌNH THỰC NGHIỆM & BÁO CÁO XỬ LÝ ẢNH (YOLOv8 & OPENCV)
cd /d "%~dp0"

echo ===================================================================
echo     ĐỒ ÁN XỬ LÝ ẢNH SỐ: NHẬN DIỆN & ĐẾM XE BÃI ĐỖ XE
echo     KHỞI CHẠY FILE CODE BÁO CÁO: bao_cao_xulyanh.py
echo ===================================================================
echo.

python bao_cao_xulyanh.py

pause
