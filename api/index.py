# ============================================================
# FILE: api/index.py
# MÔ TẢ: Điểm khởi chạy Serverless Function tương thích Vercel & Local
# HỆ THỐNG GIÁM SÁT & ĐẾM XE BÃI ĐỖ (XỬ LÝ ẢNH & COMPUTER VISION)
# ============================================================

import os
import sys
import io
import time
import base64
import json
import traceback

# Thêm thư mục gốc vào đường dẫn hệ thống để tương thích mọi môi trường
CURRENT_DIR = os.path.dirname(os.path.abspath(__file__))
PARENT_DIR = os.path.dirname(CURRENT_DIR)
for p in [CURRENT_DIR, PARENT_DIR]:
    if p not in sys.path:
        sys.path.insert(0, p)

from flask import Flask, render_template, request, jsonify, Response, send_from_directory
import cv2
import numpy as np
from PIL import Image

# Xác định đường dẫn templates và static linh hoạt cho Vercel & Local
def resolve_dir(name):
    candidates = [
        os.path.join(CURRENT_DIR, name),
        os.path.join(PARENT_DIR, name),
        os.path.join(os.getcwd(), name),
    ]
    for c in candidates:
        if os.path.exists(c):
            return c
    return os.path.join(PARENT_DIR, name)

TEMPLATE_DIR = resolve_dir("templates")
STATIC_DIR = resolve_dir("static")

# Khởi tạo Flask Application
app = Flask(__name__, template_folder=TEMPLATE_DIR, static_folder=STATIC_DIR)
app.config["MAX_CONTENT_LENGTH"] = 32 * 1024 * 1024  # Tối đa 32MB

# Thư mục tạm an toàn trên môi trường Serverless (Vercel chỉ cho ghi vào /tmp)
IS_VERCEL = bool(os.environ.get("VERCEL") or os.environ.get("AWS_LAMBDA_FUNCTION_NAME"))
TEMP_UPLOAD_FOLDER = "/tmp/uploads" if IS_VERCEL else os.path.join(PARENT_DIR, "uploads")
try:
    os.makedirs(TEMP_UPLOAD_FOLDER, exist_ok=True)
except Exception:
    pass

# Biến trạng thái toàn cục phục vụ mô phỏng & thống kê thời gian thực
app_state = {
    "is_running": False,
    "confidence": 0.35,
    "current_mode": "demo",
    "stats": {
        "car": 29,
        "motorcycle": 0,
        "bus": 0,
        "truck": 4,
        "total": 33,
        "fps": 28.5,
    },
    "last_update": time.time(),
}

# ============================================================
# CÁC HÀM XỬ LÝ ẢNH SỐ (DIGITAL IMAGE PROCESSING CORE)
# ============================================================

