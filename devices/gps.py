import serial
import pynmea2
class GPS:
    def __init__(self, port="/dev/ttyUSB1", baudrate=57600):
        self.ser = serial.Serial(port, baudrate, timeout=1)

    def read_location(self):
        while True:
            line = self.ser.readline().decode(errors='ignore').strip()
            if line.startswith("$"):
                msg = pynmea2.parse(line)
                if hasattr(msg, 'latitude') and hasattr(msg, 'longitude'):
                    print(msg.latitude, msg.longitude)
                    return (msg.latitude, msg.longitude)
        

                
