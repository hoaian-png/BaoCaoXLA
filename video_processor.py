# ============================================================
# FILE: video_processor.py
# THÀNH VIÊN PHỤ TRÁCH: Thành viên 2 (Chuyên OpenCV & Xử Lý Ảnh)
# MÔ TẢ: Xử lý khung hình, vẽ bounding box, overlay HUD tiếng Việt
# ============================================================

import os
import time
import cv2
import numpy as np
from PIL import Image, ImageDraw, ImageFont


# Bảng màu đại diện cho từng loại phương tiện:
# - OpenCV yêu cầu hệ màu BGR
# - Pillow yêu cầu hệ màu RGB
COLORS_BGR = {
    "car":        (0, 220, 100),    # Xanh lá cây - Ô tô
    "motorcycle": (0, 165, 255),    # Màu cam (BGR) - Xe máy
    "bus":        (30, 80, 255),    # Màu đỏ cam - Xe buýt
    "truck":      (255, 120, 0),    # Xanh dương - Xe tải
}

COLORS_RGB = {
    "car":        (100, 220, 0),
    "motorcycle": (255, 165, 0),
    "bus":        (255, 80, 30),
    "truck":      (0, 120, 255),
}

# Tên tiếng Việt hiển thị thân thiện trên màn hình
LABEL_VN = {
    "car":        "Ô tô",
    "motorcycle": "Xe máy",
    "bus":        "Xe buýt",
    "truck":      "Xe tải",
}


def _get_font(size):
    """
    Tải font Unicode hỗ trợ đầy đủ tiếng Việt có sẵn trên hệ điều hành.
    """
    font_paths = [
        "C:/Windows/Fonts/segoeui.ttf",     # Windows - Segoe UI
        "C:/Windows/Fonts/arial.ttf",       # Windows - Arial
        "C:/Windows/Fonts/tahoma.ttf",      # Windows - Tahoma
        "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf",  # Linux
        "/System/Library/Fonts/Helvetica.ttc",              # macOS
    ]
    for path in font_paths:
        if os.path.exists(path):
            try:
                return ImageFont.truetype(path, size)
            except Exception:
                continue

    # Fallback font mặc định
    try:
        return ImageFont.load_default(size=size)
    except Exception:
        return ImageFont.load_default()


