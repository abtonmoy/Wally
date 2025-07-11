import Jetson.GPIO as GPIO
import time

import Jetson.GPIO as GPIO
import time

class UltrasonicSensor:
    def __init__(self, trig_pin, echo_pin, timeout=0.04):
        self.trig = trig_pin
        self.echo = echo_pin
        GPIO.setup(self.trig, GPIO.OUT)
        GPIO.setup(self.echo, GPIO.IN)
        GPIO.output(self.trig, False)
        self.timeout=timeout
        time.sleep(0.1)  # Sensor settle time

    def get_distance(self):
        # Send trigger pulse
        GPIO.output(self.trig, True)
        time.sleep(0.0001)
        GPIO.output(self.trig, False)

        # Wait for echo start
        pulse_start = time.time()
        timeout = pulse_start + self.timeout
        while GPIO.input(self.echo) == 0:
            pulse_start = time.time()
            if pulse_start > timeout:
                return None

        # Wait for echo end
        pulse_end = time.time()
        timeout = pulse_end + self.timeout
        while GPIO.input(self.echo) == 1:
            pulse_end = time.time()
            if pulse_end > timeout:
                return None 

        pulse_duration = pulse_end - pulse_start
        distance_cm = pulse_duration * 17150

        return round(distance_cm, 2)

    def cleanup(self):
        GPIO.cleanup([self.trig, self.echo])

if __name__ == '__main__':
    sensor = UltrasonicSensor(trig_pin=11, echo_pin=13)

    try:
        while True:
            dist = sensor.get_distance()
            if dist is None:
                print("Timeout or no echo detected")
            else:
                print(f"Distance: {dist} cm")
            time.sleep(1)

    except KeyboardInterrupt:
        print("Stopping")

    finally:
        sensor.cleanup()

