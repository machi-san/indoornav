# V2 Enhancements

A consolidated log of features, refinements, and design ideas considered during v1 development but deliberately deferred. Each entry documents *what* was considered, *why* it didn't make v1, and *what* it would improve.

This file exists for three reasons:

- **Capstone report** — feeds the Future Work section
- **Research paper** — anchors the proposed direction discussion
- **Project memory** — preserves design reasoning that would otherwise evaporate

> Last updated: end of Phase 3 stair detection work.

---

## 🎥 Hardware

### Wide-FOV camera (~102°)
- **What**: Replace the standard ~66° Pi Camera Module v3 with the Wide variant.
- **Why deferred**: Hardware change mid-project would require re-budgeting and possibly retesting object detection accuracy on warped edge frames.
- **What it improves**: Allows true "left/right" zone semantics rather than "slight left/right." Side detections become genuinely peripheral rather than just-off-centre forward detections.
- **Trade-off**: Edge fisheye distortion may slightly reduce object detection accuracy at the periphery.

### Depth camera
- **What**: RGB-D, time-of-flight, or structured-light camera providing per-pixel distance data.
- **Why deferred**: Cost, weight, and processing budget all incompatible with v1 prototype constraints.
- **What it improves**: Unlocks genuine depth-based stair detection (a sudden floor drop = down-stairs) without needing AI or Hough heuristics. Also enables true sensor fusion.

### Downward-facing rangefinder (ultrasonic or laser)
- **What**: Additional sensor mounted to look directly downward.
- **Why deferred**: Extra hardware, additional GPIO, additional power draw — out of v1 budget.
- **What it improves**: Orthogonal signal for stair-edge detection. Catches "you're about to step off an edge" cases the camera-based approach struggles with. Particularly valuable for descending stairs where Hough is least reliable due to camera angle.

### Chest harness mounting
- **What**: Move from belt-clip to chest-mounted harness.
- **Why deferred**: Belt-clip chosen for v1 simplicity of build.
- **What it improves**: Camera angle no longer needs downward tilt. Better coverage for head-height obstacles (low-hanging signs, cabinet edges, branches). Worse for floor-level detail.

---

## 🤖 AI and Detection

### Stair-trained lightweight model
- **What**: Purpose-built model (likely MobileNet backbone, binary classifier) for indoor stair detection.
- **Why deferred**: No suitable pre-trained model available; training one requires a curated dataset that doesn't exist in the public domain.
- **What it improves**: Replaces the current Hough-based approach. Should dramatically reduce false positives on bookshelves, blinds, hallways, and striped surfaces.
- **See also**: `Stair_Detection_Research_Outline.docx` — the central thesis.

### Inter-line region texture analysis
- **What**: Classical CV refinement that analyses what sits *between* horizontal lines (smooth riser vs. cluttered book spines).
- **Why deferred**: Adds complexity rapidly approaching that of a small dedicated model. If we're going that far, training a model is the better investment.
- **What it improves**: Could bridge the gap between Hough v1 and a full trained model. Specifically targets the bookshelf/blind false positives.

### Ascending vs descending stair classification
- **What**: Distinguish "stairs going up" from "stairs going down" so alerts can be more specific.
- **Why deferred**: Likely needs depth data or a more capable model than Hough provides.
- **What it improves**: User gets directionally meaningful alerts. Descending stairs are the more dangerous case (fall risk) and warrant a different cue.

### Region-of-interest cropping
- **What**: Only analyse the lower 70% of frames for stair detection.
- **Why deferred**: Quick win not yet attempted. Worth trying as a quick v1.5 improvement before going full v2.
- **What it improves**: Eliminates ceiling-edge false positives without harming recall.

### Multi-stage cascade filtering
- **What**: Hough lines as a fast first pass, expensive AI inference only on stair-like frames.
- **Why deferred**: Requires the trained model from above to exist first.
- **What it improves**: Hybrid approach to balance speed and accuracy. Reduces inference cost compared to running an AI model on every frame.

---

## 🔊 Alert System

### Movement-based rate limiting
- **What**: Replace time-based cooldown with bounding-box-centre movement detection.
- **Why deferred**: Simpler time-based version chosen for v1 to ship faster.
- **What it improves**: Re-announces only when an object has *meaningfully moved* (e.g. 20% of frame width) rather than every 3 seconds. Reduces unnecessary chatter for stationary objects.

