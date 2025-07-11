import threading
import math
import numpy as np
import time

class FollowTheGapWorker:
    def __init__(self, lidar, min_gap_dist=1000):
        self.lidar = lidar
        self.min_gap_dist = min_gap_dist
        self.lock = threading.Lock()
        self.latest_angle = None  # in radians
        self.running = True
        self.thread = threading.Thread(target=self._run, daemon=True)
        self.thread.start()
        self.min_distance = None

    def _follow_the_gap(self, ranges_deg_dist):
        scan = np.full(360, 0.0)
        distances = []
        
        for angle_deg, dist_mm in ranges_deg_dist:
            index = int(angle_deg) % 360
            scan[index] = dist_mm / 1000.0
            distances.append(scan[index])
            
        if distances:
            self.min_distance = min(distances)

        mask = scan > (self.min_gap_dist / 1000.0)
        max_start = 0
        max_len = 0
        current_start = None

        for i in range(360):
            if mask[i]:
                if current_start is None:
                    current_start = i
            else:
                if current_start is not None:
                    length = i - current_start
                    if length > max_len:
                        max_len = length
                        max_start = current_start
                    current_start = None
        if current_start is not None:
            length = 360 - current_start
            if length > max_len:
                max_len = length
                max_start = current_start

        if max_len == 0:
            return None

        gap_center_index = (max_start + max_len // 2) % 360
        return math.radians(gap_center_index)

    def _run(self):
        while True:
            scan =  self.lidar.get_scan()
            if scan != None :
                best_angle = self._follow_the_gap(scan)
                with self.lock:
                    self.latest_angle = best_angle
            time.sleep(0.1)

    def get_current_gap_angle(self):
        with self.lock:
            return self.latest_angle
    
    def stop(self):
        self.running = False
        self.thread.join()
