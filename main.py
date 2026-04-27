import threading
import time
import cv2

from speech import start_speech_thread, speak
from ultrasonic import check_distance
from vision import process_detections, run_inference, filter_detections, preprocess_frame, load_model
from stairs import process_stair_detection

# ============================================================================
# SHARED STATE
# ============================================================================
# The latest camera frame, updated by the camera thread and read by AI/stairs.
# Single-variable assignment is atomic in CPython (GIL guarantee), so no lock
# needed for v1. See V2_ENHANCEMENTS.md for forward-compatibility notes.
latest_frame = None

# Flag to signal all threads to stop. Set True when user hits Ctrl+C.
shutdown_flag = False

# AI inference state - loaded once at startup
interpreter = None
labels = None

# ============================================================================
# MOCK CAMERA (development-only stopgap until Pi camera arrives)
# ============================================================================
USE_MOCK_CAMERA = True   # Set False when Pi hardware arrives

def get_mock_frame():
    """Returns a black 480x640 frame for development testing.
    Replace by real cv2.VideoCapture when hardware arrives."""
    import numpy as np
    return np.zeros((480, 640, 3), dtype=np.uint8)