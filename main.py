# ==============================================================================
# ĐỒ ÁN MÔN HỌC: XỬ LÝ ẢNH SỐ (DIGITAL IMAGE PROCESSING)
# ĐỀ TÀI: HỆ THỐNG NHẬN DIỆN VÀ ĐẾM SỐ LƯỢNG XE TRONG BÃI ĐỖ XE BẰNG YOLOV8 & OPENCV
# TẬP TIN DUY NHẤT (ALL-IN-ONE SINGLE FILE): main.py
# ==============================================================================
# Hướng dẫn chạy:
#   python main.py
# ==============================================================================

import os
import sys
import time
import json
import threading
from datetime import datetime

# Đảm bảo Windows console in tiếng Việt không bị lỗi font (UnicodeEncodeError)
if sys.platform.startswith("win"):
    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
        sys.stderr.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass

import cv2
import numpy as np
from PIL import Image, ImageDraw, ImageFont
from ultralytics import YOLO

# Thư viện Flask (dùng cho chế độ Web)
try:
    from flask import Flask, Response, render_template_string, jsonify, request
    FLASK_AVAILABLE = True
except ImportError:
    FLASK_AVAILABLE = False


# ==============================================================================
# 1. CẤU HÌNH HỆ THỐNG, DANH MỤC LỚP & BẢNG MÀU
# ==============================================================================
# 4 lớp phương tiện giao thông theo tập dữ liệu quốc tế COCO
VEHICLE_CLASSES = {
    2: ("car", "Ô tô"),
    3: ("motorcycle", "Xe máy"),
    5: ("bus", "Xe buýt"),
    7: ("truck", "Xe tải"),
}

# Hệ màu BGR (OpenCV)
COLORS_BGR = {
    "car":        (0, 220, 100),    # Xanh lá cây
    "motorcycle": (0, 165, 255),    # Màu cam
    "bus":        (30, 80, 255),    # Đỏ cam
    "truck":      (255, 120, 0),    # Xanh dương
}

# Hệ màu RGB (Pillow)
COLORS_RGB = {
    "car":        (100, 220, 0),
    "motorcycle": (255, 165, 0),
    "bus":        (255, 80, 30),
    "truck":      (0, 120, 255),
}


def get_system_font(size):
    """Tải font Unicode tiếng Việt từ Windows / Linux để vẽ chữ không bị vỡ font."""
    font_paths = [
        "C:/Windows/Fonts/segoeui.ttf",
        "C:/Windows/Fonts/arial.ttf",
        "C:/Windows/Fonts/tahoma.ttf",
        "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf",
        "/System/Library/Fonts/Helvetica.ttc",
    ]
    for p in font_paths:
        if os.path.exists(p):
            try:
                return ImageFont.truetype(p, size)
            except Exception:
                continue
    try:
        return ImageFont.load_default(size=size)
    except Exception:
        return ImageFont.load_default()


# ==============================================================================
# 2. MODULE AI NHẬN DIỆN & PHÂN LOẠI PHƯƠNG TIỆN (YOLOv8)
# ==============================================================================
class VehicleDetector:
    """Lớp quản lý mô hình YOLOv8, phát hiện và đếm số lượng xe."""

    def __init__(self, model_path="yolov8n.pt", confidence=0.45):
        self.model_path = model_path
        self.confidence = float(confidence)

        print(f"[AI] Đang nạp mô hình YOLOv8: '{self.model_path}' ...")
        self.model = YOLO(self.model_path)
        print("[AI] Khởi tạo mô hình thành công!")

    def set_confidence(self, conf):
        try:
            val = float(conf)
            if 0.1 <= val <= 0.95:
                self.confidence = val
        except (ValueError, TypeError):
            pass

    def detect(self, frame):
        """
        Nhận diện phương tiện trong khung hình ảnh.
        Trả về danh sách các bounding boxes và thông tin xe.
        """
        if frame is None:
            return []

        # Chạy inference với YOLOv8
        results = self.model(frame, conf=self.confidence, verbose=False)
        detections = []

        for result in results:
            boxes = result.boxes
            if boxes is None:
                continue
            for box in boxes:
                class_id = int(box.cls[0].item())
                if class_id in VEHICLE_CLASSES:
                    label_en, label_vn = VEHICLE_CLASSES[class_id]
                    coords = [int(v) for v in box.xyxy[0].tolist()]
                    conf = round(float(box.conf[0].item()), 2)

                    detections.append({
                        "box": coords,
                        "label_en": label_en,
                        "label_vn": label_vn,
                        "class_id": class_id,
                        "confidence": conf
                    })

        return detections

    def count_vehicles(self, detections):
        """Đếm số lượng từng loại xe hiện diện tức thời trong khung hình."""
        counts = {"car": 0, "motorcycle": 0, "bus": 0, "truck": 0}
        for d in detections:
            name = d.get("label_en")
            if name in counts:
                counts[name] += 1
        return counts


