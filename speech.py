#pyttsx3 The text-to-speech engine — converts text to spoken audio
#queue Python's built-in priority queue — manages alert order
#threading Allows the speech engine to run in the background without blocking the sensors

import pyttsx3
import queue
import threading
import subprocess

# Windows PowerShell speech settings (development-only stopgap)
# To be removed when hardware arrives and pyttsx3 takes over
PS_RATE = -1          # Range -10 to +10 (0 = default speaking rate)
PS_VOLUME = 100       # Range 0 to 100
SPEECH_RATE = 160          # Words per minute - slower than default for clarity
SPEECH_VOLUME = 1.0        # Maximum volume for outdoor/noisy environments

# Initialise the text-to-speech engine
engine = pyttsx3.init()
engine.setProperty('rate', SPEECH_RATE)    # words per minute (default ~200)
engine.setProperty('volume', SPEECH_VOLUME)  # 0.0 to 1.0 (max for outdoor/noisy use)

# Create the message queue
alert_queue = queue.PriorityQueue()

def speak(priority, message):
    alert_queue.put((priority, message))

def process_queue():
    while True:
        priority, message = alert_queue.get()
        print(f"Speaking (priority {priority}): {message}")
        # NOTE: Windows-only PowerShell speech as a development workaround.
        # When hardware arrives, replace this with engine.say(message) +
        # engine.runAndWait() to use the pyttsx3 settings configured above.
        subprocess.run([
            "powershell", "-Command",
            f"Add-Type -AssemblyName System.Speech; "
            f"$s = New-Object System.Speech.Synthesis.SpeechSynthesizer; "
            f"$s.Rate = {PS_RATE}; "
            f"$s.Volume = {PS_VOLUME}; "
            f"$s.Speak('{message}')"
        ])

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

