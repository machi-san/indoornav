import cv2
import numpy as np
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