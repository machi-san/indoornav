import cv2
import numpy as np
import time
from speech import speak

# Platform-conditional TFLite import:
# - Windows (mock-mode dev): tflite_runtime ships wheels for Python <=3.12
# - Linux/Pi (deployment): ai_edge_litert is the modern successor, ships Python 3.13 wheels
# The Interpreter API is identical between the two libraries.
# If neither is available, AI detection degrades gracefully.
import platform

try:
    if platform.system() == "Windows":
        from tflite_runtime.interpreter import Interpreter
    else:
        from ai_edge_litert.interpreter import Interpreter
    AI_AVAILABLE = True
except ImportError:
    AI_AVAILABLE = False
    print("Warning: TFLite interpreter not available - AI detection disabled")

# Model expects 300x300 RGB images with pixel values 0-1
MODEL_INPUT_SIZE = 320

def preprocess_frame(frame):
    # Step 1: Resize to model's expected input size
    resized = cv2.resize(frame, (MODEL_INPUT_SIZE, MODEL_INPUT_SIZE))

    # Step 2: Convert BGR (OpenCV default) to RGB (model expectation)
    rgb = cv2.cvtColor(resized, cv2.COLOR_BGR2RGB)

    # Step 3: Add a batch dimension. Model expects uint8 input (0-255),
    # not normalised floats - so no division by 255 here.
    batched = np.expand_dims(rgb, axis=0).astype(np.uint8)

    return batched

# Path to the model file (will exist on the Pi)
MODEL_PATH = "models/efficientdet_lite0.tflite"

# Initialise the model interpreter (only runs if AI is available)
interpreter = None
input_details = None
output_details = None

def load_model():
    global interpreter, input_details, output_details
    if not AI_AVAILABLE:
        print("Skipping model load - AI not available on this platform")
        return
    interpreter = Interpreter(model_path=MODEL_PATH)
    interpreter.allocate_tensors()
    input_details = interpreter.get_input_details()
    output_details = interpreter.get_output_details()
    print("Model loaded successfully")

def run_inference(preprocessed_frame):
    if not AI_AVAILABLE or interpreter is None:
        return []

    # Feed the preprocessed frame into the model
    interpreter.set_tensor(input_details[0]['index'], preprocessed_frame)

    # Run the model
    interpreter.invoke()

    # Extract the three outputs: bounding boxes, classes, confidence scores
    boxes = interpreter.get_tensor(output_details[0]['index'])[0]
    classes = interpreter.get_tensor(output_details[1]['index'])[0]
    scores = interpreter.get_tensor(output_details[2]['index'])[0]

    return boxes, classes, scores

# Minimum confidence to trust a detection
CONFIDENCE_THRESHOLD = 0.5

# Class IDs match EfficientDet-Lite0's embedded labelmap (COCO-90 scheme).
# These were updated from COCO-80 during the model swap from MobileNet SSD
# to EfficientDet-Lite0 on Pi deployment.
RELEVANT_CLASSES = {
    0: "person",
    61: "chair",
    62: "couch",
    63: "potted plant",
    64: "bed",
    66: "dining table",
    81: "refrigerator",
}

def filter_detections(boxes, classes, scores):
    filtered = []
    for i in range(len(scores)):
        if scores[i] < CONFIDENCE_THRESHOLD:
            continue
        class_id = int(classes[i])
        if class_id not in RELEVANT_CLASSES:
            continue
        filtered.append({
            "class_name": RELEVANT_CLASSES[class_id],
            "confidence": float(scores[i]),
            "box": boxes[i]
        })
    return filtered

# Zone boundaries based on horizontal bounding box centre
LEFT_MAX = 0.33
AHEAD_MAX = 0.67

def get_zone(box):
    ymin, xmin, ymax, xmax = box
    centre_x = (xmin + xmax) / 2
    if centre_x < LEFT_MAX:
        return "left"
    elif centre_x < AHEAD_MAX:
        return "ahead"
    else:
        return "right"

# AI alert priorities (lower number = more urgent)
# Default for any class not explicitly listed
AI_ALERT_PRIORITY_DEFAULT = 4

# Per-class priorities for ahead-zone detections
# Higher urgency reflects unpredictability and lack of mechanical constraints
CLASS_PRIORITIES_AHEAD = {
    "person": 3,   # Higher urgency - moves unpredictably, may not see user
}

# Per-class priorities for side-zone detections
# All side detections currently default to 4 - distinction is captured in phrasing
CLASS_PRIORITIES_SIDE = {
    "person": 4,
}

# Rate limiting: minimum seconds between repeat alerts for the same class
ALERT_COOLDOWN = 3

# Track when each class was last announced
last_alert_times = {}

def process_detections(detections):
    current_time = time.time()
    for detection in detections:
        zone = get_zone(detection["box"])
        class_name = detection["class_name"]

        # Build the spoken phrase and pick the priority based on zone
        if zone == "ahead":
            phrase = f"{class_name} ahead"
            priority = CLASS_PRIORITIES_AHEAD.get(class_name, AI_ALERT_PRIORITY_DEFAULT)
        elif zone == "left":
            phrase = f"{class_name} on your left"
            priority = CLASS_PRIORITIES_SIDE.get(class_name, AI_ALERT_PRIORITY_DEFAULT)
        elif zone == "right":
            phrase = f"{class_name} on your right"
            priority = CLASS_PRIORITIES_SIDE.get(class_name, AI_ALERT_PRIORITY_DEFAULT)
        else:
            continue

        # Rate limit: skip if this class was announced within the cooldown window
        if class_name in last_alert_times:
            if current_time - last_alert_times[class_name] < ALERT_COOLDOWN:
                continue

        # Fire the alert and update the timestamp
        speak(priority, phrase)
        last_alert_times[class_name] = current_time

if __name__ == "__main__":
    # Start the speech thread so alerts actually get spoken
    from speech import start_speech_thread
    start_speech_thread()

    # Test directional cues with mock detections
    print("Testing directional cues with mock detections...\n")

    # Three mock detections - one in each zone
    # Box format: [ymin, xmin, ymax, xmax] in normalised coords
    test_detections = [
        {
            "class_name": "person",
            "confidence": 0.95,
            "box": [0.3, 0.10, 0.9, 0.30]   # centre_x = 0.20 -> left zone
        },
        {
            "class_name": "chair",
            "confidence": 0.90,
            "box": [0.3, 0.40, 0.9, 0.60]   # centre_x = 0.50 -> ahead zone
        },
        {
            "class_name": "door",
            "confidence": 0.85,
            "box": [0.3, 0.70, 0.9, 0.90]   # centre_x = 0.80 -> right zone
        }
    ]

    # Process the mock detections - each should fire a different alert
    process_detections(test_detections)

    # Give the speech thread a moment to actually speak before the program exits
    import time
    time.sleep(8)

    print("\nDone.")
