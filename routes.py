# ============================================================
# FILE: routes.py
# THÀNH VIÊN PHỤ TRÁCH: Thành viên 4 (Chuyên Backend API & Đa Luồng)
# MÔ TẢ: Định nghĩa các tuyến API, Video Stream MJPEG, Upload File
# ============================================================

import os
import sys
import re
import time
import traceback
import threading
from urllib.parse import urlparse
import cv2
from flask import render_template, Response, jsonify, request
from werkzeug.utils import secure_filename

# Đảm bảo console trên Windows không bị lỗi UnicodeEncodeError khi in tiếng Việt
if sys.platform.startswith("win"):
    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
        sys.stderr.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass


# ===== Biến toàn cục chia sẻ giữa các luồng =====
latest_counts = {
    "car": 0, "motorcycle": 0, "bus": 0, "truck": 0,
}
latest_frame_bytes = None           # Dữ liệu ảnh JPEG mới nhất
_frame_id = 0                       # Số thứ tự frame để tránh gửi lặp
_current_session_id = 0             # Định danh phiên phân tích hiện tại
_is_session_active = False          # Trạng thái đang chạy hay dừng
_active_thread = None               # Đối tượng Thread đang chạy
_active_stop_event = None           # Cờ báo dừng luồng

# Các ổ khóa đồng bộ hoá
_state_lock = threading.Lock()      # Khóa trạng thái hệ thống
_api_lock = threading.Lock()        # Khóa gọi API Start/Stop
_inference_lock = threading.Lock()  # Khóa bảo vệ model YOLO inference

# Danh sách các định dạng video cho phép
ALLOWED_VIDEO_EXT = {".mp4", ".avi", ".mkv", ".mov", ".webm", ".wmv", ".flv"}
ALLOWED_PROTOCOLS = ("rtsp://", "http://", "https://")

NONE_LIMIT_FILE = 30                # Giới hạn frame rỗng cho file cục bộ (~1s)
NONE_LIMIT_STREAM = 300             # Giới hạn frame rỗng cho luồng mạng (~10s)

_EMPTY_COUNTS = {"car": 0, "motorcycle": 0, "bus": 0, "truck": 0}


def _validate_source(source):
    """Kiểm tra tính an toàn và hợp lệ của nguồn video."""
    if isinstance(source, bool):
        return False

    if isinstance(source, int):
        return 0 <= source <= 9

    if isinstance(source, str):
        source = source.strip()
        # Nếu là chỉ số webcam
        if re.fullmatch(r"[0-9]", source):
            return True

        lower = source.lower()
        # Nếu là URL stream
        if any(lower.startswith(p) for p in ALLOWED_PROTOCOLS):
            parsed = urlparse(source)
            host = (parsed.hostname or "").lower()
            if host in ("127.0.0.1", "localhost", "0.0.0.0", "169.254.169.254"):
                return False
            return True

        # Nếu là đường dẫn file
        if ".." in source:
            return False

        _, ext = os.path.splitext(lower)
        if ext in ALLOWED_VIDEO_EXT:
            return True

    return False


def _is_stream_source(source):
    """Phân biệt giữa luồng trực tiếp (webcam, rtsp) và file video."""
    if isinstance(source, int):
        return True
    if isinstance(source, str):
        if re.fullmatch(r"[0-9]", source.strip()):
            return True
        if any(source.lower().startswith(p) for p in ALLOWED_PROTOCOLS):
            return True
    return False


