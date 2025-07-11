from rplidar import RPLidar
from threading import Thread
import threading

class Lidar:
    def __init__(self, PORT):
        self.device = RPLidar(PORT)
        self.latest_scan = None
        self.lock = threading.Lock()
        self.start()
    def _run(self):
        for scan in self.device.iter_scans(scan_type="express"):
            points = [(angle, dist) for (_, angle, dist) in scan if dist > 0]
            filtered_points = [(angle, dist) for (angle, dist) in points if angle < 100 or angle > 260] #front facing points only to avoid seeing the battery  
            with self.lock:
                self.latest_scan = filtered_points
    
    def start(self):
        Thread(target=self._run, daemon=True).start()
    
    def get_scan(self):
        with self.lock:
            return self.latest_scan
