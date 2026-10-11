# ============================================================
# FILE: api/app.py
# MÔ TẢ: Alias cho api/index.py đảm bảo Vercel tự động nhận diện mọi cấu hình
# ============================================================
import os
import sys

CURRENT_DIR = os.path.dirname(os.path.abspath(__file__))
if CURRENT_DIR not in sys.path:
    sys.path.insert(0, CURRENT_DIR)

from index import app