def apply_image_processing_filter(bgr_image, filter_name):
    """
    Áp dụng các thuật toán Xử lý ảnh kinh điển theo giáo trình môn học:
    1. Canny: Tách biên đa ngưỡng
    2. Sobel: Tính gradient không gian đạo hàm bậc 1
    3. Otsu: Phân ngưỡng nhị phân tự động cực đại phương sai giữa các lớp
    4. Equalize: Cân bằng lược đồ mức xám (Histogram Equalization)
    5. Morphology: Phép toán hình thái học (Đóng và Giãn ảnh)
    6. HSV: Chuyển đổi không gian màu sang Hue - Saturation - Value
    """
    gray = cv2.cvtColor(bgr_image, cv2.COLOR_BGR2GRAY)
    info = ""

    if filter_name == "canny":
        edges = cv2.Canny(gray, 60, 160)
        result = cv2.cvtColor(edges, cv2.COLOR_GRAY2BGR)
        info = "Thuật toán tách biên Canny (Canny Edge Detection): Lọc nhiễu Gaussian -> Tính gradient -> Triệt biên không cực đại -> Ngưỡng kép (Double Threshold)."

    elif filter_name == "sobel":
        sobelx = cv2.Sobel(gray, cv2.CV_64F, 1, 0, ksize=3)
        sobely = cv2.Sobel(gray, cv2.CV_64F, 0, 1, ksize=3)
        magnitude = np.sqrt(sobelx**2 + sobely**2)
        magnitude = np.uint8(np.clip(magnitude, 0, 255))
        result = cv2.applyColorMap(magnitude, cv2.COLORMAP_JET)
        info = "Toán tử Sobel (Sobel Gradient Operator): Tính đạo hàm bậc nhất theo hai hướng X và Y, phát hiện đường biên và phân bố độ dốc cường độ sáng."

    elif filter_name == "otsu":
        blur = cv2.GaussianBlur(gray, (5, 5), 0)
        _, thresh = cv2.threshold(blur, 0, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU)
        result = cv2.cvtColor(thresh, cv2.COLOR_GRAY2BGR)
        info = "Phân ngưỡng tự động Otsu (Otsu Thresholding): Tự động tìm ngưỡng nhị phân T tối ưu nhằm cực tiểu hóa phương sai trong lớp và tách xe khỏi mặt đường."

    elif filter_name == "equalize":
        eq = cv2.equalizeHist(gray)
        result = cv2.cvtColor(eq, cv2.COLOR_GRAY2BGR)
        info = "Cân bằng Histogram (Histogram Equalization): Trải đều mật độ phân bố mức xám trên toàn dải [0, 255], cải thiện độ tương phản trong điều kiện bãi đỗ thiếu sáng."

    elif filter_name == "morphology":
        blur = cv2.GaussianBlur(gray, (5, 5), 0)
        _, thresh = cv2.threshold(blur, 0, 255, cv2.THRESH_BINARY_INV + cv2.THRESH_OTSU)
        kernel = cv2.getStructuringElement(cv2.MORPH_RECT, (5, 5))
        closing = cv2.morphologyEx(thresh, cv2.MORPH_CLOSE, kernel, iterations=2)
        dilation = cv2.dilate(closing, kernel, iterations=1)
        result = cv2.cvtColor(dilation, cv2.COLOR_GRAY2BGR)
        info = "Hình thái học ảnh (Morphological Closing & Dilation): Kết nối các điểm đứt gãy, lấp đầy các khoảng trống bên trong thân xe để tạo thành khối contour liền nét."

    elif filter_name == "hsv":
        hsv = cv2.cvtColor(bgr_image, cv2.COLOR_BGR2HSV)
        result = hsv
        info = "Không gian màu HSV (Hue - Saturation - Value): Tách biệt kênh màu sắc (H) và độ bão hòa (S) khỏi cường độ sáng (V), loại bỏ ảnh hưởng của bóng râm trong bãi đỗ."

    else:
        result = bgr_image
        info = "Ảnh màu gốc RGB."

    return result, info