# ==============================================================================
# 3. MODULE XỬ LÝ ẢNH & ĐỒ HỌA OVERLAY (OpenCV + Pillow)
# ==============================================================================
class ImageProcessor:
    """Lớp xử lý ma trận ảnh BGR, đo FPS, vẽ bounding box và bảng HUD tiếng Việt."""

    def __init__(self):
        self.fps = 0.0
        self.prev_time = 0.0

        # Khởi tạo sẵn font chữ
        self.font_title = get_system_font(18)
        self.font_item = get_system_font(15)
        self.font_tag = get_system_font(13)

    def update_fps(self):
        """Tính toán FPS thời gian thực dựa trên độ lệch thời gian giữa 2 frame."""
        cur = time.time()
        if self.prev_time > 0:
            delta = cur - self.prev_time
            if delta > 0:
                self.fps = round(1.0 / delta, 1)
        self.prev_time = cur
        return self.fps

    def draw_hud_and_boxes(self, frame, detections, counts, confidence_val):
        """
        Vẽ Bounding Box màu theo loại xe và Bảng thông số HUD tiếng Việt bán trong suốt.
        """
        h, w = frame.shape[:2]
        annotated = frame.copy()

        # 1. Vẽ hộp bao và góc viền công nghệ bằng OpenCV
        for d in detections:
            x1, y1, x2, y2 = d["box"]
            color = COLORS_BGR.get(d["label_en"], (0, 255, 0))

            # Khung chữ nhật
            cv2.rectangle(annotated, (x1, y1), (x2, y2), color, 2)

            # 4 góc nhấn nổi bật
            line_len = min(18, (x2 - x1) // 4, (y2 - y1) // 4)
            cv2.line(annotated, (x1, y1), (x1 + line_len, y1), color, 4)
            cv2.line(annotated, (x1, y1), (x1, y1 + line_len), color, 4)
            cv2.line(annotated, (x2, y1), (x2 - line_len, y1), color, 4)
            cv2.line(annotated, (x2, y1), (x2, y1 + line_len), color, 4)
            cv2.line(annotated, (x1, y2), (x1 + line_len, y2), color, 4)
            cv2.line(annotated, (x1, y2), (x1, y2 - line_len), color, 4)
            cv2.line(annotated, (x2, y2), (x2 - line_len, y2), color, 4)
            cv2.line(annotated, (x2, y2), (x2, y2 - line_len), color, 4)

        # 2. Chuyển sang Pillow để vẽ chữ tiếng Việt có dấu
        img_rgb = Image.fromarray(cv2.cvtColor(annotated, cv2.COLOR_BGR2RGB))
        draw = ImageDraw.Draw(img_rgb)

        # Vẽ nhãn tên xe phía trên từng hộp bao
        for d in detections:
            x1, y1, x2, y2 = d["box"]
            color_rgb = COLORS_RGB.get(d["label_en"], (0, 255, 0))
            tag_text = f"{d['label_vn']} {int(d['confidence'] * 100)}%"

            bbox_t = draw.textbbox((0, 0), tag_text, font=self.font_tag)
            tw = bbox_t[2] - bbox_t[0]
            th = bbox_t[3] - bbox_t[1]

            tag_y1 = max(0, y1 - th - 6)
            tag_y2 = tag_y1 + th + 6
            tag_x2 = min(w, x1 + tw + 10)

            draw.rectangle([x1, tag_y1, tag_x2, tag_y2], fill=color_rgb)
            draw.text((x1 + 5, tag_y1 + 3), tag_text, font=self.font_tag, fill=(255, 255, 255))

        # 3. Vẽ bảng thông số HUD bán trong suốt góc trên bên trái
        hud_w, hud_h = 265, 195
        hud_x1, hud_y1 = 15, 15
        hud_x2, hud_y2 = hud_x1 + hud_w, hud_y1 + hud_h

        overlay = Image.new("RGBA", img_rgb.size, (0, 0, 0, 0))
        draw_ov = ImageDraw.Draw(overlay)
        draw_ov.rounded_rectangle([hud_x1, hud_y1, hud_x2, hud_y2], radius=10, fill=(15, 23, 42, 215), outline=(56, 189, 248, 255), width=2)
        img_rgb = Image.alpha_composite(img_rgb.convert("RGBA"), overlay).convert("RGB")
        draw = ImageDraw.Draw(img_rgb)

        # Tiêu đề bảng HUD
        draw.text((hud_x1 + 14, hud_y1 + 10), "📊 BÃI ĐỖ XE THỜI GIAN THỰC", font=self.font_title, fill=(56, 189, 248))
        draw.line([hud_x1 + 14, hud_y1 + 36, hud_x2 - 14, hud_y1 + 36], fill=(51, 65, 85), width=1)

        total_vehicles = sum(counts.values())
        draw.text((hud_x1 + 14, hud_y1 + 45), f"• Tổng số xe: {total_vehicles} chiếc", font=self.font_item, fill=(255, 255, 255))
        draw.text((hud_x1 + 14, hud_y1 + 70), f"  - Ô tô:     {counts['car']}", font=self.font_item, fill=(100, 220, 0))
        draw.text((hud_x1 + 14, hud_y1 + 95), f"  - Xe máy:   {counts['motorcycle']}", font=self.font_item, fill=(255, 165, 0))
        draw.text((hud_x1 + 14, hud_y1 + 120), f"  - Xe buýt:  {counts['bus']}", font=self.font_item, fill=(255, 80, 30))
        draw.text((hud_x1 + 14, hud_y1 + 145), f"  - Xe tải:   {counts['truck']}", font=self.font_item, fill=(0, 120, 255))

        info_txt = f"FPS: {self.fps} | Độ tin cậy: {int(confidence_val * 100)}%"
        draw.text((hud_x1 + 14, hud_y1 + 172), info_txt, font=self.font_tag, fill=(148, 163, 184))

        # Chuyển ngược lại sang BGR cho OpenCV
        return cv2.cvtColor(np.array(img_rgb), cv2.COLOR_RGB2BGR)


# ==============================================================================
# 4. CHẾ ĐỘ 1: CỬA SỔ OPENCV TRỰC TIẾP (DESKTOP GUI)
# ==============================================================================
def run_opencv_mode(video_source=0, source_name="Video"):
    """Chạy chương trình nhận diện trên cửa sổ đồ họa OpenCV có phím tắt điều khiển."""
    print(f"\n[OPENCV] Đang mở nguồn video: {source_name} ...")
    cap = cv2.VideoCapture(video_source)

    if not cap.isOpened():
        print(f"❌ LỖI: Không thể mở video từ '{video_source}'.")
        return

    detector = VehicleDetector(model_path="yolov8n.pt", confidence=0.45)
    processor = ImageProcessor()

    width = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH)) or 1280
    height = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT)) or 720
    fps_src = cap.get(cv2.CAP_PROP_FPS) or 25.0
    if fps_src <= 0 or fps_src > 120:
        fps_src = 25.0

    # Chuẩn bị file ghi video kết quả
    output_video_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "ketqua_nhandien.mp4")
    fourcc = cv2.VideoWriter_fourcc(*"mp4v")
    out_writer = cv2.VideoWriter(output_video_path, fourcc, fps_src, (width, height))

    window_name = "DO AN XU LY ANH - NHAN DIEN XE BAI DO (YOLOv8)"
    cv2.namedWindow(window_name, cv2.WINDOW_NORMAL)
    cv2.resizeWindow(window_name, min(1280, width), min(720, height))

    print("\n" + "=" * 70)
    print("  🚀 ĐANG CHẠY CHƯƠNG TRÌNH XỬ LÝ ẢNH TRÊN CỬA SỔ OPENCV")
    print("=" * 70)
    print("  [HƯỚNG DẪN BÀN PHÍM]:")
    print("    - Nhấn 'Q' : Dừng chương trình và xuất báo cáo")
    print("    - Nhấn 'P' : Tạm dừng / Tiếp tục chạy")
    print("    - Nhấn 'S' : Chụp ảnh màn hình lưu lại báo cáo")
    print("    - Nhấn '+' : Tăng ngưỡng tin cậy (+5%)")
    print("    - Nhấn '-' : Giảm ngưỡng tin cậy (-5%)")
    print("=" * 70 + "\n")

    paused = False
    total_frames = 0
    max_count = 0
    stat_history = {"car": 0, "motorcycle": 0, "bus": 0, "truck": 0}
    snapshots = 0

    try:
        while True:
            if not paused:
                ret, frame = cap.read()
                if not ret:
                    print("\n[INFO] Đã đọc hết video.")
                    break

                processor.update_fps()
                detections = detector.detect(frame)
                counts = detector.count_vehicles(detections)

                # Vẽ HUD và Bounding Box
                final_frame = processor.draw_hud_and_boxes(frame, detections, counts, detector.confidence)

                # Lưu vào video
                if out_writer is not None:
                    out_writer.write(final_frame)

                # Thống kê
                total_frames += 1
                curr_tot = sum(counts.values())
                if curr_tot > max_count:
                    max_count = curr_tot
                for k in counts:
                    if counts[k] > stat_history[k]:
                        stat_history[k] = counts[k]

                cv2.imshow(window_name, final_frame)

            key = cv2.waitKey(1) & 0xFF
            if key == ord('q') or key == 27:
                break
            elif key == ord('p') or key == ord(' '):
                paused = not paused
                print(f"[STATUS] {'TẠM DỪNG' if paused else 'TIẾP TỤC'}")
            elif key == ord('s'):
                snapshots += 1
                fname = f"anh_chup_bao_cao_{datetime.now().strftime('%Y%m%d_%H%M%S')}.jpg"
                cv2.imwrite(fname, final_frame)
                print(f"📸 Đã chụp ảnh: {fname}")
            elif key == ord('+') or key == ord('='):
                detector.set_confidence(min(0.95, detector.confidence + 0.05))
                print(f"🎯 Ngưỡng tin cậy: {int(detector.confidence * 100)}%")
            elif key == ord('-') or key == ord('_'):
                detector.set_confidence(max(0.10, detector.confidence - 0.05))
                print(f"🎯 Ngưỡng tin cậy: {int(detector.confidence * 100)}%")

    finally:
        cap.release()
        if out_writer is not None:
            out_writer.release()
        cv2.destroyAllWindows()

        # Xuất file báo cáo tổng kết
        report_txt = (
            "======================================================================\n"
            "        BÁO CÁO KẾT QUẢ THỰC NGHIỆM ĐỒ ÁN XỬ LÝ ẢNH SỐ\n"
            "======================================================================\n\n"
            f"1. Tên đề tài: Hệ Thống Nhận Diện & Đếm Số Lượng Xe Trong Bãi Đỗ Xe\n"
            f"2. Nguồn dữ liệu: {source_name}\n"
            f"3. Thời gian chạy: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n"
            f"4. Tổng số khung hình đã phân tích: {total_frames:,} frames\n"
            f"5. Số lượng xe lớn nhất cùng lúc: {max_count} chiếc\n"
            f"6. Đỉnh điểm từng loại xe:\n"
            f"   - Ô tô:     {stat_history['car']} chiếc\n"
            f"   - Xe máy:   {stat_history['motorcycle']} chiếc\n"
            f"   - Xe buýt:  {stat_history['bus']} chiếc\n"
            f"   - Xe tải:   {stat_history['truck']} chiếc\n"
            f"7. Video kết quả đã lưu: {os.path.abspath(output_video_path)}\n"
            "======================================================================\n"
        )
        with open("thong_ke_ket_qua.txt", "w", encoding="utf-8") as f:
            f.write(report_txt)

        print("\n" + report_txt)
        print("✅ Hoàn thành xuất sắc bài báo cáo xử lý ảnh!")