def create_routes(app, detector, video_proc, upload_folder="uploads"):
    """Tạo và đăng ký tất cả các route của ứng dụng Flask."""
    os.makedirs(upload_folder, exist_ok=True)

    global latest_counts, latest_frame_bytes, _frame_id
    global _current_session_id, _is_session_active, _active_thread, _active_stop_event

    def detection_loop(session_id, stop_event, source, none_limit):
        """
        Vòng lặp đọc ảnh, phát hiện xe và cập nhật giao diện.
        Mỗi phiên có một VideoCapture riêng biệt để giải phóng an toàn.
        """
        global latest_counts, latest_frame_bytes, _frame_id, _is_session_active

        print(f"[HỆ THỐNG] Khởi tạo luồng xử lý phiên {session_id} với nguồn: {source}")
        cap = cv2.VideoCapture(source)

        if not cap.isOpened():
            print(f"[LỖI] Không thể kết nối tới nguồn video: {source}")
            with _state_lock:
                if _current_session_id == session_id:
                    _is_session_active = False
            return

        none_count = 0

        try:
            while not stop_event.is_set():
                ret, frame = cap.read()

                if not ret or frame is None:
                    none_count += 1
                    if none_count >= none_limit:
                        print(f"[THÔNG BÁO] Video phiên {session_id} đã kết thúc hoặc mất kết nối.")
                        break
                    time.sleep(0.03)
                    continue

                none_count = 0

                # Chạy phát hiện xe với khóa bảo vệ
                with _inference_lock:
                    detections = detector.detect(frame)
                    counts = detector.count_vehicles(detections)

                # Vẽ bounding box và HUD tiếng Việt
                processed_frame = video_proc.draw_detections(frame, detections, counts)
                frame_bytes = video_proc.encode_frame(processed_frame)

                # Cập nhật dữ liệu cho client
                if frame_bytes is not None:
                    with _state_lock:
                        if _current_session_id == session_id and not stop_event.is_set():
                            latest_counts = counts
                            latest_frame_bytes = frame_bytes
                            _frame_id += 1

        except Exception as e:
            print(f"[LỖI] Luồng phiên {session_id} gặp sự cố: {e}")
            traceback.print_exc()

        finally:
            try:
                cap.release()
            except Exception:
                pass

            with _state_lock:
                if _current_session_id == session_id:
                    _is_session_active = False
                    latest_frame_bytes = None
                    latest_counts = _EMPTY_COUNTS.copy()
            print(f"[HỆ THỐNG] Phiên {session_id} đã kết thúc và giải phóng tài nguyên.")

    # ----------------------------------------------------
    # ROUTE 1: Trang chủ Dashboard
    # ----------------------------------------------------
    @app.route("/")
    def index():
        return render_template("index.html")

    # ----------------------------------------------------
    # ROUTE 2: Luồng phát Video trực tiếp MJPEG
    # ----------------------------------------------------
    @app.route("/video_feed")
    def video_feed():
        def generate():
            with _state_lock:
                my_session = _current_session_id
            last_sent_id = -1
            no_frame_waited = 0

            while True:
                with _state_lock:
                    if _current_session_id != my_session or not _is_session_active:
                        break
                    frame = latest_frame_bytes
                    current_id = _frame_id

                if frame is None:
                    time.sleep(0.05)
                    no_frame_waited += 1
                    # Sau ~10 giây không có frame thì kết thúc worker
                    if no_frame_waited > 200:
                        break
                    continue

                no_frame_waited = 0

                if current_id == last_sent_id:
                    time.sleep(0.03)
                    continue

                last_sent_id = current_id
                try:
                    yield (
                        b"--frame\r\n"
                        b"Content-Type: image/jpeg\r\n\r\n"
                        + frame
                        + b"\r\n"
                    )
                except (GeneratorExit, Exception):
                    break

        return Response(
            generate(),
            mimetype="multipart/x-mixed-replace; boundary=frame",
        )

    # ----------------------------------------------------
    # ROUTE 3: API Lấy thống kê số lượng xe thời gian thực
    # ----------------------------------------------------
    @app.route("/api/stats")
    def get_stats():
        with _state_lock:
            counts = latest_counts.copy()
            active = _is_session_active and (_active_thread is not None and _active_thread.is_alive())

        return jsonify({
            "counts": counts,
            "total": sum(counts.values()),
            "is_running": active,
            "fps": video_proc.fps,
        })

    # ----------------------------------------------------
    # ROUTE 4: API Bắt đầu nhận diện
    # ----------------------------------------------------
    @app.route("/api/start", methods=["POST"])
    def start_detection():
        global _current_session_id, _is_session_active, _active_thread, _active_stop_event
        global latest_counts, latest_frame_bytes, _frame_id

        data = request.get_json(silent=True)
        if not isinstance(data, dict):
            return jsonify({"error": "Dữ liệu JSON không hợp lệ."}), 400

        source = data.get("source", 0)
        confidence = data.get("confidence", None)

        if confidence is not None:
            detector.set_confidence(confidence)

        # Xử lý chuỗi số webcam (ví dụ "0" -> 0)
        if isinstance(source, str) and re.fullmatch(r"[0-9]", source.strip()):
            source = int(source.strip())

        if not _validate_source(source):
            return jsonify({
                "error": "Nguồn video không hợp lệ. Vui lòng chọn Webcam (0), tải video lên hoặc nhập link hợp lệ."
            }), 400

        with _api_lock:
            with _state_lock:
                old_stop_event = _active_stop_event
                old_thread = _active_thread
                _current_session_id += 1
                my_session = _current_session_id
                _is_session_active = True
                latest_counts = _EMPTY_COUNTS.copy()
                latest_frame_bytes = None
                _frame_id += 1

            # Dừng phiên cũ nếu có
            if old_stop_event is not None:
                old_stop_event.set()
            if old_thread is not None and old_thread.is_alive():
                old_thread.join(timeout=2.0)

            video_proc.reset_timing()
            none_limit = NONE_LIMIT_STREAM if _is_stream_source(source) else NONE_LIMIT_FILE
            my_stop = threading.Event()

            t = threading.Thread(
                target=detection_loop,
                args=(my_session, my_stop, source, none_limit),
                daemon=True,
            )

            with _state_lock:
                _active_stop_event = my_stop
                _active_thread = t

            t.start()

        return jsonify({
            "message": "Đã bắt đầu nhận diện",
            "source": str(source),
            "session_id": my_session
        })

    # ----------------------------------------------------
    # ROUTE 5: API Dừng nhận diện
    # ----------------------------------------------------
    @app.route("/api/stop", methods=["POST"])
    def stop_detection():
        global _is_session_active, latest_counts, latest_frame_bytes

        with _api_lock:
            with _state_lock:
                _is_session_active = False
                old_stop_event = _active_stop_event
                old_thread = _active_thread
                latest_counts = _EMPTY_COUNTS.copy()
                latest_frame_bytes = None

            if old_stop_event is not None:
                old_stop_event.set()
            if old_thread is not None and old_thread.is_alive():
                old_thread.join(timeout=2.0)

        return jsonify({"message": "Đã dừng nhận diện"})

    # ----------------------------------------------------
    # ROUTE 6: API Upload file video kiểm thử từ máy tính
    # ----------------------------------------------------
    @app.route("/api/upload", methods=["POST"])
    def upload_video():
        if "video" not in request.files:
            return jsonify({"error": "Không tìm thấy file tải lên."}), 400

        file = request.files["video"]
        if file.filename == "":
            return jsonify({"error": "Chưa chọn file video nào."}), 400

        filename = secure_filename(file.filename)
        _, ext = os.path.splitext(filename.lower())

        if ext not in ALLOWED_VIDEO_EXT:
            return jsonify({"error": f"Định dạng {ext} không được hỗ trợ. Vui lòng tải file video (mp4, avi, mov...)."}), 400

        save_path = os.path.join(upload_folder, filename)
        file.save(save_path)

        return jsonify({
            "message": "Tải video lên thành công!",
            "file_path": save_path,
            "filename": filename
        })
