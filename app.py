# ============================================================
# FILE: app.py
# THÀNH VIÊN PHỤ TRÁCH: Thành viên 3 (Chuyên Backend Flask & Khởi Tạo)
# MÔ TẢ: Khởi tạo ứng dụng Flask, liên kết các module AI & Video
# ============================================================

import os
import sys

# Đảm bảo console trên Windows không bị lỗi UnicodeEncodeError khi in tiếng Việt
if sys.platform.startswith("win"):
    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
        sys.stderr.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass

from flask import Flask
from detector import VehicleDetector
from video_processor import VideoProcessor
from routes import create_routes


def create_app():
    """
    Hàm Factory khởi tạo toàn bộ ứng dụng:
    1. Flask App
    2. Model AI nhận diện phương tiện (YOLOv8)
    3. Bộ xử lý video & HUD hiển thị (OpenCV + PIL)
    4. Đăng ký các Endpoint & API Route
    """
    app = Flask(__name__)
    app.config["UPLOAD_FOLDER"] = os.path.join(os.path.dirname(os.path.abspath(__file__)), "uploads")
    os.makedirs(app.config["UPLOAD_FOLDER"], exist_ok=True)

    print("[APP] Đang nạp mô hình AI...")
    # Khởi tạo detector với bản Nano siêu nhẹ 'yolov8n.pt'
    detector = VehicleDetector(model_path="yolov8n.pt", confidence=0.45)

    print("[APP] Khởi tạo bộ xử lý đồ họa & video...")
    video_proc = VideoProcessor()

    print("[APP] Đăng ký các tuyến đường API...")
    create_routes(app, detector, video_proc, upload_folder=app.config["UPLOAD_FOLDER"])

    return app


# ============================================================
# ĐIỂM BẮT ĐẦU CHẠY ỨNG DỤNG (Local Server)
# Lệnh chạy: python app.py
# ============================================================
if __name__ == "__main__":
    app = create_app()

    port = int(os.environ.get("FLASK_PORT", 5000))
    host = os.environ.get("FLASK_HOST", "127.0.0.1")

    print("\n" + "=" * 65)
    print("  🚗 HỆ THỐNG NHẬN DIỆN & ĐẾM XE TRONG BÃI ĐỖ (VIDEO TRỰC TIẾP)")
    print(f"  🌐 Truy cập giao diện web tại: http://{host}:{port}")
    print("  ⏹  Nhấn Ctrl + C để dừng máy chủ")
    print("=" * 65 + "\n")

    # threaded=True để xử lý đồng thời luồng video MJPEG và các truy vấn API
    app.run(host=host, port=port, debug=False, threaded=True)
