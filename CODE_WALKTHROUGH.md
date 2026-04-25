# 🛠 Code Walkthrough — Indoor Navigation Project

A block-by-block reference of all the code built collaboratively, organised by task and then by file. For each block: **what it does**, **why it's written that way**, and any **key design decisions** or **gotchas** worth remembering.

This is meant as a study and report-writing aid — refer back to it whenever a decision needs justifying or a line needs re-explaining.

---

## 📑 Table of Contents

- [Task 10 — Ultrasonic Sensors & Audio Alert System](#task-10--ultrasonic-sensors--audio-alert-system)
  - [`speech.py` — Priority-queued audio alerts](#speechpy--priority-queued-audio-alerts)
  - [`ultrasonic.py` — Multi-sensor distance reading and alerting](#ultrasonicpy--multi-sensor-distance-reading-and-alerting)
- [Task 11 — Object & Scene Detection with AI](#task-11--object--scene-detection-with-ai)
  - [`vision.py` — MobileNet SSD inference pipeline](#visionpy--mobilenet-ssd-inference-pipeline)
- [Task 12 — Stair Detection](#task-12--stair-detection)
  - [`stairs.py` — Hough-line-based stair detection](#stairspy--hough-line-based-stair-detection)

---

# Task 10 — Ultrasonic Sensors & Audio Alert System

## `speech.py` — Priority-queued audio alerts

### Block 1 — Imports and engine setup

```python
import pyttsx3
import queue
import threading

engine = pyttsx3.init()
engine.setProperty('rate', 150)
engine.setProperty('volume', 1.0)

alert_queue = queue.PriorityQueue()
```

**What it does:** Sets up the text-to-speech engine and creates the central message queue that all alerts flow through.

**Why it's written this way:**

- `pyttsx3` is cross-platform (Windows, macOS, Linux) and works offline — important because the device shouldn't need Wi-Fi to talk.
- `queue.PriorityQueue` was chosen over a regular list because it **auto-sorts** items by priority on insertion. Lower priority number = more urgent, so fall hazards (1) will always come out before close obstacles (2), regardless of the order they were added.
- `threading` is imported here because the speech loop will eventually run in a background thread so it doesn't block the main program.

### Block 2 — The `speak()` function

```python
def speak(priority, message):
    alert_queue.put((priority, message))
```

**What it does:** The public entry point that other modules (`ultrasonic.py`, `vision.py`, `stairs.py`) use to fire an alert. Takes a priority number and a message and drops a tuple onto the queue.

**Why it's written this way:**

- Tuples are used because `PriorityQueue` sorts by the first element — so `(1, "stairs ahead")` will always come out before `(2, "obstacle ahead")` even if added later.
- The function deliberately doesn't speak anything itself — it just queues. This **separates "add to queue" from "actually speak"**, which lets the speaking happen in the background.

### Block 3 — The `process_queue()` function (final working version)

```python
def process_queue():
    while True:
        priority, message = alert_queue.get()
        subprocess.run([
            "powershell", "-Command",
            f"Add-Type -AssemblyName System.Speech; "
            f"(New-Object System.Speech.Synthesis.SpeechSynthesizer).Speak('{message}')"
        ])
```

**What it does:** The background consumer — it waits for messages on the queue and speaks them one at a time.

**Why it's written this way:**

- `while True` makes this loop forever — it's supposed to. This loop runs in a daemon thread that ends when the main program ends.
- `alert_queue.get()` **blocks** (waits patiently) until something is on the queue. This is efficient — no CPU spinning, no polling.
- We ended up using `subprocess.run` + PowerShell because `pyttsx3`'s `runAndWait()` has a Windows-specific bug where the engine goes silent after the first call inside a thread.
- **When the Pi arrives**, this will be swapped back to `engine.say(message); engine.runAndWait()` because `pyttsx3` works reliably on Linux.

**Key design decision — cross-platform speech:** The queue, threading, and priority logic are all platform-independent. Only the actual speech call changes between Windows (PowerShell) and Pi (pyttsx3). This is a clean separation worth calling out in the report.

### Block 4 — `start_speech_thread()`

```python
def start_speech_thread():
    thread = threading.Thread(target=process_queue, daemon=True)
    thread.start()
```

**What it does:** Kicks off the speech loop as a background thread so the main program can keep running.

**Why it's written this way:**

- `daemon=True` means the thread dies when the main program exits. Without this, the program would hang on exit because `while True` would keep the thread alive forever.
- The thread only needs to be started once, at program startup.

**Gotcha discovered the hard way:** Forgetting to import `threading` caused this function to silently fail — the thread never actually started, so `process_queue` ran in the main thread instead, blocking everything. Lesson: **PyCharm's "unresolved reference" warnings are real signals, not cosmetic noise.**

### Block 5 — The test block

```python
if __name__ == "__main__":
    start_speech_thread()
    speak(2, "Obstacle ahead")
    speak(1, "Careful, stairs ahead")
    speak(3, "Obstacle, left side")

    import time
    time.sleep(10)
```

**What it does:** Proves the whole system works end-to-end. Starts the thread, adds three alerts in "wrong" order (2, 1, 3), then sleeps 10 seconds to give the thread time to speak them all.

**Why the ordering matters:** If the priority queue works correctly, the user hears them in 1-2-3 order, not 2-1-3. That's the whole point of the queue.

**Why `time.sleep(10)` is needed:** Without it, the main program would exit immediately and the daemon thread would be killed before speaking anything. The sleep keeps the program alive long enough for the queue to drain.

---

## `ultrasonic.py` — Multi-sensor distance reading and alerting

### Block 1 — Imports and configuration

```python
import RPi.GPIO as GPIO
import time
from speech import speak, start_speech_thread

SENSOR_PINS = {
    "north":      {"trig": 17, "echo": 27},
    "north_east": {"trig": 22, "echo": 23},
    "north_west": {"trig": 24, "echo": 25},
}

CAUTION_DISTANCE = 100
STOP_DISTANCE = 50
```

**What it does:** Sets up the hardware interface and defines three sensors plus their distance thresholds.

**Why it's written this way:**

- Using a **nested dictionary** for `SENSOR_PINS` means the code can refer to sensors by meaningful names (`"north"`) rather than pin numbers, and each sensor's trigger/echo pins travel together as a unit.
- The thresholds are **module-level constants** at the top of the file — if we need to re-tune them later, everything is in one obvious place.
- Distances are in centimetres because that's what the HC-SR04 naturally reports.

### Block 2 — Alert phrase library

```python
ALERT_PHRASES = {
    "north": {
        "stop":    "Stop, obstacle ahead",
        "caution": "Caution, obstacle ahead",
    },
    "north_west": {
        "stop":    "Stop, obstacle on your left",
        "caution": "Caution, obstacle on your left",
    },
    "north_east": {
        "stop":    "Stop, obstacle on your right",
        "caution": "Caution, obstacle on your right",
    },
}

ALERT_PRIORITY = {
    "stop":    2,
    "caution": 3,
}
```

**What it does:** Centralises every spoken phrase and its priority level in one place.

**Why it's written this way:**

- Keeping phrases in a dictionary (not hardcoded throughout the code) means **tweaking wording is a one-line change** — no hunting through code.
- The nested structure mirrors how the code looks things up: `ALERT_PHRASES[sensor][alert_level]` gives the phrase directly.
- Starting each phrase with the action word ("Stop", "Caution") means the user hears the most important word first.

### Block 3 — `check_alert()`

```python
def check_alert(distance):
    if distance <= STOP_DISTANCE:
        return "stop"
    elif distance <= CAUTION_DISTANCE:
        return "caution"
    else:
        return "clear"
```

**What it does:** Takes a raw distance reading and classifies it into one of three states.

**Why it's written this way:**

- Returns a **string** rather than a number so the rest of the code reads like English: `if alert_level == "stop"`.
- Uses `elif` so the checks are evaluated in order — anything below 50cm is "stop" and never gets re-checked against the 100cm threshold.

### Block 4 — `setup_gpio()`

```python
def setup_gpio():
    GPIO.setmode(GPIO.BCM)
    for sensor in SENSOR_PINS.values():
        GPIO.setup(sensor["trig"], GPIO.OUT)
        GPIO.setup(sensor["echo"], GPIO.IN)
```

**What it does:** Prepares the Pi's pins so they're ready to send pulses and read echoes.

**Why it's written this way:**

- `GPIO.BCM` uses the Broadcom pin numbering (the numbers printed on the board) rather than physical pin positions — it's the standard convention and easier to match up with wiring diagrams.
- The loop sets up all three sensors in one go instead of repeating the setup code three times.

### Block 5 — `get_distance()`

```python
def get_distance(sensor_name):
    pins = SENSOR_PINS[sensor_name]
    trig = pins["trig"]
    echo = pins["echo"]

    GPIO.output(trig, True)
    time.sleep(0.00001)
    GPIO.output(trig, False)

    while GPIO.input(echo) == 0:
        pulse_start = time.time()
    while GPIO.input(echo) == 1:
        pulse_end = time.time()

    echo_time = pulse_end - pulse_start
    distance = (echo_time * 34300) / 2

    return round(distance, 1)
```

**What it does:** Sends an ultrasonic pulse, measures how long the echo takes to return, and converts that into a distance in centimetres.

**Why it's written this way:**

- `time.sleep(0.00001)` is a 10-microsecond pulse — the HC-SR04's datasheet specifies this exact duration.
- The two `while` loops capture the start and end of the echo pulse — one waits for the echo pin to go HIGH, the other waits for it to go LOW.
- `34300` is the speed of sound in cm/s. We divide by 2 because the pulse travels there **and** back.
- `round(distance, 1)` keeps the output to one decimal place — more precision than that is noise.

**⚠ Known issue (for Pi-side hardening later):** If an echo never arrives (extreme proximity or sensor misfire), the `while` loops could hang forever. A timeout safeguard will be needed when running on real hardware.

### Block 6 — Main loop

```python
if __name__ == "__main__":
    setup_gpio()
    start_speech_thread()
    try:
        while True:
            for sensor_name in SENSOR_PINS:
                dist = get_distance(sensor_name)
                alert_level = check_alert(dist)
                if alert_level != "clear":
                    phrase = ALERT_PHRASES[sensor_name][alert_level]
                    priority = ALERT_PRIORITY[alert_level]
                    speak(priority, phrase)
                print(f"{sensor_name}: {dist} cm ({alert_level})")
            time.sleep(0.5)
    except KeyboardInterrupt:
        cleanup()
```

**What it does:** The full pipeline — set up sensors, start the speech thread, loop forever reading each sensor and speaking alerts when appropriate.

**Why it's written this way:**

- `try` / `except KeyboardInterrupt` lets the user press Ctrl+C to exit cleanly. Without it, the GPIO pins would stay in a weird state and could damage the Pi.
- `time.sleep(0.5)` spaces the readings so the ultrasonic pulses don't interfere with each other and the CPU isn't hammered.
- The `print()` is for debugging visibility — can be removed later.
- **Three sensors read sequentially, not in parallel** — this is fine for v1 but could be parallelised with threads later if scan rate matters.

---

# Task 11 — Object & Scene Detection with AI

## `vision.py` — MobileNet SSD inference pipeline

### Block 1 — Imports and graceful AI availability check

```python
import cv2
import numpy as np
import time
from speech import speak

try:
    from tflite_runtime.interpreter import Interpreter
    AI_AVAILABLE = True
except ImportError:
    AI_AVAILABLE = False
    print("Warning: tflite_runtime not available - AI detection disabled (expected on Windows)")
```

**What it does:** Imports the libraries and **attempts** to import the Pi-only AI library without crashing if it's missing.

**Why it's written this way — graceful degradation:**

- `tflite_runtime` only installs on the Pi. On Windows, the import would normally crash the whole file.
- `try`/`except ImportError` lets the code attempt the import and handle failure gracefully.
- The `AI_AVAILABLE` flag is checked throughout the rest of the file — any AI-dependent code is wrapped in `if AI_AVAILABLE:` so it silently skips on Windows.
- The code doesn't check the OS directly — it checks whether the import worked. This is more robust because it handles any environment where the library is missing, not just Windows.

### Block 2 — Preprocessing

```python
MODEL_INPUT_SIZE = 300

def preprocess_frame(frame):
    resized = cv2.resize(frame, (MODEL_INPUT_SIZE, MODEL_INPUT_SIZE))
    rgb = cv2.cvtColor(resized, cv2.COLOR_BGR2RGB)
    normalised = rgb / 255.0
    batched = np.expand_dims(normalised, axis=0).astype(np.float32)
    return batched
```

**What it does:** Takes a raw camera frame and transforms it into exactly what the model expects.

**Why each step:**

1. **Resize to 300×300** — MobileNet SSD was trained on 300×300 inputs. Larger or smaller breaks the model.
2. **Convert BGR → RGB** — OpenCV uses BGR by default, but the model was trained on RGB. Wrong colour order = wildly wrong predictions.
3. **Normalise 0-255 → 0-1** — Neural networks perform better on small, consistent number ranges. Division by 255 achieves this.
4. **Add batch dimension** — The model expects a "batch" of images even if the batch is just one image. `np.expand_dims` wraps the (300, 300, 3) array into (1, 300, 300, 3).

### Block 3 — Model loading

```python
MODEL_PATH = "models/mobilenet_ssd.tflite"

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
```

**What it does:** Loads the `.tflite` model file once at program startup and gets the input/output specifications ready for inference.

**Why it's written this way:**

- `interpreter`, `input_details`, and `output_details` are module-level globals because they're created once and used many times.
- `global` is needed inside the function because Python would otherwise create new local variables instead of modifying the module-level ones.
- The `AI_AVAILABLE` guard means this function is safe to call on Windows — it just does nothing.
- Loading is slow (~seconds), so it's separated from inference which runs per-frame.

### Block 4 — Running inference

```python
def run_inference(preprocessed_frame):
    if not AI_AVAILABLE or interpreter is None:
        return []

    interpreter.set_tensor(input_details[0]['index'], preprocessed_frame)
    interpreter.invoke()

    boxes = interpreter.get_tensor(output_details[0]['index'])[0]
    classes = interpreter.get_tensor(output_details[1]['index'])[0]
    scores = interpreter.get_tensor(output_details[2]['index'])[0]

    return boxes, classes, scores
```

**What it does:** Feeds a preprocessed frame into the model, runs it, and pulls out three parallel arrays of results.

**Why it's written this way:**

- **Guard clause** at the top returns early if AI isn't available — prevents crashes on Windows.
- `set_tensor` + `invoke` + `get_tensor` is the standard TFLite inference pattern.
- `[0]` at the end of each `get_tensor` call strips the batch dimension — we only fed one image so we only want one set of results.
- The three returned arrays are **parallel** — `boxes[i]`, `classes[i]`, and `scores[i]` all describe the same detected object.

### Block 5 — Filtering detections

```python
CONFIDENCE_THRESHOLD = 0.5

RELEVANT_CLASSES = {
    0:  "person",
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
```

**What it does:** Takes the raw model output and keeps only the detections that are (a) confident enough and (b) relevant to indoor navigation.

**Why each decision:**

- **Confidence threshold of 0.5** — below this, the model is basically guessing. False positives would train the user to ignore alerts.
- **COCO class IDs** — MobileNet SSD was trained on the COCO dataset. The numbers (0, 56, 57…) are fixed by the dataset and can't be changed.
- **Relevance filtering** — the model can detect ~80 classes, but most (kite, broccoli, surfboard) aren't navigation hazards indoors.
- **Returns dictionaries, not parallel arrays** — bundles each detection's info together under named keys (`class_name`, `confidence`, `box`), which is more readable and less error-prone than juggling `classes[i]`, `scores[i]`, and `boxes[i]` everywhere.
- **`continue`** jumps to the next iteration of the loop when a filter fails — cleaner than deeply nested `if` blocks.

### Block 6 — Zone detection

```python
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
```

**What it does:** Decides which zone (left / ahead / right) an object is in, based on its bounding box position in the image.

**Why it's written this way:**

- Bounding box coordinates are **normalised** (0 to 1), where 0 is the far left of the image and 1 is the far right.
- We compute the **horizontal centre** of the box — `(xmin + xmax) / 2` — and classify by which third of the image it falls in.
- **Tuple unpacking** (`ymin, xmin, ymax, xmax = box`) extracts all four coords in one line, even though only two are used. Makes the structure of `box` self-documenting.
- Vertical coordinates (`ymin`, `ymax`) are ignored because left/ahead/right is a purely horizontal question.

### Block 7 — Processing detections (with rate limiting)

```python
AI_ALERT_PRIORITY = 2
ALERT_COOLDOWN = 3
last_alert_times = {}

def process_detections(detections):
    current_time = time.time()
    for detection in detections:
        zone = get_zone(detection["box"])
        if zone != "ahead":
            continue
        class_name = detection["class_name"]
        if class_name in last_alert_times:
            if current_time - last_alert_times[class_name] < ALERT_COOLDOWN:
                continue
        phrase = f"{class_name} ahead"
        speak(AI_ALERT_PRIORITY, phrase)
        last_alert_times[class_name] = current_time
```

**What it does:** The final orchestration — takes filtered detections, decides which deserve a voice alert, and respects a 3-second cooldown per class.

**Why each design decision:**

- **Zone filter (`if zone != "ahead"`)** — AI alerts only fire for objects directly ahead, because the ultrasonic sensors already handle left/right zones. This avoids duplicate information.
- **Class-keyed timestamp dictionary** — `last_alert_times["chair"] = 1729612345.2` lets us check "when did I last announce a chair?" in constant time. Separate tracking per class means you can still hear "person ahead" shortly after "chair ahead".
- **Cooldown of 3 seconds** — short enough that the user isn't left unaware if an object persists, long enough to prevent spam.
- **Timestamp only updated when an alert actually fires** — if we updated it on every detection, the cooldown would never expire.
- **Priority 2** — same as ultrasonic "stop" alerts. A person directly ahead is as urgent as a close obstacle.
- **f-string** for the phrase means the class name gets substituted directly: `f"{class_name} ahead"` becomes `"chair ahead"`.

---

# Task 12 — Stair Detection

## `stairs.py` — Hough-line-based stair detection

### Block 1 — Imports

```python
import cv2
import numpy as np
import time
from speech import speak
```

**What it does:** Brings in OpenCV, numpy, timing, and the speech function.

**Why no `try`/`except` this time:** Unlike `vision.py`, there's no Pi-only library here. Hough line detection is pure OpenCV, which installs identically on Windows and the Pi. One of the hidden wins of going with classical computer vision instead of a second AI model.

### Block 2 — Detection thresholds

```python
MIN_LINES_FOR_STAIRS = 3
HORIZONTAL_TOLERANCE = 10
EDGE_DETECTION_LOW = 50
EDGE_DETECTION_HIGH = 150

STAIR_ALERT_PRIORITY = 1
```

**What each constant does:**

- **`MIN_LINES_FOR_STAIRS = 3`** — stairs have multiple parallel step edges. One or two horizontal lines could be anything (a table edge, a windowsill); three or more is more stair-like.
- **`HORIZONTAL_TOLERANCE = 10`** — real stairs in a camera image rarely look **perfectly** horizontal because the camera tilts slightly. ±10° of wobble accommodates this.
- **`EDGE_DETECTION_LOW` / `HIGH`** — the Canny algorithm's two thresholds. Pixels below LOW are never edges; pixels above HIGH always are; in-between pixels are edges only if connected to a strong edge. 50/150 is a standard starting point.
- **`STAIR_ALERT_PRIORITY = 1`** — the highest urgency, reserved for fall hazards. Decided all the way back in Task 1.

**Why they're at the top of the file:** All four thresholds are *tuning knobs*. Based on the test-image results (which showed heavy false positives), these values will definitely be adjusted — having them all in one visible location makes tuning painless.

### Block 3 — `detect_stairs()`

```python
def detect_stairs(frame):
    grey = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
    edges = cv2.Canny(grey, EDGE_DETECTION_LOW, EDGE_DETECTION_HIGH)
    lines = cv2.HoughLinesP(
        edges,
        rho=1,
        theta=np.pi / 180,
        threshold=80,
        minLineLength=50,
        maxLineGap=10
    )

    if lines is None:
        return False

    horizontal_count = 0
    for line in lines:
        x1, y1, x2, y2 = line[0]
        angle = np.degrees(np.arctan2(y2 - y1, x2 - x1))
        if abs(angle) < HORIZONTAL_TOLERANCE or abs(abs(angle) - 180) < HORIZONTAL_TOLERANCE:
            horizontal_count += 1

    return horizontal_count >= MIN_LINES_FOR_STAIRS
```

**What each step does:**

1. **Greyscale conversion** — strips colour because edge detection only cares about brightness changes. Reduces the data to process by ~3×.
2. **Canny edge detection** — finds pixels where brightness changes sharply (the edges of steps, furniture, walls, etc.).
3. **Probabilistic Hough Transform** — samples random points in the edges and finds straight line segments. Returns endpoints `(x1, y1, x2, y2)` which we can calculate angles from.
4. **`if lines is None:` guard** — when no lines are found, HoughLinesP returns `None`, not an empty list. Without this, iterating would crash.
5. **Angle calculation** — `arctan2(Δy, Δx)` gives the angle of the line; `np.degrees` converts to degrees. A horizontal line has an angle near 0° or near ±180°.
6. **Return boolean** — just yes/no. The decision of *what to do about it* lives in `process_stair_detection`.

**Why HoughLinesP (probabilistic) over HoughLines:**

- **Faster** — samples points instead of checking every pixel.
- **Returns endpoints** — makes angle calculation possible.
- **Pi-friendly** — the non-P version is too slow for real-time processing on limited hardware.

**Why the double angle check** (`abs(angle) < 10 or abs(abs(angle) - 180) < 10`): a line drawn left-to-right has angle 0°, but the same line drawn right-to-left has angle 180° or -180°. Both should count as horizontal.

### Block 4 — `process_stair_detection()`

```python
STAIR_ALERT_COOLDOWN = 3
last_stair_alert_time = 0

def process_stair_detection(frame):
    global last_stair_alert_time
    current_time = time.time()

    if not detect_stairs(frame):
        return

    if current_time - last_stair_alert_time < STAIR_ALERT_COOLDOWN:
        return

    speak(STAIR_ALERT_PRIORITY, "Stairs ahead")
    last_stair_alert_time = current_time
```

**What it does:** Runs stair detection, and if stairs are found and enough time has passed since the last alert, speaks "Stairs ahead" at priority 1.

**Why each design decision:**

- **Single timestamp variable, not a dictionary** — unlike `vision.py` where multiple classes needed tracking, there's only one type of stair alert, so a single scalar suffices.
- **`global` keyword** — needed because the function modifies the module-level `last_stair_alert_time`.
- **Detection runs BEFORE the cooldown check** — this is a deliberate ordering. If we checked the cooldown first, we'd skip detection during the cooldown period, meaning we'd never *know* whether stairs were there. Running detection first means we always know what's in the frame; the cooldown just decides whether to *announce* it.
- **Two guard clauses** instead of nested `if` blocks — flatter and easier to read.
- **Timestamp updated only when an alert fires** — same pattern as `vision.py`.

### Block 5 — The test block

```python
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
```

**What it does:** Loads every image in `test_images/`, runs `detect_stairs()` on each, and prints the verdict.

**Why it's written this way:**

- **`import os` inside the test block** — `os` is only needed for testing, not for the real detection pipeline. Keeping it local to `__main__` avoids polluting the main module.
- **`cv2.imread`** returns a numpy array in the same format as a live camera frame. The detection function has no idea where the frame came from and doesn't care.
- **`if frame is None:` guard** — `cv2.imread` returns `None` for unreadable files (wrong format, corrupt, etc.) instead of crashing. This guard prevents the whole test run from dying on one bad file.
- **No `speak()` calls** — this is diagnostic, not integration. We just want to see the detector's yes/no decisions in the console, not hear them announced.
- **`{filename:30s}` padding** — pads filenames to 30 chars so the verdicts line up in a neat column.

**What the first test revealed:** High recall (100% — caught all stair images) but low precision (flagged many non-stair images). This is the data that justifies adding the clustering + spacing filters as the next step.

---

### Task 12 — Block 4: The Clustering Filter Experiment (Reverted)

**What was attempted:** Two additional checks were added to `detect_stairs()` to reduce false positives — a **span test** (horizontal lines must span less than 40% of image height) and a **position test** (bottommost line must sit in the lower half of the image).

**Why it was reverted:** Diagnostic instrumentation revealed two problems:
- Hough returned 60–500+ horizontal "lines" per image due to edge fragmentation, not the few dozen visible step edges.
- Real stair images consistently produced span ratios of 0.82–1.00 because the visible step edges genuinely stretch across most of the image height (top step is far/high, bottom step is close/low).
- Span and position values for true stairs were indistinguishable from those of false positives like blinds, bookshelves, and hallways.

**Why it's worth documenting anyway:** The dead-end produced two genuine insights — (1) the discriminating signal between stairs and confounders lies in the *regions between* horizontal lines, not in the geometry of the lines themselves; (2) the geometric-filter approach has a fundamental ceiling that further parameter tuning cannot break through. These insights now anchor a planned research paper on stair-trained lightweight models.

**Code state:** `detect_stairs()` was rolled back to the pre-cluster v1 (3+ horizontal lines = stairs). Constants `CLUSTER_SPAN_MAX` and `CLUSTER_POSITION_MIN` were removed. A docstring-style comment block above the function documents the v1 trade-offs and the abandoned experiment.

---

*Document maintained as part of the Indoor Navigation for Visually Impaired capstone project. Updated as new code is written.*
