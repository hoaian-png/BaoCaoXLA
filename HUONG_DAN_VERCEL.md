# 🚀 Hướng Dẫn Triển Khai (Deploy) Lên Vercel

Dự án **Smart Parking Monitor - Báo Cáo Xử Lý Ảnh Số** đã được cấu hình hoàn chỉnh để triển khai trực tiếp lên đám mây **Vercel Serverless**.

---

## 📌 1. Các File Cấu Hình Đã Được Tối Ưu Cho Vercel

1. **`vercel.json`**: Định tuyến toàn bộ yêu cầu web và API vào hàm Serverless Python `@vercel/python`.
2. **`api/index.py`**: Điểm khởi chạy WSGI Flask Serverless, tích hợp:
   - Dashboard thời gian thực
   - Thuật toán Xử Lý Ảnh Số: **Canny, Sobel, Otsu, Histogram Equalization, Morphology, HSV**
   - Thuật toán phát hiện phương tiện & đếm xe thông minh bằng OpenCV
   - API phân tích ảnh, video và webcam HTML5
3. **`requirements.txt`**: Tối ưu dung lượng **dưới 250MB** (OpenCV Headless, Pillow, NumPy, Flask) đảm bảo Vercel build nhanh trong 20s và không bị giới hạn bộ nhớ.
4. **`requirements-local.txt`**: Giữ nguyên môi trường YOLOv8 Nano đầy đủ cho việc chạy offline cục bộ trên máy tính.
5. **`.gitignore`**: Loại bỏ các video nặng và file nhị phân lớn để repo nhẹ (< 3MB), đẩy code lên GitHub chỉ mất 3 giây.

---

## ⚡ 2. Quy Trình 3 Bước Triển Khai Lên Vercel (Miễn Phí 100%)

### **Bước 1: Tạo Repository mới trên GitHub**
1. Truy cập [https://github.com/new](https://github.com/new).
2. Đặt tên kho lưu trữ: `smart-parking` (hoặc tên tùy chọn).
3. Chọn quyền riêng tư là **Public**.
4. **Không** tích chọn *"Add a README file"*.
5. Bấm nút xanh **"Create repository"**.
6. Sao chép đường link HTTPS của repo (Ví dụ: `https://github.com/hoaian-png/smart-parking.git`).

---

### **Bước 2: Đẩy Code Lên GitHub**
Bạn có thể nhấp đúp chạy file **`DAY_LEN_GITHUB_VA_VERCEL.bat`** và dán link vừa tạo, **HOẶC** mở PowerShell tại thư mục này và gõ:

```powershell
git remote add origin https://github.com/hoaian-png/smart-parking.git
git push -u origin main
```

---

### **Bước 3: Bấm Deploy trên Vercel (1 Click)**
1. Truy cập [https://vercel.com/new](https://vercel.com/new).
2. Đăng nhập bằng tài khoản GitHub (`hoaian-png`).
3. Trong danh sách repositories, tìm `smart-parking` và bấm nút **"Import"**.
4. Giữ nguyên toàn bộ cấu hình mặc định, sau đó bấm nút **"Deploy"**.
5. Chờ khoảng **20 - 30 giây**, Vercel sẽ cấp một đường link trực tuyến vĩnh viễn có dạng:
   👉 **`https://smart-parking-xxx.vercel.app`**

---

## 🌟 3. Các Tính Năng Có Thể Trình Chiếu Trên Vercel

Khi người khác truy cập link Vercel từ điện thoại hoặc máy tính:
- **🚗 1-Click Demo Bãi Đỗ:** Nhấn xem ngay phân tích bãi đỗ với 33 phương tiện được đóng khung Bounding Box và thống kê tỉ lệ lấp đầy.
- **📷 Camera Thiết Bị (HTML5 Webcam):** Người xem cấp quyền camera trên điện thoại/laptop để hệ thống nhận diện vật thể trực tiếp.
- **📁 Tải Ảnh / Video Bãi Đỗ:** Cho phép người dùng tải ảnh từ máy lên để phân tích số lượng xe tức thì.
- **🔬 Phòng Thí Nghiệm Xử Lý Ảnh:** Bấm thử các thuật toán kinh điển môn Xử Lý Ảnh (**Canny**, **Sobel**, **Otsu**, **Cân bằng Histogram**, **Hình thái học ảnh**, **Không gian HSV**) kèm giải thích cơ sở toán học trực quan!
