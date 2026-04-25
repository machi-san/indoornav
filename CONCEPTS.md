# 📚 Concepts Discovered — Indoor Navigation Project

A running log of programming, engineering, and computer-vision concepts encountered during the build of this project. Each concept was worked through collaboratively — most of them surfaced from reasoning about real design decisions rather than being taught top-down.

\---

## 🧵 Concurrency \& program flow

* **Priority queues** — data structures that auto-sort items by urgency, not insertion order. Used in `speech.py` so that fall hazards are spoken before lower-priority alerts regardless of when they were added.
* **Threading \& daemon threads** — running background work (like the speech engine) without blocking the main program. `daemon=True` means the thread won't prevent the program from exiting.
* **Scope \& the `global` keyword** — variables defined inside a function are local by default; `global` tells Python to reach outside and modify the module-level variable instead.

\---

## 🛡 Robust programming

* **Graceful degradation** — wrapping imports in `try`/`except` so code runs across platforms without crashing when a platform-specific library (e.g. `tflite\\\_runtime`) isn't installed.
* **Guard clauses** — early `return` statements that exit a function quickly when conditions aren't met. Keeps the main logic un-indented and readable.
* **Zero-indexing** — arrays start at index `0`, so the Nth item lives at index `N-1`.
* **Mocking** - feeding a function with hand-crafted input that simulates what real input would look like, so you can verify the function's logic in isolation.

\---

## 📦 Data organisation

* **Arrays vs dictionaries** — arrays store values by position; dictionaries store values by name. Dictionaries bundle related info together (class, confidence, box) instead of juggling parallel arrays.
* **Tuple unpacking** — extracting multiple values from a collection in one line: `ymin, xmin, ymax, xmax = box`.
* **Module-level constants** — thresholds and tuning values live at the top of a file, not buried in functions, so they're easy to adjust later.

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

\---

*Document maintained as part of the Indoor Navigation for Visually Impaired capstone project. Updated as new concepts are encountered.*

