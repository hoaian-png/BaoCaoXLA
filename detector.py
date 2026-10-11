# ============================================================
# FILE: detector.py
# THÀNH VIÊN PHỤ TRÁCH: Thành viên 1 (Chuyên AI / YOLO)
# MÔ TẢ: Module nhận diện phương tiện giao thông sử dụng YOLOv8
# ============================================================

import os
from ultralytics import YOLO  # Thư viện mô hình YOLOv8 của Ultralytics


class VehicleDetector:
    """
    Lớp VehicleDetector chịu trách nhiệm:
    1. Tải mô hình YOLOv8 (tự động tải bản nhẹ yolov8n.pt nếu chưa có).
    2. Nhận diện các phương tiện trong từng khung hình (frame).
    3. Phân loại theo 4 nhóm chính: Ô tô, Xe máy, Xe buýt, Xe tải.
    4. Đếm số lượng xe đang hiện diện trong bãi đỗ.
    """

    # Danh mục các lớp phương tiện theo chuẩn COCO dataset:
    # Class ID:
    #   2 -> car (Ô tô)
    #   3 -> motorcycle (Xe máy)
    #   5 -> bus (Xe buýt)
    #   7 -> truck (Xe tải)
    VEHICLE_CLASSES = {
        2: "car",
        3: "motorcycle",
        5: "bus",
        7: "truck",
    }

    def __init__(self, model_path="yolov8n.pt", confidence=0.45):
        """
        Khởi tạo bộ nhận diện.

        Tham số:
            model_path (str): Đường dẫn tới trọng số YOLOv8 (.pt).
                              Mặc định là 'yolov8n.pt' (bản Nano siêu nhẹ và nhanh).
            confidence (float): Ngưỡng độ tin cậy tối thiểu (0.1 - 0.9).
        """
        self.model_path = model_path
        self.confidence = float(confidence)

        print(f"[AI] Đang nạp mô hình YOLOv8: {self.model_path} ...")
        # Khởi tạo mô hình YOLO
        self.model = YOLO(self.model_path)
        print("[AI] Khởi tạo mô hình thành công!")

    def set_confidence(self, new_conf):
        """Cập nhật ngưỡng tin cậy theo yêu cầu từ giao diện web."""
        try:
            val = float(new_conf)
            if 0.1 <= val <= 0.95:
                self.confidence = val
        except (ValueError, TypeError):
            pass

    def detect(self, frame):
        """
        Phát hiện phương tiện trong một khung hình ảnh.

        Tham số:
            frame: Ảnh numpy array (BGR từ OpenCV).

        Trả về:
            list: Danh sách các đối tượng phát hiện, ví dụ:
                  [
                      {
                          "box": [x1, y1, x2, y2],
                          "label": "car",
                          "class_id": 2,
                          "confidence": 0.88
                      },
                      ...
                  ]
        """
        if frame is None:
            return []

        # Chạy inference với mô hình YOLOv8
        # verbose=False: Tắt in log ra terminal mỗi frame để tăng tốc độ
        results = self.model(frame, conf=self.confidence, verbose=False)

        detections = []

        for result in results:
            boxes = result.boxes
            if boxes is None:
                continue

            for box in boxes:
                # Lấy class id dạng số nguyên
                class_id = int(box.cls[0].item())

                # Chỉ giữ lại các loại phương tiện trong danh mục quan tâm
                if class_id in self.VEHICLE_CLASSES:
                    # Lấy tọa độ hộp bao [x1, y1, x2, y2]
                    coords = box.xyxy[0].tolist()
                    x1, y1, x2, y2 = [int(v) for v in coords]

                    # Độ tin cậy (confidence score)
                    conf = round(float(box.conf[0].item()), 2)
                    label = self.VEHICLE_CLASSES[class_id]

                    detections.append({
                        "box": [x1, y1, x2, y2],
                        "label": label,
                        "class_id": class_id,
                        "confidence": conf
                    })

        return detections

    def count_vehicles(self, detections):
        """
        Đếm số lượng từng loại xe đang hiện diện trong khung hình hiện tại.
        (Đếm tức thời theo thời gian thực cho bãi đỗ xe).

        Tham số:
            detections (list): Danh sách trả về từ hàm detect().

        Trả về:
            dict: Thống kê số lượng từng loại, ví dụ:
                  {'car': 4, 'motorcycle': 10, 'bus': 1, 'truck': 0}
        """
        counts = {name: 0 for name in self.VEHICLE_CLASSES.values()}

        for item in detections:
            name = item.get("label")
            if name in counts:
                counts[name] += 1

        return counts
