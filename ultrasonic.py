import RPi.GPIO as GPIO
import time
import state
from speech import speak, start_speech_thread
# GPIO pin assignments for each sensor
SENSOR_PINS = {
    "north":      {"trig": 17, "echo": 27},
    "north_east": {"trig": 22, "echo": 23},
    "north_west": {"trig": 24, "echo": 25},
}
# Distance thresholds in centimetres
CAUTION_DISTANCE = 100  # Approaching warning
STOP_DISTANCE = 50      # Stop alert
# Alert phrases per sensor direction and range
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

# Priority mapping
ALERT_PRIORITY = {
    "stop":    2,
    "caution": 3,
}
# Rate limiting: minimum seconds between repeat alerts for the same (sensor, level) pair.
# Prevents the speech queue from filling faster than it can drain in cluttered environments.
ALERT_COOLDOWN = 3

# Tracks the time of the last alert for each (sensor, level) combination.
# Keys are tuples like ("north", "stop"); values are time.time() floats.
last_alert_times = {}
def check_alert(distance):
    if distance <= STOP_DISTANCE:     #<=50cm
        return "stop"
    elif distance <= CAUTION_DISTANCE:       #<=100cm
        return "caution"
    else:
        return "clear"
# tells the Pi to use the BCM pin numbering system (the numbers printed on the board)
def setup_gpio():
    GPIO.setmode(GPIO.BCM)
    for sensor in SENSOR_PINS.values():
        GPIO.setup(sensor["trig"], GPIO.OUT)
        GPIO.setup(sensor["echo"], GPIO.IN)

# Timeout for echo wait loops (seconds). 40ms corresponds to ~7m max distance,
# well beyond HC-SR04's reliable range (~4m). If echo doesn't respond within
# this window, the sensor is considered to have failed for this cycle.
ECHO_TIMEOUT = 0.04

def get_distance(sensor_name):
    """Read distance from the named sensor. Returns the distance in cm,
    or None if the sensor failed to produce a valid echo within ECHO_TIMEOUT."""
    pins = SENSOR_PINS[sensor_name]
    trig = pins["trig"]
    echo = pins["echo"]

    # Send a 10 microsecond pulse
    GPIO.output(trig, True)
    time.sleep(0.00001)
    GPIO.output(trig, False)

    # Wait for echo to go HIGH (start of pulse)
    pulse_start = time.time()
    timeout_at = pulse_start + ECHO_TIMEOUT
    while GPIO.input(echo) == 0:
        pulse_start = time.time()
        if pulse_start > timeout_at:
            return None  # echo never went high - sensor unresponsive

    # Wait for echo to go LOW (end of pulse)
    pulse_end = pulse_start
    timeout_at = pulse_start + ECHO_TIMEOUT
    while GPIO.input(echo) == 1:
        pulse_end = time.time()
        if pulse_end > timeout_at:
            return None  # echo stuck high - sensor malfunctioning

    # Calculate distance in centimetres
    echo_time = pulse_end - pulse_start
    distance = (echo_time * 34300) / 2

    return round(distance, 1)

    return round(distance, 1)
def cleanup():
    GPIO.cleanup()


def ultrasonic_loop():
    """Main ultrasonic sensor loop. Reads all sensors in turn,
    fires alerts if obstacles detected, and prints distances.
    Designed to run as a thread from main.py, or standalone for testing."""
    setup_gpio()
    try:
        while not state.shutdown_flag:
            for sensor_name in SENSOR_PINS:
                dist = get_distance(sensor_name)
                if dist is None:
                    print(f"{sensor_name}: timeout (no reading)")
                    continue
                alert_level = check_alert(dist)
                if alert_level != "clear":
                    # Rate-limit: skip if this (sensor, level) was alerted within the cooldown window
                    alert_key = (sensor_name, alert_level)
                    now = time.time()
                    last_time = last_alert_times.get(alert_key,0)
                    if now - last_time >= ALERT_COOLDOWN:
                        phrase = ALERT_PHRASES[sensor_name][alert_level]
                        priority = ALERT_PRIORITY[alert_level]
                        speak(priority, phrase)
                        last_alert_times[alert_key] = now
                print(f"{sensor_name}: {dist} cm ({alert_level}")
            time.sleep(0.5)
    finally:
        cleanup()


if __name__ == "__main__":
    start_speech_thread()
    ultrasonic_loop()