class VideoProcessor:
    """
    Lớp VideoProcessor chịu trách nhiệm:
    - Tính toán FPS thời gian thực.
    - Vẽ hộp giới hạn (Bounding Box) có màu riêng cho từng loại xe.
    - Vẽ chữ tiếng Việt sắc nét bằng Pillow (tránh lỗi font của OpenCV putText).
    - Vẽ bảng thông số HUD (Heads-up display) bán trong suốt góc trên khung hình.
    - Nén khung hình sang JPEG định dạng byte để truyền phát MJPEG.
    """

    def __init__(self):
        self.fps = 0.0
        self.prev_time = 0.0

        # Khởi tạo sẵn các cỡ font để tái sử dụng nhanh, tránh giật lag
        self.font_box = _get_font(16)
        self.font_hud_title = _get_font(16)
        self.font_hud_item = _get_font(14)

    def reset_timing(self):
        """Khởi động lại bộ đo FPS khi bắt đầu phiên mới."""
        self.fps = 0.0
        self.prev_time = 0.0

    def update_fps(self):
        """Tính toán FPS dựa trên khoảng thời gian giữa các khung hình."""
        cur = time.time()
        if self.prev_time > 0:
            delta = cur - self.prev_time
            if delta > 0:
                self.fps = round(1.0 / delta, 1)
        self.prev_time = cur

    def draw_detections(self, frame, detections, counts):
        """
        Vẽ Bounding Boxes và bảng thống kê tiếng Việt lên khung hình.

        Tham số:
            frame: Ảnh numpy mảng BGR.
            detections: Danh sách xe nhận diện được từ YOLO.
            counts: Thống kê số lượng từng loại.

        Trả về:
            frame: Ảnh đã được vẽ thông tin hoàn chỉnh.
        """
        if frame is None:
            return None

        # Cập nhật FPS
        self.update_fps()
        h, w = frame.shape[:2]

        # 1. Vẽ các đường khung Bounding Box bằng OpenCV (tốc độ cao)
        for item in detections:
            x1, y1, x2, y2 = item["box"]
            label = item["label"]
            color_bgr = COLORS_BGR.get(label, (0, 255, 0))

            # Giới hạn trong kích thước ảnh
            x1, y1 = max(0, x1), max(0, y1)
            x2, y2 = min(w, x2), min(h, y2)

            # Vẽ viền hộp chữ nhật
            cv2.rectangle(frame, (x1, y1), (x2, y2), color_bgr, 2)

            # Vẽ điểm neo góc để tăng tính thẩm mỹ
            corner_len = min(15, (x2 - x1) // 4, (y2 - y1) // 4)
            if corner_len > 0:
                cv2.line(frame, (x1, y1), (x1 + corner_len, y1), (255, 255, 255), 3)
                cv2.line(frame, (x1, y1), (x1, y1 + corner_len), (255, 255, 255), 3)

        # 2. Vẽ nền HUD bán trong suốt góc trên bên trái
        hud_w, hud_h = 240, 165
        overlay = frame.copy()
        cv2.rectangle(overlay, (12, 12), (12 + hud_w, 12 + hud_h), (15, 23, 42), -1)
        # Pha trộn nền với độ mờ 65%
        cv2.addWeighted(overlay, 0.65, frame, 0.35, 0, frame)
        # Viền neon trang trí cho HUD
        cv2.rectangle(frame, (12, 12), (12 + hud_w, 12 + hud_h), (59, 130, 246), 1)

        # 3. Chuyển sang Pillow để vẽ toàn bộ nhãn tiếng Việt chuẩn Unicode
        frame_rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
        pil_img = Image.fromarray(frame_rgb)
        draw = ImageDraw.Draw(pil_img)

        # Vẽ nhãn trên đầu từng xe
        for item in detections:
            x1, y1 = item["box"][:2]
            label = item["label"]
            conf = int(item["confidence"] * 100)
            vn_name = LABEL_VN.get(label, label)
            text_str = f"{vn_name} {conf}%"
            color_rgb = COLORS_RGB.get(label, (0, 255, 0))

            # Đo kích thước chữ
            bbox = draw.textbbox((0, 0), text_str, font=self.font_box)
            tw = bbox[2] - bbox[0]
            th = bbox[3] - bbox[1]

            # Tọa độ hộp nhãn (tránh tràn viền trên)
            tag_x = max(2, x1)
            tag_y = max(2, y1 - th - 8)

            # Vẽ background cho chữ
            draw.rectangle(
                [tag_x, tag_y, tag_x + tw + 10, tag_y + th + 6],
                fill=color_rgb
            )
            # Vẽ chữ màu trắng
            draw.text(
                (tag_x + 5, tag_y + 2),
                text_str,
                font=self.font_box,
                fill=(255, 255, 255)
            )

        # 4. Vẽ nội dung trong bảng HUD
        total = sum(counts.values())
        # Tiêu đề HUD
        draw.text(
            (22, 20),
            f"TỔNG SỐ XE: {total} | FPS: {self.fps}",
            font=self.font_hud_title,
            fill=(255, 255, 255)
        )
        draw.line([(22, 45), (22 + hud_w - 20, 45)], fill=(100, 116, 139), width=1)

        # Danh sách chi tiết từng loại
        y_pos = 54
        for key in ["car", "motorcycle", "bus", "truck"]:
            vn_name = LABEL_VN.get(key, key)
            cnt = counts.get(key, 0)
            color_rgb = COLORS_RGB.get(key, (255, 255, 255))

            # Chấm tròn chỉ thị màu
            draw.ellipse([24, y_pos + 4, 32, y_pos + 12], fill=color_rgb)
            # Tên loại xe
            draw.text((38, y_pos), f"{vn_name}:", font=self.font_hud_item, fill=(203, 213, 225))
            # Số lượng
            draw.text((180, y_pos), f"{cnt} xe", font=self.font_hud_item, fill=(255, 255, 255))
            y_pos += 26

        # 5. Chuyển ngược lại sang OpenCV BGR
        final_frame = cv2.cvtColor(np.array(pil_img), cv2.COLOR_RGB2BGR)
        return final_frame

    def encode_frame(self, frame):
        """
        Nén ảnh thành chuỗi byte JPEG để truyền phát stream web.
        """
        if frame is None:
            return None

        # Chất lượng JPEG 80: Đẹp, dung lượng nhỏ, stream mượt mà
        ret, buf = cv2.imencode(".jpg", frame, [cv2.IMWRITE_JPEG_QUALITY, 80])
        if not ret:
            return None
        return buf.tobytes()
