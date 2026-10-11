@echo off
chcp 65001 >nul
title HƯỚNG DẪN ĐẨY CODE LÊN GITHUB & DEPLOY VERCEL
color 0b

echo ======================================================================
echo    🚗 HƯỚNG DẪN DEPLOY DỰ ÁN LÊN VERCEL TRONG 2 PHÚT (MIỄN PHÍ)
echo ======================================================================
echo.
echo  Dự án đã được cấu hình hoàn chỉnh các file cần thiết cho Vercel:
echo    [✓] vercel.json (Định tuyến Serverless)
echo    [✓] api/index.py (Entry point Flask WSGI)
echo    [✓] requirements.txt (Dependencies nhẹ dưới 250MB)
echo    [✓] Đã tạo Git commit ban đầu trên nhánh 'main'
echo.
echo ======================================================================
echo  BƯỚC 1: TẠO REPOSITORY TRÊN GITHUB
echo ======================================================================
echo  1. Mở trình duyệt vào: https://github.com/new
echo  2. Điền Repository name: smart-parking (hoặc tên tuỳ chọn)
echo  3. Chọn chế độ Public
echo  4. KHÔNG tích chọn "Add a README file"
echo  5. Bấm nút xanh "Create repository"
echo.
echo ======================================================================
echo  BƯỚC 2: LIÊN KẾT VÀ ĐẨY CODE (PUSH)
echo ======================================================================
echo.
set /p REPO_URL="Dán link GitHub vừa tạo vào đây (Ví dụ: https://github.com/hoaian-png/smart-parking.git): "

if "%REPO_URL%"=="" (
    echo.
    echo [!] Bạn chưa nhập link. Vui lòng chạy lại file khi đã tạo repo!
    pause
    exit /b
)

echo.
echo Đang liên kết remote origin...
git remote remove origin 2>nul
git remote add origin %REPO_URL%

echo Đang đẩy code lên GitHub (git push -u origin main)...
git push -u origin main

if %ERRORLEVEL% NEQ 0 (
    echo.
    echo [!] Nếu gặp lỗi xác thực GitHub, bạn hãy mở GitHub Desktop hoặc đăng nhập Git Credential.
    echo [!] Hoặc bạn có thể dùng lệnh: git push -u origin main
    echo.
) else (
    echo.
    echo ======================================================================
    echo  [✓] ĐÃ PUSH CODE LÊN GITHUB THÀNH CÔNG!
    echo ======================================================================
    echo.
    echo  BƯỚC 3: DEPLOY TRÊN VERCEL (1 CÚ CLICK)
    echo  ------------------------------------------------------------------
    echo  1. Mở trình duyệt vào: https://vercel.com/new
    echo  2. Đăng nhập bằng tài khoản GitHub (hoaian-png)
    echo  3. Tìm repo vừa tạo và bấm nút "Import"
    echo  4. Giữ nguyên tất cả cài đặt mặc định, bấm nút "Deploy"
    echo  5. Đợi ~30 giây, Vercel sẽ cấp link online vĩnh viễn dạng:
    echo     👉 https://smart-parking-xxx.vercel.app
    echo.
    echo  Link này bất kỳ ai (thầy cô, bạn bè) đều mở được trên máy tính hay điện thoại!
    echo ======================================================================
)

echo.
pause
