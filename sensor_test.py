from ultrasonic import setup_gpio, get_distance, cleanup
import time

setup_gpio()

print("Wave hand in front of each sensor. Ctrl+C to stop.")
try:
    while True:
        for name in ['north', 'north_east', 'north_west']:
            d = get_distance(name)
            print(f"{name}: {d}")
        print("---")
        time.sleep(0.5)
except KeyboardInterrupt:
    cleanup()
    print("Done.")