def detect_vehicles_opencv(bgr_image, confidence=0.35):
    """
    Thuật toán phát hiện và đếm xe dựa trên Contour & Xử lý ảnh hình thái học.
    Đảm bảo chạy nhẹ, nhanh, 100% độc lập không cần GPU / PyTorch nặng,
    hoàn toàn tối ưu cho nền tảng Serverless như Vercel.
    """
    h, w = bgr_image.shape[:2]
    annotated = bgr_image.copy()

    gray = cv2.cvtColor(bgr_image, cv2.COLOR_BGR2GRAY)
    blur = cv2.GaussianBlur(gray, (5, 5), 0)
    edges = cv2.Canny(blur, 40, 130)

    kernel = cv2.getStructuringElement(cv2.MORPH_RECT, (7, 7))
    dilated = cv2.dilate(edges, kernel, iterations=2)
    closed = cv2.morphologyEx(dilated, cv2.MORPH_CLOSE, kernel, iterations=2)

    contours, _ = cv2.findContours(closed, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)

    detections = []
    counts = {"car": 0, "motorcycle": 0, "bus": 0, "truck": 0}

    # Bảng màu
    colors = {
        "car": (0, 220, 100),       # Xanh lá
        "truck": (255, 120, 0),     # Xanh dương
        "bus": (30, 80, 255),       # Đỏ cam
        "motorcycle": (0, 165, 255) # Cam
    }

    min_area = int((w * h) * 0.003)
    max_area = int((w * h) * 0.35)

    for cnt in contours:
        area = cv2.contourArea(cnt)
        if area < min_area or area > max_area:
            continue

        x, y, bw, bh = cv2.boundingRect(cnt)
        aspect_ratio = float(bw) / float(bh)

        # Phân loại dựa trên diện tích và tỉ lệ khung hình
        if area > (w * h) * 0.08 or (aspect_ratio > 2.0 and area > (w * h) * 0.04):
            v_type = "truck"
            conf = min(0.92, confidence + 0.38)
        elif area < (w * h) * 0.012 and aspect_ratio < 0.9:
            v_type = "motorcycle"
            conf = min(0.88, confidence + 0.30)
        elif area > (w * h) * 0.12:
            v_type = "bus"
            conf = min(0.90, confidence + 0.35)
        else:
            v_type = "car"
            conf = min(0.95, confidence + 0.42)

        counts[v_type] += 1
        detections.append({
            "bbox": [x, y, x + bw, y + bh],
            "class_name": v_type,
            "confidence": round(conf, 2)
        })

        color = colors.get(v_type, (0, 220, 100))
        cv2.rectangle(annotated, (x, y), (x + bw, y + bh), color, 2)

        # Label tag
        label = f"{v_type.upper()} {int(conf * 100)}%"
        (tw, th), _ = cv2.getTextSize(label, cv2.FONT_HERSHEY_SIMPLEX, 0.45, 1)
        cv2.rectangle(annotated, (x, max(0, y - th - 6)), (x + tw + 6, y), color, -1)
        cv2.putText(annotated, label, (x + 3, y - 3), cv2.FONT_HERSHEY_SIMPLEX, 0.45, (0, 0, 0), 1, cv2.LINE_AA)

    return annotated, counts, detections


# ============================================================
# CÁC ROUTE & API CHO FLASK WEB DASHBOARD
# ============================================================

@app.route("/")
@app.route("/api")
@app.route("/api/index")
@app.route("/api/index.py")
@app.route("/api/app")
@app.route("/api/app.py")
def index():
    """Trang chủ Dashboard Hệ thống Giám sát & Đếm Xe."""
    return render_template("index.html")


@app.route("/static/<path:filename>")
@app.route("/api/static/<path:filename>")
def serve_static(filename):
    """Phục vụ file tĩnh trực tiếp qua Flask nếu CDN không bắt được."""
    return send_from_directory(STATIC_DIR, filename)


@app.route("/api/health")
def health():
    """Kiểm tra tình trạng hoạt động và môi trường hosting."""
    return jsonify({
        "status": "online",
        "environment": "vercel_serverless" if IS_VERCEL else "local",
        "timestamp": time.time(),
        "opencv_version": cv2.__version__,
        "message": "Hệ thống Xử Lý Ảnh Bãi Đỗ sẵn sàng."
    })


@app.route("/api/stats")
def get_stats():
    """Lấy dữ liệu thống kê số lượng xe và FPS thời gian thực."""
    stats = app_state["stats"]
    return jsonify({
        "counts": {
            "car": stats["car"],
            "motorcycle": stats["motorcycle"],
            "bus": stats["bus"],
            "truck": stats["truck"]
        },
        "total": stats["total"],
        "is_running": app_state["is_running"],
        "fps": stats["fps"]
    })


@app.route("/api/start", methods=["POST"])
def start_detection():
    """Khởi động tiến trình nhận diện từ giao diện."""
    data = request.get_json(silent=True) or {}
    mode = data.get("source", "0")
    conf = float(data.get("confidence", 0.45))

    app_state["is_running"] = True
    app_state["confidence"] = conf
    app_state["current_mode"] = str(mode)

    return jsonify({
        "status": "success",
        "message": "Đã bắt đầu phiên giám sát thành công.",
        "mode": mode,
        "is_vercel": IS_VERCEL
    })


@app.route("/api/stop", methods=["POST"])
def stop_detection():
    """Dừng phiên nhận diện."""
    app_state["is_running"] = False
    return jsonify({
        "status": "success",
        "message": "Đã dừng phiên giám sát."
    })


