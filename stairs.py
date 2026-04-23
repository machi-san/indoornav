import cv2
import numpy as np
import time
from speech import speak

# Stair detection thresholds
MIN_LINES_FOR_STAIRS = 3       # Minimum parallel horizontal lines to consider it stairs
HORIZONTAL_TOLERANCE = 10      # Lines within this many degrees of horizontal are "horizontal"
EDGE_DETECTION_LOW = 50        # Canny lower threshold
EDGE_DETECTION_HIGH = 150      # Canny upper threshold

# Priority for stair alerts (highest urgency - fall hazard)
STAIR_ALERT_PRIORITY = 1

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

    # Step 4: Count how many lines are roughly horizontal
    horizontal_count = 0
    for line in lines:
        x1, y1, x2, y2 = line[0]
        # Calculate the angle of the line in degrees
        angle = np.degrees(np.arctan2(y2 - y1, x2 - x1))
        # A horizontal line has an angle near 0 (or near 180/-180)
        if abs(angle) < HORIZONTAL_TOLERANCE or abs(abs(angle) - 180) < HORIZONTAL_TOLERANCE:
            horizontal_count += 1

    # Step 5: Decide if it's stairs
    return horizontal_count >= MIN_LINES_FOR_STAIRS

# Rate limiting: minimum seconds between repeat stair alerts
STAIR_ALERT_COOLDOWN = 3

# Track when stairs were last announced
last_stair_alert_time = 0

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