# ==============================================================================
# 5. CHẾ ĐỘ 2: WEB DASHBOARD THỜI GIAN THỰC (FLASK TỰ CHỨA HTML/CSS/JS)
# ==============================================================================
EMBEDDED_HTML_TEMPLATE = """<!DOCTYPE html>
<html lang="vi">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Hệ Thống Nhận Diện Bãi Đỗ Xe - Xử Lý Ảnh Số</title>
    <style>
        :root {
            --bg-main: #0b0f19; --bg-card: #111827; --border-color: #1f2937;
            --primary: #38bdf8; --accent-car: #22c55e; --accent-moto: #f97316;
            --accent-bus: #ef4444; --accent-truck: #3b82f6; --text-main: #f3f4f6;
        }
        * { box-sizing: border-box; margin: 0; padding: 0; }
        body { font-family: 'Segoe UI', Tahoma, sans-serif; background-color: var(--bg-main); color: var(--text-main); min-height: 100vh; padding: 20px; }
        .header { text-align: center; margin-bottom: 25px; border-bottom: 1px solid var(--border-color); padding-bottom: 15px; }
        .header h1 { font-size: 24px; color: var(--primary); text-transform: uppercase; letter-spacing: 1px; }
        .header p { color: #94a3b8; font-size: 14px; margin-top: 5px; }
        .container { max-width: 1400px; margin: 0 auto; display: grid; grid-template-columns: 2fr 1fr; gap: 20px; }
        @media (max-width: 1024px) { .container { grid-template-columns: 1fr; } }
        .card { background: var(--bg-card); border: 1px solid var(--border-color); border-radius: 12px; padding: 20px; box-shadow: 0 4px 6px -1px rgba(0, 0, 0, 0.3); }
        .video-container { position: relative; width: 100%; aspect-ratio: 16/9; background: #000; border-radius: 8px; overflow: hidden; display: flex; align-items: center; justify-content: center; border: 2px solid #1e293b; }
        .video-container img { width: 100%; height: 100%; object-fit: contain; }
        .video-placeholder { color: #64748b; text-align: center; }
        .stats-grid { display: grid; grid-template-columns: 1fr 1fr; gap: 15px; margin-top: 20px; }
        .stat-box { background: #1e293b; border-radius: 8px; padding: 15px; text-align: center; border-left: 4px solid var(--primary); }
        .stat-box.car { border-color: var(--accent-car); }
        .stat-box.moto { border-color: var(--accent-moto); }
        .stat-box.bus { border-color: var(--accent-bus); }
        .stat-box.truck { border-color: var(--accent-truck); }
        .stat-title { font-size: 13px; color: #94a3b8; text-transform: uppercase; }
        .stat-value { font-size: 32px; font-weight: bold; margin-top: 5px; }
        .stat-total { grid-column: span 2; background: linear-gradient(135deg, #1e293b, #0f172a); border-left: 4px solid var(--primary); }
        .control-group { margin-top: 20px; }
        .control-group label { display: block; font-size: 14px; color: #94a3b8; margin-bottom: 8px; }
        .btn-row { display: flex; gap: 10px; margin-top: 20px; }
        .btn { flex: 1; padding: 12px; border: none; border-radius: 6px; font-weight: bold; cursor: pointer; text-transform: uppercase; font-size: 14px; transition: all 0.2s; }
        .btn-start { background: #10b981; color: white; }
        .btn-start:hover { background: #059669; }
        .btn-stop { background: #ef4444; color: white; }
        .btn-stop:hover { background: #dc2626; }
        input[type="range"] { width: 100%; accent-color: var(--primary); }
        .badge { display: inline-block; padding: 4px 8px; border-radius: 4px; font-size: 12px; background: #334155; }
    </style>
</head>
<body>
    <div class="header">
        <h1>🚗 Hệ Thống Nhận Diện & Đếm Xe Bãi Đỗ (Xử Lý Ảnh Số)</h1>
        <p>Mô hình: <strong>YOLOv8 Nano</strong> | Xử lý ảnh: <strong>OpenCV & Pillow</strong> | Nền tảng: <strong>Flask Localhost</strong></p>
    </div>
    <div class="container">
        <div class="card">
            <h2 style="font-size: 18px; margin-bottom: 15px; color: var(--primary);">🎥 Luồng Video Xử Lý Ảnh Trực Tiếp</h2>
            <div class="video-container">
                <img id="videoFeed" src="" style="display: none;" alt="Video Feed">
                <div id="placeholder" class="video-placeholder">
                    <p style="font-size: 40px; margin-bottom: 10px;">📹</p>
                    <p>Nhấn <strong>▶ BẮT ĐẦU</strong> bên phải để phát hiện và đếm xe</p>
                </div>
            </div>
            <div style="display: flex; justify-content: space-between; margin-top: 15px; font-size: 13px; color: #94a3b8;">
                <span>Trạng thái: <strong id="statusText" style="color: #ef4444;">ĐÃ DỪNG</strong></span>
                <span>Tốc độ: <strong id="fpsText" style="color: var(--primary);">0.0 FPS</strong></span>
            </div>
        </div>
        <div class="card">
            <h2 style="font-size: 18px; margin-bottom: 15px; color: var(--primary);">📊 Bảng Thống Kê Phương Tiện</h2>
            <div class="stats-grid">
                <div class="stat-box stat-total">
                    <div class="stat-title">Tổng số xe trong bãi</div>
                    <div class="stat-value" id="valTotal" style="color: var(--primary);">0</div>
                </div>
                <div class="stat-box car">
                    <div class="stat-title">Ô tô</div>
                    <div class="stat-value" id="valCar" style="color: var(--accent-car);">0</div>
                </div>
                <div class="stat-box moto">
                    <div class="stat-title">Xe máy</div>
                    <div class="stat-value" id="valMoto" style="color: var(--accent-moto);">0</div>
                </div>
                <div class="stat-box bus">
                    <div class="stat-title">Xe buýt</div>
                    <div class="stat-value" id="valBus" style="color: var(--accent-bus);">0</div>
                </div>
                <div class="stat-box truck">
                    <div class="stat-title">Xe tải</div>
                    <div class="stat-value" id="valTruck" style="color: var(--accent-truck);">0</div>
                </div>
            </div>
            <div class="control-group">
                <label>Ngưỡng tin cậy (Confidence): <strong id="confVal" style="color: var(--primary);">45%</strong></label>
                <input type="range" id="confSlider" min="10" max="90" value="45">
            </div>
            <div class="btn-row">
                <button class="btn btn-start" id="btnStart" onclick="startDetection()">▶ Bắt Đầu</button>
                <button class="btn btn-stop" id="btnStop" onclick="stopDetection()">⏹ Dừng</button>
            </div>
        </div>
    </div>
    <script>
        let isRunning = false;
        let pollTimer = null;

        function startDetection() {
            fetch('/api/start', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ conf: document.getElementById('confSlider').value / 100 })
            }).then(r => r.json()).then(data => {
                isRunning = true;
                document.getElementById('videoFeed').src = '/video_feed?' + new Date().getTime();
                document.getElementById('videoFeed').style.display = 'block';
                document.getElementById('placeholder').style.display = 'none';
                document.getElementById('statusText').innerText = 'ĐANG CHẠY';
                document.getElementById('statusText').style.color = '#10b981';
                if (!pollTimer) pollTimer = setInterval(updateStats, 1000);
            });
        }

        function stopDetection() {
            fetch('/api/stop', { method: 'POST' }).then(() => {
                isRunning = false;
                document.getElementById('videoFeed').style.display = 'none';
                document.getElementById('placeholder').style.display = 'block';
                document.getElementById('statusText').innerText = 'ĐÃ DỪNG';
                document.getElementById('statusText').style.color = '#ef4444';
                if (pollTimer) { clearInterval(pollTimer); pollTimer = null; }
                resetValues();
            });
        }

        function updateStats() {
            if (!isRunning) return;
            fetch('/api/stats').then(r => r.json()).then(d => {
                document.getElementById('fpsText').innerText = d.fps + ' FPS';
                document.getElementById('valTotal').innerText = d.counts.total;
                document.getElementById('valCar').innerText = d.counts.car;
                document.getElementById('valMoto').innerText = d.counts.motorcycle;
                document.getElementById('valBus').innerText = d.counts.bus;
                document.getElementById('valTruck').innerText = d.counts.truck;
            }).catch(() => {});
        }

        function resetValues() {
            document.getElementById('fpsText').innerText = '0.0 FPS';
            document.getElementById('valTotal').innerText = '0';
            document.getElementById('valCar').innerText = '0';
            document.getElementById('valMoto').innerText = '0';
            document.getElementById('valBus').innerText = '0';
            document.getElementById('valTruck').innerText = '0';
        }

        document.getElementById('confSlider').oninput = function() {
            document.getElementById('confVal').innerText = this.value + '%';
            if (isRunning) {
                fetch('/api/conf', {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify({ conf: this.value / 100 })
                });
            }
        };
    </script>
</body>
</html>
"""