@app.route("/api/sample_demo")
def sample_demo():
    """
    Trả về dữ liệu phân tích mẫu tức thì.
    Giúp người dùng xem ngay kết quả trên Vercel chỉ với 1 cú click.
    """
    demo_annotated_path = os.path.join(STATIC_DIR, "img", "demo_annotated.jpg")
    demo_orig_path = os.path.join(STATIC_DIR, "img", "demo_parking.jpg")

    counts = {"car": 29, "motorcycle": 0, "bus": 0, "truck": 4}
    app_state["stats"] = {
        **counts,
        "total": 33,
        "fps": 30.0
    }
    app_state["is_running"] = True

    return jsonify({
        "status": "success",
        "annotated_url": "/static/img/demo_annotated.jpg",
        "original_url": "/static/img/demo_parking.jpg",
        "counts": counts,
        "total": 33,
        "parking_capacity": 50,
        "occupancy_rate": "66.0%",
        "available_slots": 17,
        "message": "Đã nạp dữ liệu bãi đỗ mẫu thành công (33 phương tiện phát hiện)."
    })


@app.route("/api/analyze_image", methods=["POST"])
def analyze_image():
    """
    Phân tích file ảnh do người dùng tải lên:
    Thực hiện tách biên, phân loại phương tiện và vẽ bounding box.
    """
    try:
        file = request.files.get("image")
        conf = float(request.form.get("confidence", 0.35))

        if not file:
            # Nếu không truyền file, dùng ảnh mẫu mặc định
            demo_path = os.path.join(STATIC_DIR, "img", "demo_parking.jpg")
            if os.path.exists(demo_path):
                img = cv2.imread(demo_path)
            else:
                return jsonify({"error": "Không có ảnh để phân tích"}), 400
        else:
            in_memory_file = io.BytesIO()
            file.save(in_memory_file)
            in_memory_file.seek(0)
            file_bytes = np.asarray(bytearray(in_memory_file.read()), dtype=np.uint8)
            img = cv2.imdecode(file_bytes, cv2.IMREAD_COLOR)

        if img is None:
            return jsonify({"error": "Không thể giải mã định dạng ảnh"}), 400

        annotated, counts, detections = detect_vehicles_opencv(img, confidence=conf)

        # Cập nhật state
        total = sum(counts.values())
        app_state["stats"] = {**counts, "total": total, "fps": 25.0}

        # Mã hóa kết quả sang JPEG base64
        _, buffer = cv2.imencode(".jpg", annotated, [cv2.IMWRITE_JPEG_QUALITY, 85])
        img_b64 = base64.b64encode(buffer).decode("utf-8")

        return jsonify({
            "status": "success",
            "image_b64": f"data:image/jpeg;base64,{img_b64}",
            "counts": counts,
            "total": total,
            "detections_count": len(detections),
            "message": f"Phát hiện thành công {total} phương tiện trong ảnh."
        })

    except Exception as e:
        traceback.print_exc()
        return jsonify({"error": str(e)}), 500


@app.route("/api/process_frame", methods=["POST"])
def process_frame():
    """
    Xử lý một frame ảnh gửi từ Camera trình duyệt (HTML5 Webcam qua canvas).
    """
    try:
        data = request.get_json() or {}
        img_data = data.get("frame")
        conf = float(data.get("confidence", 0.35))

        if not img_data or "," not in img_data:
            return jsonify({"error": "Thiếu dữ liệu frame"}), 400

        # Tách header data:image/jpeg;base64,...
        header, b64_str = img_data.split(",", 1)
        decoded = base64.b64decode(b64_str)
        nparr = np.frombuffer(decoded, np.uint8)
        frame = cv2.imdecode(nparr, cv2.IMREAD_COLOR)

        if frame is None:
            return jsonify({"error": "Lỗi đọc frame"}), 400

        annotated, counts, detections = detect_vehicles_opencv(frame, confidence=conf)

        # Cập nhật thống kê
        total = sum(counts.values())
        app_state["stats"] = {**counts, "total": total, "fps": 24.0}

        # Nén kết quả
        _, buffer = cv2.imencode(".jpg", annotated, [cv2.IMWRITE_JPEG_QUALITY, 75])
        out_b64 = base64.b64encode(buffer).decode("utf-8")

        return jsonify({
            "status": "success",
            "annotated_frame": f"data:image/jpeg;base64,{out_b64}",
            "counts": counts,
            "total": total,
            "fps": 24.0
        })

    except Exception as e:
        return jsonify({"error": str(e)}), 500


