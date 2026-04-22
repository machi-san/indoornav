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