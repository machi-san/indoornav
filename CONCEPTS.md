# 📚 Concepts Discovered — Indoor Navigation Project

A running log of programming, engineering, and computer-vision concepts encountered during the build of this project. Each concept was worked through collaboratively — most of them surfaced from reasoning about real design decisions rather than being taught top-down.

\---

## 🧵 Concurrency \& program flow

* **Priority queues** — data structures that auto-sort items by urgency, not insertion order. Used in `speech.py` so that fall hazards are spoken before lower-priority alerts regardless of when they were added.
* **Threading \& daemon threads** — running background work (like the speech engine) without blocking the main program. `daemon=True` means the thread won't prevent the program from exiting.
* **Scope \& the `global` keyword** — variables defined inside a function are local by default; `global` tells Python to reach outside and modify the module-level variable instead.
* **Producer/consumer pattern** — one thread (producer) generates data at its own pace; one or more threads (consumers) sample that data at their own paces. Decouples timing between fast producers and slow consumers. 
* **Snapshot reference pattern** — copying a shared variable into a local variable (frame = latest_frame) before processing it. Ensures the function operates on a single consistent value even if the shared variable gets updated mid-processing.
* **Shutdown flag pattern** — a shared boolean (shutdown_flag) that all worker threads check each iteration. The main thread sets it on Ctrl+C, and workers exit their loops at the next check. Simple, correct, but causes up to one-loop-iteration of shutdown lag.

\---

## 🛡 Robust programming

* **Graceful degradation** — wrapping imports in `try`/`except` so code runs across platforms without crashing when a platform-specific library (e.g. `tflite\\\_runtime`) isn't installed.
* **Guard clauses** — early `return` statements that exit a function quickly when conditions aren't met. Keeps the main logic un-indented and readable.
* **Zero-indexing** — arrays start at index `0`, so the Nth item lives at index `N-1`.
* **Mocking** - feeding a function with hand-crafted input that simulates what real input would look like, so you can verify the function's logic in isolation.
* **Global Interpreter Lock(GIL)** - affects how threads work. In short: only one Python thread can execute Python code at a time, even if you have 4 threads on a 4-core CPU
* **Race condition** - happens if the camera thread is mid-write when a reader grabs the frame? You could get a half-old, half-new frame which implies corrupted data.
* **Threading lock** - a mechanism that says "while I'm writing, no one can read; while someone's reading, no one can write." It serialises access to the shared resource.
* **try/finally for resource management** — guarantees cleanup code runs even if the main code crashes. Critical for hardware resources (camera, GPIO), file handles, network connections. Without it, a crash leaves resources locked until reboot.
* **Conditional imports for cross-platform code** — importing platform-specific modules (like RPi.GPIO) only inside conditional blocks (if not USE_MOCK_CAMERA) prevents crashes on platforms where the module doesn't exist.
* **Mock objects for development without hardware** — fake implementations (get_mock_frame() returning a black frame) let you test integration logic without the real hardware being present. Mocks get swapped for real implementations later.

\---

## 📦 Data organisation

* **Arrays vs dictionaries** — arrays store values by position; dictionaries store values by name. Dictionaries bundle related info together (class, confidence, box) instead of juggling parallel arrays.
* **Tuple unpacking** — extracting multiple values from a collection in one line: `ymin, xmin, ymax, xmax = box`.
* **Module-level constants** — thresholds and tuning values live at the top of a file, not buried in functions, so they're easy to adjust later.
* **Interleaved Output** - a classic threading artefact. Just a cosmetic side effect of multiple threads writing to stdout without coordination.
* **Dictionary-based per-class configuration** — using a dictionary like CLASS_PRIORITIES_AHEAD = {"person": 3} with .get(class_name, default) is cleaner than if/elif chains for per-class behaviour. Adding new classes is one line, no logic changes needed.
* **dict.get(key, default)** — returns the value if key exists, otherwise returns the default. Avoids try/except wrapping for "key might not exist" lookups.

\---

## 🖼 Computer vision fundamentals

* **Preprocessing pipeline** — resize → colour-convert → normalise → batch-wrap. AI models expect a specific, consistent input shape.
* **Normalisation** — squashing pixel values from 0–255 into 0–1 by dividing by 255. Neural networks perform better on small, consistent number ranges.
* **Bounding boxes** — four coordinates `\\\[ymin, xmin, ymax, xmax]` describing a rectangle around a detected object. Used here for left/ahead/right zone decisions.
* **Greyscale for edge detection** — stripping colour because edge detection only cares about brightness changes. 3× less data to process on the Pi.
* **Canny edge detection** — detects sharp brightness transitions in an image. Uses two thresholds (low and high) to decide what counts as an edge.
* **Hough Transform (probabilistic version)** — finds straight line segments in edge data. The "P" version is faster and returns endpoints, which lets us calculate angles.

\---

## 🤖 AI inference

