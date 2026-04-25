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
STAIR_ALERT_COOLDOWN = 3
last_stair_alert_time = 0

# ============================================================================
# STAIR DETECTION - v1 (Hough Transform)
# ============================================================================
# Approach: Detect 3+ roughly-horizontal line segments using Hough Transform.
#
# Performance on 18-image test set:
#   - Recall: 100% (all real stairs detected)
#   - Precision: ~36% (false positives on hallways, bookshelves, blinds,
#     empty rooms, striped surfaces)
#
# Rationale for accepting low precision:
#   For a safety-critical assistive device, missing a real stair (false
#   negative) is far more dangerous than a false alarm (false positive).
#   The user can learn to tolerate occasional incorrect alerts; they cannot
#   recover from an unannounced fall.
#
# Attempted refinement (clustering filter):
#   Geometric filters on horizontal-line span and position were tested and
#   abandoned. Diagnostic analysis showed real stair images and confounders
#   (e.g. blinds_1, stairs_1) produced indistinguishable span/position
#   values. The discriminating signal lies in the structure of the regions
#   BETWEEN the horizontal lines (smooth risers vs. cluttered book spines),
#   not in the geometry of the lines themselves.
#
# Future work:
#   See Stair_Detection_Research_Outline.docx for a full analysis and
#   proposal for a stair-trained lightweight model.
# ============================================================================

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
        angle = np.degrees(np.arctan2(y2 - y1, x2 - x1))
        if abs(angle) < HORIZONTAL_TOLERANCE or abs(abs(angle) - 180) < HORIZONTAL_TOLERANCE:
            horizontal_count += 1

    # Step 5: Decide if it's stairs
    return horizontal_count >= MIN_LINES_FOR_STAIRS

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