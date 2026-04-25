import cv2
import numpy as np
import time
from speech import speak

# Try to import the Pi-only AI library; fall back gracefully on Windows
try:
    from tflite_runtime.interpreter import Interpreter
    AI_AVAILABLE = True
except ImportError:
    AI_AVAILABLE = False
    print("Warning: tflite_runtime not available - AI detection disabled (expected on Windows)")

# Model expects 300x300 RGB images with pixel values 0-1
MODEL_INPUT_SIZE = 300

def preprocess_frame(frame):
    # Step 1: Resize to 300x300
    resized = cv2.resize(frame, (MODEL_INPUT_SIZE, MODEL_INPUT_SIZE))

    # Step 2: Convert BGR to RGB
    rgb = cv2.cvtColor(resized, cv2.COLOR_BGR2RGB)

    # Step 3: Normalise pixel values to 0-1
    normalised = rgb / 255.0

    # Step 4: Add a batch dimension (the model expects a batch of images)
    batched = np.expand_dims(normalised, axis=0).astype(np.float32)

    return batched
# Path to the model file (will exist on the Pi)
MODEL_PATH = "models/mobilenet_ssd.tflite"

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

# Classes relevant to indoor navigation (COCO dataset labels)
RELEVANT_CLASSES = {
    0: "person",
    56: "chair",
    57: "couch",
    58: "potted plant",
    59: "bed",
    60: "dining table",
    72: "refrigerator",
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

# Priority for AI-detected objects in the ahead zone
AI_ALERT_PRIORITY_AHEAD = 3   # Object directly in walking path
AI_ALERT_PRIORITY_SIDE = 4    # Object slightly off-centre forward

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
            priority = AI_ALERT_PRIORITY_AHEAD
        elif zone == "left":
            phrase = f"{class_name} on your left"
            priority = AI_ALERT_PRIORITY_SIDE
        elif zone == "right":
            phrase = f"{class_name} on your right"
            priority = AI_ALERT_PRIORITY_SIDE
        else:
            # Unexpected zone value - skip this detection
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