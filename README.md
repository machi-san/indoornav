# Indoor Navigation System for Visually Impaired Users

A real-time edge AI system that combines object detection, classical computer vision, and ultrasonic sensor fusion to deliver priority-based audio alerts for indoor navigation.

> **Status:** Active capstone project — currently in development (Phase 3 of 5).

---

## 📖 Project Overview

Designed for a visually impaired user wearing a chest-mounted Raspberry Pi with a camera and ultrasonic sensors. The system processes the environment in real time and delivers spoken alerts prioritised by urgency:

| Priority | Alert Type | Example |
|----------|-----------|---------|
| 1 | Fall hazards | "Stairs ahead" |
| 2 | Immediate obstacles | Ultrasonic stop-distance trigger |
| 3 | AI-detected objects | "Person ahead", "Chair ahead" |
| 4 | Caution warnings | Ultrasonic caution-distance trigger |

The lower the number, the more urgent the alert — and higher-priority alerts interrupt lower-priority ones in the speech queue.

---

## 🛠 Tech Stack

- **Python 3** — core implementation
- **TensorFlow Lite** — MobileNet SSD object detection optimised for edge hardware
- **OpenCV** — image preprocessing and Hough Transform for stair detection
- **pyttsx3** — offline text-to-speech for audio alerts
- **Raspberry Pi 4** — target deployment platform (camera + ultrasonic sensors via GPIO)

---

## 📐 System Architecture

The codebase is split into modular files, each handling one concern:

| File | Responsibility |
|------|---------------|
| `speech.py` | Priority queue + threaded audio output |
| `ultrasonic.py` | Distance sensor reading and threshold-based alerts |
| `vision.py` | AI inference pipeline (preprocess → detect → filter → announce) |
| `stairs.py` | Classical CV stair detection (Hough Transform + clustering filters) |

---

## 📊 Current Progress

- ✅ **Task 9** — Ultrasonic obstacle detection with caution/stop distance thresholds
- ✅ **Task 10** — Audio alert system with priority queue and threading
- ✅ **Task 11** — AI object detection pipeline with rate-limited alerts
- 🟡 **Task 12** — Stair detection via Hough Transform *(in progress — currently tuning clustering filters)*
- ⏳ **Task 13+** — Hardware integration, end-to-end testing, enclosure design *(pending Raspberry Pi delivery)*

---

## 📚 Documentation

Two living documents track the engineering decisions and learning behind this project:

- **[CONCEPTS.md](CONCEPTS.md)** — running log of programming and engineering concepts encountered during the build (priority queues, normalisation, recall vs precision, robust statistics, and more)
- **[CODE_WALKTHROUGH.md](CODE_WALKTHROUGH.md)** — block-level explanation of every code module, organised by task, with the reasoning behind each design decision

These aren't just code comments — they capture the *why* behind every trade-off, including the deliberate scope decisions (e.g. why classical CV was chosen over a stair-detection model for v1, why time-based rate limiting was preferred over movement detection).

---

## 🎯 Design Decisions Worth Noting

A few engineering trade-offs documented for transparency:

- **Standard camera + ultrasonic over depth camera** — chosen for cost, weight, and Pi-compatible processing budget. Depth-based fusion documented as a v2 enhancement.
- **Hough Transform over a stair-detection AI model** — pre-trained models for indoor stairs are scarce and inconsistent. Hough is lightweight, runs comfortably on the Pi, and provides a clear improvement path (clustering → spacing → AI hybrid).
- **Time-based rate limiting** — simpler than movement-based suppression and good enough for v1. Movement-based logic noted as a v2 enhancement.
- **Layered detection** — ultrasonic catches "*something* is there" regardless of object type, AI identifies "*what* it is" when in the ahead zone. Each system covers the other's blind spots.

---

## ⚠ Academic Notice

This is an active capstone project submitted for academic credit at **Amity University Dubai** (B.Tech Mechatronics Engineering, expected graduation June 2026).

**Please do not copy this code or documentation for your own academic submissions.** Suspected academic misconduct will be reported to the relevant institutions.

For learning purposes, you're welcome to read, reference, and discuss the approaches used. Issues and discussion are open if you want to chat about any of the design decisions.

---

## 👤 Author

**Wahua Omumachi** — [github.com/machi-san](https://github.com/machi-san)

Mechatronics Engineering student, Amity University Dubai.
