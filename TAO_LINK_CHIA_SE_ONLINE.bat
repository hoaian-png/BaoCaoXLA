@echo off
chcp 65001 >nul
title TẠO ĐƯỜNG LINK ONLINE CHIA SẺ RA INTERNET CHO BÀI BÁO CÁO
cd /d "%~dp0"

echo ==============================================================================
echo    ĐỒ ÁN XỬ LÝ ẢNH SỐ: CÔNG CỤ TẠO LINK CHIA SẺ TRỰC TUYẾN RA INTERNET
echo ==============================================================================
echo.
echo ⚠️ LƯU Ý QUAN TRỌNG:
echo   - Hãy đảm bảo bạn ĐANG BẬT server web (chạy chay_main.bat ở chế độ 2)
echo   - Không tắt cửa sổ này trong suốt thời gian người khác đang xem web.
echo.
echo 🚀 ĐANG KẾT NỐI VÀ TẠO LINK CÔNG KHAI (KHÔNG CẦN CÀI ĐẶT THÊM GÌ)...
echo.
echo ==============================================================================
echo 👉 Bạn hãy nhìn dòng có chữ "https://..." bên dưới:
echo    Đó chính là đường LINK ONLINE để gửi cho người khác hoặc thầy cô truy cập!
echo ==============================================================================
echo.

ssh -o StrictHostKeyChecking=no -R 80:localhost:5000 nokey@localhost.run

pause