* **Pre-trained models** — downloading and using someone else's trained neural network instead of training one from scratch.
* **MobileNet SSD** — a small, fast, Single Shot Detector. *MobileNet* = optimised for edge devices; *SSD* = detects and classifies in a single pass.
* **`.tflite` format** — TensorFlow Lite, optimised for ARM processors and low memory. Perfect for the Pi.
* **Three outputs per inference** — class, bounding box, confidence. Returned as parallel arrays where index N in each describes the same object.
* **Confidence thresholds** — filtering out low-confidence "wild guesses" to avoid false positives.
* **Interpreter pattern** — load model once, allocate memory once, then run inference per frame.

\---

## 🎯 Design \& systems thinking

* **Layered detection** — multiple independent systems (ultrasonic for "something is there", AI for "what it is") covering each other's blind spots.
* **Zone-based alerting** — the AI only announces in the "ahead" zone because ultrasonic already handles the sides. Avoids duplicate information.
* **Rate limiting (cooldown-based)** — suppressing repeat alerts within N seconds using a timestamp lookup.
* **Priority inversion** — lower priority number = more urgent. Counterintuitive but common in alert systems.
* **Separation of detection from announcement** — `detect\\\_stairs()` returns a boolean; `process\\\_stair\\\_detection()` decides whether to speak. Same pattern in `vision.py`.
* **Recall vs precision** — "did we catch all the stairs?" vs "of the things we flagged, how many really were stairs?" For a safety device, recall matters more.
* **Multi-criteria / cascade filtering** — stacking filters (3+ lines AND clustered AND evenly spaced) for compounding precision gains without sacrificing recall too badly.
* **Incremental change, isolated measurement** — change one thing at a time, measure its effect, then change the next thing. Same principle as Git commits.
* **Scope decisions (v1 vs v2)** — honest calls about what's achievable now vs documented as future work (depth camera, AI stair detection, movement-based rate limiting, sensor fusion).
* **Robust Statistics** - Picking measurements that don't get thrown off by outliers
* **Premature Optimisation Concern** - looked at "more data structures" and thought "more cost." That's healthy paranoia for embedded systems where memory and CPU are limited.
* **Asymmetric error costs in safety systems** — for an assistive device, false negatives (missed obstacle) cost more than false positives (false alarm). Drives priority on recall over precision in detection systems.
* **Race conditions and atomic operations** — when multiple threads share variables, simultaneous reads/writes can produce corrupted intermediate states. CPython's GIL guarantees single-variable assignments are atomic, which makes simple shared booleans/references safe without locks.
* **Module ownership of state** — each module owns the state it cares about. vision.py owns the AI model interpreter, speech.py owns the queue, main.py owns thread orchestration. Modules don't reach into each other's state. Makes refactoring local rather than global.

\---

## 🛠 Engineering workflow

* **Commit early, commit often** — committing before risky changes so buggy versions are preserved in Git history for debugging narratives.
* **Commit messages as documentation** — being honest about known issues in commit messages (e.g. *"pyttsx3 Windows bug — only first alert speaks"*). Future-you will thank past-you.
* **PyCharm run configurations** — PyCharm sometimes "runs an old version" because run configs are saved per-file. Right-click inside the target file and choose *Run 'filename'* to force a fresh config.

\---

### 🧪 Empirical engineering & dead-ends

- **Hough fragmentation** — Probabilistic Hough Transform returns *line segments*, not visible lines. A single visible edge in an image often gets broken into dozens or hundreds of short segments. Counting "lines found" can wildly overstate the visible structure.

- **The discriminator might not be where you think it is** — When attempting to filter stairs from confounders (bookshelves, blinds, hallways), the geometric properties of horizontal lines (span, position) overlapped completely between true positives and false positives. The real distinguishing signal lay in the regions *between* the lines (smooth risers vs. cluttered book spines), not in the lines themselves.

- **Dead-ends as data** — A filter that fails to discriminate is informative. The clustering-filter experiment proved empirically that simple geometric rules cannot solve stair detection, which justifies escalating to a different approach (purpose-trained model) rather than tuning thresholds indefinitely.

- **Knowing when to stop** — Persistence and excellence are different things. Choosing to ship a v1 with documented limitations and pivot to a research-paper framing produces better engineering outcomes than dogged threshold-tuning. This is a real engineering skill, not a concession.

- **WIP commits as honest documentation** — committing buggy or incomplete code with a (WIP) marker preserves the debugging journey. Future you (or reviewers) can see how you got from broken to working in distinct steps.

- **Incremental change with isolated measurement** — change one thing, measure the effect, then change the next. Same principle as good Git commits. Prevents "I changed five things and now it's broken, but which change caused it?"

- **Diagnostic instrumentation** — temporary print statements that expose intermediate values during debugging. Get added to investigate something specific, get removed once the issue is understood.
\---

*Document maintained as part of the Indoor Navigation for Visually Impaired capstone project. Updated as new concepts are encountered.*