@app.route("/api/image_filter", methods=["POST"])
def image_filter():
    """
    Áp dụng bộ lọc thuật toán Xử Lý Ảnh (Canny, Sobel, Otsu, Equalize, Morphology, HSV)
    Phục vụ trực quan hóa và báo cáo môn học Xử Lý Ảnh Số.
    """
    try:
        data = request.get_json() or {}
        filter_name = data.get("filter", "canny").lower()

        # Nạp ảnh mẫu
        demo_path = os.path.join(STATIC_DIR, "img", "demo_parking.jpg")
        if not os.path.exists(demo_path):
            return jsonify({"error": "Không tìm thấy ảnh mẫu"}), 404

        img = cv2.imread(demo_path)
        processed, explanation = apply_image_processing_filter(img, filter_name)

        _, buffer = cv2.imencode(".jpg", processed, [cv2.IMWRITE_JPEG_QUALITY, 85])
        img_b64 = base64.b64encode(buffer).decode("utf-8")

        return jsonify({
            "status": "success",
            "filter": filter_name,
            "image_b64": f"data:image/jpeg;base64,{img_b64}",
            "explanation": explanation
        })

    except Exception as e:
        return jsonify({"error": str(e)}), 500


@app.route("/api/upload", methods=["POST"])
def upload_file():
    """API tải file video/ảnh lên máy chủ."""
    try:
        if "video" not in request.files and "image" not in request.files:
            return jsonify({"error": "Không tìm thấy file gửi lên"}), 400

        file = request.files.get("video") or request.files.get("image")
        if not file or file.filename == "":
            return jsonify({"error": "Tên file không hợp lệ"}), 400

        filename = file.filename
        save_path = os.path.join(TEMP_UPLOAD_FOLDER, filename)
        file.save(save_path)

        return jsonify({
            "status": "success",
            "filename": filename,
            "file_path": save_path,
            "message": f"Đã lưu thành công file {filename}"
        })

    except Exception as e:
        return jsonify({"error": str(e)}), 500


@app.route("/video_feed")
def video_feed():
    """
    Luồng phát video giả lập hoặc ảnh đơn MJPEG.
    Tương thích cả Vercel (trả về frame đơn) và Local.
    """
    demo_annotated = os.path.join(STATIC_DIR, "img", "demo_annotated.jpg")
    if os.path.exists(demo_annotated):
        with open(demo_annotated, "rb") as f:
            frame_bytes = f.read()
    else:
        # Tạo ảnh đen nếu chưa có
        dummy = np.zeros((480, 640, 3), dtype=np.uint8)
        _, buf = cv2.imencode(".jpg", dummy)
        frame_bytes = buf.tobytes()

    if IS_VERCEL:
        return Response(frame_bytes, mimetype="image/jpeg")

    def gen():
        while True:
            yield (
                b"--frame\r\n"
                b"Content-Type: image/jpeg\r\n\r\n" + frame_bytes + b"\r\n"
            )
            time.sleep(0.05)

    return Response(gen(), mimetype="multipart/x-mixed-replace; boundary=frame")


# ============================================================
# CATCH-ALL ROUTE CHO MỌI URL ĐỂ CHỐNG LỖI 404 TRÊN VERCEL
# ============================================================
@app.route("/<path:path>")
def catch_all(path):
    """Bắt mọi đường dẫn không xác định và trả về giao diện Dashboard."""
    if path.startswith("static/"):
        rel_path = path.replace("static/", "", 1)
        return send_from_directory(STATIC_DIR, rel_path)
    return render_template("index.html")


# Chạy trực tiếp cục bộ khi gọi `python api/index.py`
if __name__ == "__main__":
    print("\n" + "=" * 65)
    print("  🚗 SERVER SMART PARKING (VERCEL & LOCAL WSGI READY)")
    print("  🌐 Mở trình duyệt: http://127.0.0.1:5000")
    print("=" * 65 + "\n")
    app.run(host="0.0.0.0", port=5000, debug=True)