def run_web_mode(video_source=0):
    """Khởi chạy ứng dụng Web Flask thời gian thực được nhúng hoàn toàn trong file này."""
    if not FLASK_AVAILABLE:
        print("❌ Lỗi: Thư viện Flask chưa được cài đặt. Hãy chạy: pip install flask")
        return

    app = Flask(__name__)
    detector = VehicleDetector(model_path="yolov8n.pt", confidence=0.45)
    processor = ImageProcessor()

    state = {
        "is_running": False,
        "cap": None,
        "lock": threading.Lock(),
        "latest_frame": None,
        "counts": {"total": 0, "car": 0, "motorcycle": 0, "bus": 0, "truck": 0},
        "fps": 0.0,
    }

    def video_worker():
        while state["is_running"]:
            with state["lock"]:
                cap = state["cap"]
            if cap is None or not cap.isOpened():
                time.sleep(0.05)
                continue

            ret, frame = cap.read()
            if not ret:
                time.sleep(0.05)
                continue

            fps = processor.update_fps()
            detections = detector.detect(frame)
            counts = detector.count_vehicles(detections)
            counts["total"] = sum(counts.values())

            final_frame = processor.draw_hud_and_boxes(frame, detections, counts, detector.confidence)
            ret_enc, jpeg = cv2.imencode('.jpg', final_frame, [int(cv2.IMWRITE_JPEG_QUALITY), 85])

            if ret_enc:
                with state["lock"]:
                    state["latest_frame"] = jpeg.tobytes()
                    state["counts"] = counts
                    state["fps"] = fps

            time.sleep(0.01)

    @app.route('/')
    def index():
        return render_template_string(EMBEDDED_HTML_TEMPLATE)

    @app.route('/video_feed')
    def video_feed():
        def generate():
            while state["is_running"]:
                with state["lock"]:
                    frame = state["latest_frame"]
                if frame is not None:
                    yield (b'--frame\r\nContent-Type: image/jpeg\r\n\r\n' + frame + b'\r\n')
                time.sleep(0.03)
        return Response(generate(), mimetype='multipart/x-mixed-replace; boundary=frame')

    @app.route('/api/start', methods=['POST'])
    def api_start():
        data = request.get_json() or {}
        conf = data.get("conf", 0.45)
        detector.set_confidence(conf)

        with state["lock"]:
            if state["cap"] is not None:
                state["cap"].release()
            state["cap"] = cv2.VideoCapture(video_source)
            state["is_running"] = True

        threading.Thread(target=video_worker, daemon=True).start()
        return jsonify({"status": "ok", "message": "Started"})

    @app.route('/api/stop', methods=['POST'])
    def api_stop():
        with state["lock"]:
            state["is_running"] = False
            if state["cap"] is not None:
                state["cap"].release()
                state["cap"] = None
            state["latest_frame"] = None
            state["counts"] = {"total": 0, "car": 0, "motorcycle": 0, "bus": 0, "truck": 0}
            state["fps"] = 0.0
        return jsonify({"status": "ok", "message": "Stopped"})

    @app.route('/api/stats')
    def api_stats():
        with state["lock"]:
            return jsonify({"counts": state["counts"], "fps": state["fps"]})

    @app.route('/api/conf', methods=['POST'])
    def api_conf():
        data = request.get_json() or {}
        detector.set_confidence(data.get("conf", 0.45))
        return jsonify({"status": "ok"})

    # Tự động lấy địa chỉ IP mạng LAN (Wi-Fi) để máy khác truy cập
    import socket
    lan_ip = "127.0.0.1"
    try:
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        s.connect(("8.8.8.8", 80))
        lan_ip = s.getsockname()[0]
        s.close()
    except Exception:
        pass

    print("\n" + "=" * 70)
    print("  🌐 WEB DASHBOARD ĐÃ SẴN SÀNG PHỤC VỤ:")
    print("  👉 Truy cập trên máy này:                http://localhost:5000")
    print(f"  👉 Máy người khác / Điện thoại (cùng WiFi): http://{lan_ip}:5000")
    print("  ⏹  Nhấn Ctrl + C để dừng máy chủ")
    print("=" * 70 + "\n")
    app.run(host="0.0.0.0", port=5000, debug=False, threaded=True)


