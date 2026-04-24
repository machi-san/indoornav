import cv2
import numpy as np
import time
from speech import speak

# Stair detection thresholds
MIN_LINES_FOR_STAIRS = 3       # Minimum parallel horizontal lines to consider it stairs
HORIZONTAL_TOLERANCE = 10      # Lines within this many degrees of horizontal are "horizontal"
EDGE_DETECTION_LOW = 50        # Canny lower threshold
EDGE_DETECTION_HIGH = 150      # Canny upper threshold

# Clustering filter thresholds
CLUSTER_SPAN_MAX = 0.4       # Horizontal lines must span less than this fraction of image height
CLUSTER_POSITION_MIN = 0.5   # Bottommost horizontal line must sit below this fraction of image height

# Priority for stair alerts (highest urgency - fall hazard)
STAIR_ALERT_PRIORITY = 1
STAIR_ALERT_COOLDOWN = 3
last_stair_alert_time = 0

def detect_stairs(frame):
    # Step 1: Convert to greyscale (faster processing, edges only need brightness)
    grey = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)

    # Step 2: Detect edges using Canny
    edges = cv2.Canny(grey, EDGE_DETECTION_LOW, EDGE_DETECTION_HIGH)

    # Step 3: Find lines using Hough Transform
    lines = cv2.HoughLinesP(
        edges,
        rho=1,
        theta=np.pi / 180,
        threshold=80,
        minLineLength=50,
        maxLineGap=10
    )

    # If no lines were found, definitely not stairs
    if lines is None:
        return False

     # Step 4: Collect y-coordinates of roughly horizontal lines
    horizontal_y_values = []
    for line in lines:
        x1, y1, x2, y2 = line[0]
        # Calculate the angle of the line in degrees
        angle = np.degrees(np.arctan2(y2 - y1, x2 - x1))
        # A horizontal line has an angle near 0 (or near 180/-180)
        if abs(angle) < HORIZONTAL_TOLERANCE or abs(abs(angle) - 180) < HORIZONTAL_TOLERANCE:
                # Store the average y of the two endpoints as the line's position
                horizontal_y_values.append((y1 + y2) / 2)

        # Step 5: Must have enough horizontal lines
    print(f"    horizontal lines found: {len(horizontal_y_values)}")
    if len(horizontal_y_values) < MIN_LINES_FOR_STAIRS:
        return False

        # Step 6: Clustering filter - check tightness and position
    image_height = frame.shape[0]
    max_y = max(horizontal_y_values)
    min_y = min(horizontal_y_values)

    span_ratio = (max_y - min_y) / image_height
    position_ratio = max_y / image_height

    print(f"    span={span_ratio:.2f}, position={position_ratio:.2f}, lines={len(horizontal_y_values)}")

    # Tightness: cluster must span less than 40% of image height
    if span_ratio >= CLUSTER_SPAN_MAX:
            return False

        # Position: bottommost line must sit in the lower half
    if position_ratio <= CLUSTER_POSITION_MIN:
            return False

        # Passed all filters - looks like stairs
    return True

def process_stair_detection(frame):
    global last_stair_alert_time
    current_time = time.time()

    # Run the detection
    if not detect_stairs(frame):
        return

    # Stairs detected - check rate limit before alerting
    if current_time - last_stair_alert_time < STAIR_ALERT_COOLDOWN:
        return

    # Fire the alert
    speak(STAIR_ALERT_PRIORITY, "Stairs ahead")
    last_stair_alert_time = current_time

if __name__ == "__main__":
    import os

    test_folder = "test_images"
    test_files = sorted(os.listdir(test_folder))

    print(f"Testing stair detection on {len(test_files)} images...\n")

    for filename in test_files:
        filepath = os.path.join(test_folder, filename)
        frame = cv2.imread(filepath)

        if frame is None:
            print(f"  ⚠  Could not load {filename} - skipping")
            continue

        is_stairs = detect_stairs(frame)
        verdict = "STAIRS DETECTED" if is_stairs else "no stairs"
        print(f"  {filename:30s} → {verdict}")

    print("\nDone.")