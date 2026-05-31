#pyttsx3 The text-to-speech engine — converts text to spoken audio
#queue Python's built-in priority queue — manages alert order
#threading Allows the speech engine to run in the background without blocking the sensors

import pyttsx3
import queue
import threading
import subprocess
import platform

# Windows PowerShell speech settings (development-only stopgap)
# To be removed when hardware arrives and pyttsx3 takes over
# Speech backend selection.
# True  = use PowerShell subprocess (Windows development stopgap)
# False = use pyttsx3 directly (Pi deployment, Linux)
# Flip to False when deploying to the Raspberry Pi.
# Speech backend selection (auto-detected from host OS).
# Windows: PowerShell subprocess via System.Speech.Synthesis (dev workaround)
# Linux:   pyttsx3 engine directly (Pi deployment path)
USE_POWERSHELL_TTS = platform.system() == "Windows"
PS_RATE = -1          # Range -10 to +10 (0 = default speaking rate)
PS_VOLUME = 100       # Range 0 to 100
SPEECH_RATE = 160          # Words per minute - slower than default for clarity
SPEECH_VOLUME = 1.0        # Maximum volume for outdoor/noisy environments

# Maximum number of alerts allowed in the speech queue at once.
# Bounded queue prevents pile-up during sustained activity (e.g., cluttered indoor spaces).
# When full, the lowest-priority item is dropped to make room for new alerts —
# this preserves critical alerts (stairs, immediate obstacles) over contextual ones.
MAX_QUEUE_SIZE = 5

# Initialise the text-to-speech engine
engine = pyttsx3.init()
engine.setProperty('rate', SPEECH_RATE)    # words per minute (default ~200)
engine.setProperty('volume', SPEECH_VOLUME)  # 0.0 to 1.0 (max for outdoor/noisy use)

# Create the message queue
alert_queue = queue.PriorityQueue(maxsize=MAX_QUEUE_SIZE)

def speak(priority, message):
    """Queue an alert for speech. If the queue is full, the lowest-priority item
    is evicted to make room — preserving critical alerts over contextual ones."""
    try:
        alert_queue.put_nowait((priority, message))
    except queue.Full:
        # Queue is full. Inspect the heap directly to find the worst (highest-number)
        # priority item. If the new alert is better than the worst, evict and re-add.
        with alert_queue.mutex:
            heap = alert_queue.queue
            if not heap:
                return  # Edge case: somehow empty between check and lock
            # The heap is ordered with smallest priority at index 0.
            # Worst priority is the maximum across all items.
            worst_index = max(range(len(heap)), key=lambda i: heap[i][0])
            worst_priority = heap[worst_index][0]
            if priority < worst_priority:
                # New alert is more urgent than the worst pending one. Evict it.
                heap.pop(worst_index)
                # Restore heap invariant after removing a non-root element
                import heapq
                heapq.heapify(heap)
                # Now there's room. Add the new alert through the normal path
                # (re-lock the mutex is fine — same thread).
        # If we evicted, re-try the put. If we didn't (new alert was the worst), drop it silently.
        if priority < worst_priority:
            try:
                alert_queue.put_nowait((priority, message))
            except queue.Full:
                pass  # Shouldn't happen but degrade safely

def process_queue():
    while True:
        priority, message = alert_queue.get()
        print(f"Speaking (priority {priority}): {message}")
        if USE_POWERSHELL_TTS:
            # Windows development stopgap: spawn a PowerShell subprocess
            # that uses System.Speech.Synthesis.SpeechSynthesizer.
            subprocess.run([
                "powershell", "-Command",
                f"Add-Type -AssemblyName System.Speech; "
                f"$s = New-Object System.Speech.Synthesis.SpeechSynthesizer; "
                f"$s.Rate = {PS_RATE}; "
                f"$s.Volume = {PS_VOLUME}; "
                f"$s.Speak('{message}')"
            ])
        else:
            # Pi deployment: use the pyttsx3 engine configured at module load.
            engine.say(message)
            engine.runAndWait()

def start_speech_thread():
    thread = threading.Thread(target=process_queue, daemon=True)
    thread.start()
if __name__ == "__main__":
    start_speech_thread()
    speak(2, "Obstacle ahead")
    speak(1, "Careful, stairs ahead")
    speak(3, "Obstacle, left side")

    import time
    time.sleep(10)