# ==============================================================================
# 6. HÀM MAIN: MENU LỰA CHỌN PHƯƠNG THỨC CHẠY BÁO CÁO
# ==============================================================================
def main():
    print("=" * 70)
    print("  🚗 BÁO CÁO ĐỒ ÁN XỬ LÝ ẢNH: NHẬN DIỆN & ĐẾM XE BÃI ĐỖ (YOLOv8)")
    print("=" * 70)
    print("  CHỌN PHƯƠNG THỨC KHỞI CHẠY:")
    print("    [1] Chạy qua Cửa sổ OpenCV GUI (Xem video trực tiếp, phím tắt Q/P/S)")
    print("    [2] Chạy qua Trình duyệt Web Dashboard (Giao diện web http://127.0.0.1:5000)")
    print("=" * 70)

    mode = input("👉 Nhập chế độ muốn chạy (1 hoặc 2) [Mặc định 1]: ").strip()
    if mode not in ["1", "2"]:
        mode = "1"

    print("\n  CHỌN NGUỒN VIDEO ĐẦU VÀO:")
    print("    [1] Video mẫu có sẵn: uploads/sample_parking_demo.mp4")
    print("    [2] Video quay thực tế: uploads/Quay_man_hinh_2026-10-07_154410.mp4")
    print("    [3] Webcam máy tính trực tiếp (Camera 0)")
    print("    [4] Nhập đường dẫn file video hoặc link RTSP tùy chọn")

    choice = input("👉 Nhập nguồn video (1-4) [Mặc định 1]: ").strip()
    if not choice:
        choice = "1"

    base_dir = os.path.dirname(os.path.abspath(__file__))
    video_source = 0
    source_name = "Webcam"

    if choice == "1":
        video_source = os.path.join(base_dir, "uploads", "sample_parking_demo.mp4")
        source_name = "sample_parking_demo.mp4"
    elif choice == "2":
        fpath = os.path.join(base_dir, "uploads", "Quay_man_hinh_2026-10-07_154410.mp4")
        if os.path.exists(fpath):
            video_source = fpath
            source_name = "Quay_man_hinh_2026-10-07_154410.mp4"
        else:
            video_source = os.path.join(base_dir, "uploads", "sample_parking_demo.mp4")
            source_name = "sample_parking_demo.mp4"
    elif choice == "3":
        video_source = 0
        source_name = "Webcam máy tính"
    elif choice == "4":
        p = input("Nhập đường dẫn file video / link camera: ").strip()
        video_source = int(p) if p.isdigit() else p
        source_name = str(p)

    if mode == "1":
        run_opencv_mode(video_source, source_name)
    else:
        run_web_mode(video_source)


if __name__ == "__main__":
    main()
