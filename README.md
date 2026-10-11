# 🚗 HỆ THỐNG NHẬN DIỆN VÀ ĐẾM SỐ LƯỢNG XE TRONG BÃI ĐỖ (VIDEO TRỰC TIẾP)

Đồ án môn học **Xử Lý Ảnh Số** thực hiện bởi **Nhóm 6 Thành Viên**.
Ứng dụng công nghệ: **Python**, **YOLOv8 (Ultralytics)**, **OpenCV**, **Flask Framework**, **HTML5/CSS3/JavaScript**.

---

## 👥 BẢNG PHÂN CÔNG NHIỆM VỤ (6 THÀNH VIÊN)

| STT | Thành Viên | Vai Trò | File Đảm Nhận | Nhiệm Vụ Chi Tiết |
| :---: | :--- | :--- | :--- | :--- |
| **1** | Thành viên 1 | **Chuyên gia AI / YOLO** | `detector.py` | Tải và cấu hình mô hình YOLOv8, trích xuất tọa độ Bounding Box, phân loại 4 nhóm phương tiện (Ô tô, Xe máy, Xe buýt, Xe tải), đếm số lượng tức thời. |
| **2** | Thành viên 2 | **Chuyên gia OpenCV / Xử Lý Ảnh** | `video_processor.py` | Đọc khung hình, tính toán FPS, vẽ Bounding Box màu theo loại xe, vẽ bảng thông số HUD tiếng Việt bằng Pillow (không lỗi font), mã hóa JPEG. |
| **3** | Thành viên 3 | **Backend Flask (Khởi tạo)** | `app.py` | Tạo ứng dụng Flask, cấu hình đường dẫn upload, mã hóa UTF-8 console Windows, liên kết các module và điều phối cổng chạy local server. |
| **4** | Thành viên 4 | **Backend Flask (API & Luồng)** | `routes.py` | Xây dựng các API `/api/start`, `/api/stop`, `/api/stats`, `/api/upload`, stream video MJPEG `/video_feed`, quản lý phiên đa luồng an toàn. |
| **5** | Thành viên 5 | **Frontend Developer (Layout & Logic)** | `templates/index.html`<br>`static/js/main.js` | Thiết kế cấu trúc giao diện Dashboard, viết logic gọi API, polling cập nhật số liệu realtime, xử lý tải file video từ máy tính. |
| **6** | Thành viên 6 | **Frontend UI/UX (Thiết Kế & CSS)** | `static/css/style.css` | Thiết kế giao diện Dark Mode công nghệ cao, responsive đa kích thước màn hình, hiệu ứng ánh sáng neon, animation nhảy số và chuẩn accessibility. |

---

## 📁 CẤU TRÚC THƯ MỤC DỰ ÁN

```text
C:\BaoCao\BaoCaoXLA\
│
├── app.py                  # [TV3] File chính khởi chạy Flask Server
├── detector.py             # [TV1] Module AI YOLOv8 nhận diện và phân loại xe
├── video_processor.py      # [TV2] Module OpenCV xử lý ảnh và vẽ HUD tiếng Việt
├── routes.py               # [TV4] Module định tuyến API, video stream và upload
├── requirements.txt        # Danh sách thư viện phụ thuộc
├── run.bat                 # Phím tắt click đúp chạy nhanh trên Windows
├── README.md               # Hướng dẫn chi tiết đồ án
│
├── templates/
│   └── index.html          # [TV5] Giao diện Dashboard HTML5
│
├── static/
│   ├── css/
│   │   └── style.css       # [TV6] Giao diện Dark Theme hiện đại
│   └── js/
│       └── main.js         # [TV5] Logic JavaScript thời gian thực
│
└── uploads/                # Thư mục lưu các file video tải lên thử nghiệm
```

---

## 🚀 HƯỚNG DẪN KHỞI CHẠY TRÊN MÁY TÍNH (VS CODE)

### Cách 1: Chạy nhanh bằng 1 click (Tiện nhất)
1. Mở thư mục `C:\BaoCao\BaoCaoXLA` trong File Explorer của Windows.
2. Nhấp đúp chuột vào file **`run.bat`**.
3. Hệ thống sẽ tự động khởi động máy chủ và mở trình duyệt web tại `http://127.0.0.1:5000`.

---

### Cách 2: Chạy bằng Terminal trong VS Code
1. Mở thư mục `C:\BaoCao\BaoCaoXLA` bằng **VS Code**.
2. Mở Terminal tích hợp (`Ctrl + ~` hoặc `Terminal -> New Terminal`).
3. Cài đặt các thư viện (nếu chưa cài):
   ```bash
   pip install -r requirements.txt
   ```
4. Khởi chạy máy chủ:
   ```bash
   python app.py
   ```
5. Mở trình duyệt web bất kỳ (Chrome, Edge, Cốc Cốc...) và truy cập địa chỉ:
   ```text
   http://127.0.0.1:5000
   ```

---

## 🎯 CÁCH SỬ DỤNG GIAO DIỆN WEB

1. **Sử dụng Webcam trực tiếp:**
   - Chọn tab **📷 Webcam** (mặc định Camera 0).
   - Nhấn nút **▶ BẮT ĐẦU** để xem video và đếm xe.
2. **Kiểm thử bằng File Video:**
   - Chọn tab **📁 Tải File Video** -> Nhấn **Chọn Video Từ Máy Tính...** để chọn file video mẫu (ví dụ: `.mp4`).
   - Sau khi tải lên thành công, nhấn **▶ BẮT ĐẦU** để phân tích.
3. **Kiểm thử bằng Camera IP / RTSP:**
   - Chọn tab **🌐 Nhập Link / RTSP** -> Nhập địa chỉ luồng camera.
   - Nhấn **▶ BẮT ĐẦU**.
4. **Điều chỉnh độ nhạy (Confidence):**
   - Kéo thanh trượt **Độ tin cậy** (mặc định 45%) để lọc các vật thể nhận diện chính xác nhất.
5. **Dừng hệ thống:**
   - Nhấn **⏹ DỪNG** để giải phóng camera và đặt lại số liệu về 0.
