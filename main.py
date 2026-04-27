import threading
import time
import cv2

from speech import start_speech_thread
# ultrasonic_loop is imported inside main() conditionally, since RPi.GPIO would crash on Windows
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



# ============================================================================
# MOCK CAMERA (development-only stopgap until Pi camera arrives)
# ============================================================================
USE_MOCK_CAMERA = True   # Set False when Pi hardware arrives

def get_mock_frame():
    """Returns a black 480x640 frame for development testing.
    Replace by real cv2.VideoCapture when hardware arrives."""
    import numpy as np
    return np.zeros((480, 640, 3), dtype=np.uint8)

# ============================================================================
# CAMERA THREAD
# ============================================================================

def camera_loop():
    """Continuously captures frames and updates the shared latest_frame.
    Runs as its own thread so AI and stairs threads always have a fresh frame."""
    global latest_frame

    if USE_MOCK_CAMERA:
        # Development mode - feed mock black frames at ~30fps
        while not shutdown_flag:
            latest_frame = get_mock_frame()
            time.sleep(0.033)   # ~30 frames per second
    else:
        # Hardware mode - capture from real camera
        cap = cv2.VideoCapture(0)
        if not cap.isOpened():
            print("ERROR: Could not open camera. Exiting camera thread.")
            return

        try:
            while not shutdown_flag:
                ret, frame = cap.read()
                if ret:
                    latest_frame = frame
                else:
                    print("WARNING: Failed to grab frame")
                    time.sleep(0.1)
        finally:
            cap.release()
            print("Camera released.")

# ============================================================================
# AI DETECTION THREAD
# ============================================================================

def ai_loop():
    """Continuously runs object detection on the latest frame.
    Reads from latest_frame, runs MobileNet SSD inference, fires alerts."""
    global interpreter, labels

    # Load the model once at thread startup
    interpreter, labels = load_model()
    if interpreter is None:
        print("ERROR: Could not load AI model. Exiting AI thread.")
        return

    print("AI thread ready.")

    while not shutdown_flag:
        # Skip if no frame is available yet
        if latest_frame is None:
            time.sleep(0.05)
            continue

        # Snapshot the current frame so we don't see mid-update changes
        frame = latest_frame

        # Run the full AI pipeline
        input_tensor = preprocess_frame(frame)
        boxes, classes, scores = run_inference(interpreter, input_tensor)
        detections = filter_detections(boxes, classes, scores)
        process_detections(detections)

        # Don't hammer the CPU - AI inference is the slowest step anyway
        time.sleep(0.1)

# ============================================================================
# STAIR DETECTION THREAD
# ============================================================================

def stairs_loop():
    """Continuously runs stair detection on the latest frame.
    Reads from latest_frame, runs Hough-based detection, fires Priority 1 alerts."""
    print("Stairs thread ready.")

    while not shutdown_flag:
        # Skip if no frame is available yet
        if latest_frame is None:
            time.sleep(0.05)
            continue

        # Snapshot the current frame so we don't see mid-update changes
        frame = latest_frame

        # Run the stair detection pipeline (handles its own rate limiting)
        process_stair_detection(frame)

        # Stair detection is lighter than AI - we can afford a faster loop
        time.sleep(0.05)

# ============================================================================
# MAIN ENTRY POINT
# ============================================================================

def main():
    """Start all threads and wait for shutdown signal."""
    global shutdown_flag

    print("=" * 60)
    print("Indoor Navigation System - starting up")
    print(f"Mock camera: {USE_MOCK_CAMERA}")
    print("=" * 60)

    # Start the speech consumer thread first - everything else depends on it
    start_speech_thread()
    print("Speech thread started.")

    # Build the list of worker threads
    threads = [
        threading.Thread(target=camera_loop, name="CameraThread", daemon=True),
        threading.Thread(target=ai_loop, name="AIThread", daemon=True),
        threading.Thread(target=stairs_loop, name="StairsThread", daemon=True),
    ]

    # Ultrasonic only runs on real hardware - skip in mock mode
    if not USE_MOCK_CAMERA:
        from ultrasonic import ultrasonic_loop
        threads.append(
            threading.Thread(target=ultrasonic_loop, name="UltrasonicThread", daemon=True)
        )
    else:
        print("Skipping ultrasonic thread (mock mode - no GPIO available)")

    # Start all threads
    for t in threads:
        t.start()
        print(f"Started: {t.name}")

    print("=" * 60)
    print("All threads running. Press Ctrl+C to shut down.")
    print("=" * 60)

    # Main thread waits for keyboard interrupt
    try:
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        print("\nShutdown signal received. Stopping threads...")
        shutdown_flag = True
        # Give threads a moment to notice the flag and exit cleanly
        time.sleep(1)
        print("Shutdown complete.")


if __name__ == "__main__":
    main()