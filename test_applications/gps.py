import serial
import pynmea2
import threading
import time
from utils import Vector

# Shared variable for latest GPS coordinates
latest_coords = {'lat': None, 'lon': None, 'acc': None, 'msg': None, 'line':None}
lock = threading.Lock()

def gps_poll(port='/dev/ttyACM0', baud=9600, update_interval=0.01):
    """Background thread function to read GPS data."""
    global latest_coords
    ser = serial.Serial(port, baud, timeout=1)

    while True:
        try:
            line = ser.readline().decode('ascii', errors='replace').strip()
            latest_coords['line'] = line
            if line.startswith('$GPGGA') or line.startswith('$GPRMC'):
                msg = pynmea2.parse(line)
                latest_coords['msg'] = msg
                if hasattr(msg, 'latitude') and hasattr(msg, 'longitude'):
                    with lock:
                        latest_coords['lat'] = msg.latitude
                        latest_coords['lon'] = msg.longitude
                        #latest_coords['acc'] = msg.horizontal_dil
            time.sleep(update_interval)  # limit frequency of update
        except Exception as e:
            print(f"GPS read error: {e}")
t = threading.Thread(target=gps_poll, daemon=True).start()
time.sleep(5)
def gps_read():
    if latest_coords['lat'] != None and latest_coords['lon'] != None:
        return Vector(latest_coords['lat'], latest_coords['lon'])
    else:
        return Vector(0,0)
# Start GPS thread


if __name__ == "__main__":
    while True:
        print(f"Lon: {latest_coords['lon']}, Lat: {latest_coords['lat']}")

        time.sleep(1)