### Granular zone tracking for AI alerts
- **What**: Use `class_name + zone` as the rate-limit dictionary key instead of just `class_name`.
- **Why deferred**: Adds chatter risk if objects wobble between zones; v1 favours quietness.
- **What it improves**: A person moving from "ahead" to "left" within the cooldown would re-announce. Gives the user directional updates for moving objects.

### Distinct phrasing for ascending vs descending stairs
- **What**: "Stairs going up" vs "Stairs going down."
- **Why deferred**: Detection method (Hough) doesn't currently distinguish direction.
- **What it improves**: Critical safety cue. Descending stairs are the higher fall risk and the user's response should differ.

### Dynamic alert phrasing
- **What**: Adapt phrasing based on user feedback or training. E.g., user might prefer "obstacle" over specific class names in cluttered environments.
- **Why deferred**: Requires user testing data to inform the design.
- **What it improves**: Personalised alerting reduces cognitive load and user fatigue.

---

## 🔗 Sensor Fusion

### Cross-validation between camera and ultrasonic for stair detections
- **What**: Reduce false positives by requiring both signals to agree before firing a stair alert.
- **Why deferred**: Reframed Task 12 subtask, currently deferred to hardware integration phase.
- **What it improves**: Significant precision gain on the stair detector — addresses the core v1 limitation without changing the detection algorithm itself.

### Layered confidence scoring
- **What**: Alert fires with higher confidence (and therefore higher priority) when multiple sensors agree.
- **Why deferred**: v1 uses fixed priorities per source for simplicity.
- **What it improves**: Adapts urgency to actual situation rather than hardcoded source priority.

### True depth fusion
- **What**: Once a depth-capable sensor exists, fuse depth-per-pixel data with AI detections.
- **Why deferred**: Depends on depth camera hardware (see Hardware section).
- **What it improves**: Richer scene understanding. Distance-aware alerts ("Person 2 metres ahead"), ground discontinuity detection, occlusion reasoning.

---

## 📊 Evaluation and User Testing

### Expanded test set (50+ images)
- **What**: Cover more confounder categories — escalators, ramps, decorative tile, hospital corridors, transit stations.
- **Why deferred**: 18-image set was sufficient to identify v1 failure modes; expansion needed for proper precision/recall measurement.
- **What it improves**: Statistical confidence in detector performance. Required before any claims of "production readiness."

### Real user testing
- **What**: Test all alert phrases with an actual visually impaired user (Task 13 Subtask 4).
- **Why deferred**: Requires hardware integration first.
- **What it improves**: Validates whether "Person on your left" is interpreted correctly or causes overcorrection. Captures the subjective UX issues that internal testing cannot reveal.

### Quantitative metrics in production
- **What**: Log detection events, false positive reports, and alert response times.
- **Why deferred**: Requires deployed system and user opt-in for data collection.
- **What it improves**: Enables ongoing tuning. Also provides the cloud/data analytics angle that AI/IoT roles often look for.

---

## 🛠 System and Infrastructure

### Cloud logging of detection events
- **What**: Send event data to a cloud backend for analysis and remote diagnostics.
- **Why deferred**: v1 is fully edge-based by design.
- **What it improves**: Per-user tuning, fleet-wide analytics, faster bug triage. Ticks the IoT data-pipeline box for portfolio purposes.

### Configurable alert preferences per user
- **What**: User-adjustable speech rate, volume, phrasing style (concise vs. natural), zone announcement preferences.
- **Why deferred**: v1 has no user-facing configuration interface.
- **What it improves**: Accessibility itself — different users have different sensory and cognitive needs.

### Better stair detection error handling
- **What**: Graceful degradation when the camera momentarily loses focus or is blocked.
- **Why deferred**: Edge cases not yet observed in testing.
- **What it improves**: Robustness in real-world conditions (pocket lint, body brushing, motion blur).

---

## 🔑 Pattern Summary

The v2 enhancements cluster into three themes:

- **Hardware that v1 deliberately couldn't afford** — depth camera, wide camera, downward rangefinder
- **Engineering approaches that needed more time** — movement-based rate limiting, cascade filters, granular zone tracking
- **Research directions that are essentially papers** — stair-trained model, inter-line texture analysis, sensor fusion methodology

Each item has a clear *why we didn't do it now* and a clear *why it matters* — useful both for the capstone Future Work section and the research paper's proposed direction discussion.

---

*Living document — to be expanded as the project continues and new ideas surface.*
