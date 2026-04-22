import cv2
import numpy as np
from speech import speak
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