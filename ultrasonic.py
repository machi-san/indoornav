import RPi.GPIO as GPIO
import time
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

def get_distance(sensor_name):
    pins = SENSOR_PINS[sensor_name]
    trig = pins["trig"]
    echo = pins["echo"]

    # Send a 10 microsecond pulse
    GPIO.output(trig, True)
    time.sleep(0.00001)
    GPIO.output(trig, False)

    # Measure echo time
    while GPIO.input(echo) == 0:
        pulse_start = time.time()
    while GPIO.input(echo) == 1:
        pulse_end = time.time()

    # Calculate distance in centimetres
    echo_time = pulse_end - pulse_start
    distance = (echo_time * 34300) / 2

    return round(distance, 1)
def cleanup():
    GPIO.cleanup()

if __name__ == "__main__":
    setup_gpio()
    try:
        while True:
            for sensor_name in SENSOR_PINS:
                dist = get_distance(sensor_name)
                print(f"{sensor_name}: {dist} cm")
            time.sleep(0.5)
    except KeyboardInterrupt:
        cleanup()