#pyttsx3 The text-to-speech engine — converts text to spoken audio
#queue Python's built-in priority queue — manages alert order
#threading Allows the speech engine to run in the background without blocking the sensors

import pyttsx3
import queue
import threading

# Initialise the text-to-speech engine
engine = pyttsx3.init()
engine.setProperty('rate', 150)    # Speed of speech
engine.setProperty('volume', 1.0)  # Full volume

# Create the message queue
alert_queue = queue.PriorityQueue()

def speak(priority, message):
    alert_queue.put((priority, message))

def process_queue():
    while True:
        priority, message = alert_queue.get()
        local_engine = pyttsx3.init()
        local_engine.setProperty('rate', 150)
        local_engine.setProperty('volume', 1.0)
        local_engine.say(message)
        local_engine.runAndWait()
        local_engine.stop()

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

