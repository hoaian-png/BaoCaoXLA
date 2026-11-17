# 🚗 HỆ THỐNG NHẬN DIỆN VÀ ĐẾM SỐ LƯỢNG XE TRONG BÃI ĐỖ (VIDEO TRỰC TIẾP)

Đồ án môn học **Xử Lý Ảnh Số** thực hiện bởi **Nhóm 6 Thành Viên**.
Ứng dụng công nghệ: **Python**, **YOLOv8 (Ultralytics)**, **OpenCV**, **Flask Framework**, **HTML5/CSS3/JavaScript**.

---

## 📁 CẤU TRÚC THƯ MỤC DỰ ÁN

```text
BaoCaoXLA/
│
├── app.py                  # [TV3] File chính khởi chạy Flask Server
├── detector.py             # [TV1] Module AI YOLOv8 nhận diện và phân loại xe
├── video_processor.py      # [TV2] Module OpenCV xử lý ảnh và vẽ HUD tiếng Việt
├── routes.py               # [TV4] Module định tuyến API, video stream và upload
├── requirements.txt        # Thư viện cho dashboard OpenCV và Vercel
├── requirements-local.txt  # Thư viện cho bản YOLOv8 cục bộ
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

## Cài đặt và sử dụng trên Windows

Dùng Python 3.11 64-bit và Git. Tạo môi trường ảo trong thư mục dự án:

```powershell
git clone https://github.com/hoaian-png/BaoCaoXLA.git
cd BaoCaoXLA
py -3.11 -m venv .venv
```

### Chạy dashboard với OpenCV

Dùng bản này để thử dữ liệu mẫu, tải ảnh, dùng webcam từ trình duyệt và thử các bộ lọc xử lý ảnh. Bản triển khai Vercel dùng cùng điểm khởi chạy `api/index.py`.

```powershell
.\.venv\Scripts\python.exe -X utf8 -m pip install -r requirements.txt
.\.venv\Scripts\python.exe -m flask --app api.index run
```

Mở [http://127.0.0.1:5000](http://127.0.0.1:5000).

1. Chọn **Demo Mẫu** rồi bấm **Nạp Lại Dữ Liệu Mẫu** để xem ảnh đã đánh dấu và số lượng xe.
2. Chọn **Tải Ảnh / Video** và chọn một ảnh JPG hoặc PNG để phân tích. Luồng tải video hiện lưu được tệp, còn nút **Bắt đầu** chưa khởi chạy phân tích video đã tải.
3. Chọn **Webcam**, bấm **Bắt đầu** và cấp quyền camera cho trình duyệt. Bấm **Dừng** khi hoàn tất.
4. Chọn **Thí Nghiệm Xử Lý Ảnh** và bấm bộ lọc, ví dụ **Tách Biên Canny**, để xem kết quả trên ảnh mẫu.

Xem thêm [hướng dẫn triển khai Vercel](HUONG_DAN_VERCEL.md).

### Chạy YOLOv8 với video mẫu

```powershell
py -3.11 -m venv venv
.\venv\Scripts\python.exe -X utf8 -m pip install -r requirements-local.txt
.\venv\Scripts\python.exe app.py
```

Lần đầu cần Internet để tải `yolov8n.pt`. Giữ máy chủ chạy và mở PowerShell thứ hai tại thư mục dự án:

```powershell
$settings = @{ source = 'uploads/sample_parking_demo.mp4'; confidence = 0.45 } | ConvertTo-Json
Invoke-RestMethod 'http://127.0.0.1:5000/api/start' -Method Post -ContentType 'application/json' -Body $settings
```

Mở [luồng video đã đánh dấu](http://127.0.0.1:5000/video_feed) và xem [thống kê hiện tại](http://127.0.0.1:5000/api/stats). Để dùng webcam của máy chủ, đổi giá trị `source` thành số `0`. Để dừng phiên, gọi:

```powershell
Invoke-RestMethod 'http://127.0.0.1:5000/api/stop' -Method Post
```

Trong bản YOLOv8, các mục demo, ảnh và bộ lọc trên dashboard cần những API hiện chỉ có ở bản OpenCV. `run.bat` cũng chạy bản YOLOv8 và dùng lệnh `python` từ môi trường đang hoạt động. Nhấn **Ctrl+C** ở terminal chạy Flask để tắt máy chủ.
