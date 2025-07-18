import time
import struct
import math
import signal
import sys

Commands = {
    "turn_wheel":        0,
    "turn_while_moving": 1,
    "turn_inplace":      2,
    "drive_straight":    3,
    "drive_m_meters":    4,
    "reverse":           5,
}

class EnhancedHybridNavigator:
    def __init__(self, base_speed, ftg_navigator, waypoint_navigator, camera, ser):
        self.ftg_navigator = ftg_navigator
        self.waypoint_navigator = waypoint_navigator
        self.camera = camera
        self.base_speed = base_speed
        self.safe_distance = 1.5
        self.stop_distance = 0.5
        self.camera_detection_distance = 2.0
        self.ser = ser
        self.last_command_time = time.time()

        self.MODE_GPS_NAVIGATION = 0
        self.MODE_OBSTACLE_AVOIDANCE = 1
        self.current_mode = self.MODE_GPS_NAVIGATION

        self.frame_width = 640
        self.frame_height = 480
        self.center_zone_width = 200
        self.center_zone_height = 150

        signal.signal(signal.SIGINT, self.signal_handler)

    def signal_handler(self, sig, frame):
        self.stop_robot()
        sys.exit(0)

    def send_command(self, command, param1=0, param2=0, param3=0):
        current_time = time.time()
        if current_time - self.last_command_time < 0.02:
            time.sleep(0.02 - (current_time - self.last_command_time))

        if self.ser and self.ser.is_open:
            try:
                packet = struct.pack('<BBfff', command, 0, param1, param2, param3)
                self.ser.write(packet)
                self.ser.flush()
                self.last_command_time = time.time()
                return True
            except Exception as e:
                print(f"Serial write error: {e}")
                return False
        return False

    def stop_robot(self):
        print("Stopping robot...")
        self.send_command(Commands["drive_straight"], 0)
        time.sleep(0.1)

    def get_lidar_distance_at_angle(self, target_angle_deg):
        scan = self.ftg_navigator.lidar.get_scan()
        if not scan:
            return None

        min_angle_diff = float('inf')
        closest_distance = None

        for angle, dist in scan:
            angle_diff = abs(angle - target_angle_deg)
            if angle_diff > 180:
                angle_diff = 360 - angle_diff

            if angle_diff < min_angle_diff:
                min_angle_diff = angle_diff
                closest_distance = dist / 1000.0

        return closest_distance if min_angle_diff < 5 else None

    def get_object_distance_from_lidar(self, obj_center_x):
        camera_center_x = self.frame_width / 2
        pixel_offset = obj_center_x - camera_center_x

        camera_fov = 60
        angle_per_pixel = camera_fov / self.frame_width
        object_angle = pixel_offset * angle_per_pixel
        lidar_angle = -object_angle % 360

        return self.get_lidar_distance_at_angle(lidar_angle)

    def is_object_in_path(self, obj):
        x, y, w, h = obj['bbox']
        center_x, center_y = obj['center']

        zone_left = (self.frame_width - self.center_zone_width) // 2
        zone_right = zone_left + self.center_zone_width
        zone_top = (self.frame_height - self.center_zone_height) // 2
        zone_bottom = zone_top + self.center_zone_height

        if (zone_left <= center_x <= zone_right and
                zone_top <= center_y <= zone_bottom):
            return True

        overlap_left = max(x, zone_left)
        overlap_right = min(x + w, zone_right)
        overlap_top = max(y, zone_top)
        overlap_bottom = min(y + h, zone_bottom)

        if overlap_left < overlap_right and overlap_top < overlap_bottom:
            overlap_area = (overlap_right - overlap_left) * (overlap_bottom - overlap_top)
            obj_area = w * h
            overlap_ratio = overlap_area / obj_area

            if overlap_ratio > 0.3:
                return True

        return False

    def detect_forward_obstacles(self):
        objects = self.camera.get_objects()

        if not objects:
            return False, None, None

        forward_obstacles = []

        for obj in objects:
            if self.is_object_in_path(obj):
                center_x, center_y = obj['center']
                lidar_distance = self.get_object_distance_from_lidar(center_x)

                if lidar_distance is not None:
                    forward_obstacles.append({
                        'object': obj,
                        'distance': lidar_distance,
                        'camera_center': (center_x, center_y),
                        'lidar_confirmed': True
                    })
                else:
                    x, y, w, h = obj['bbox']
                    bbox_area = w * h
                    estimated_distance = max(0.5, 4.0 * (self.frame_width * self.frame_height) / (bbox_area * 1000))
                    forward_obstacles.append({
                        'object': obj,
                        'distance': estimated_distance,
                        'camera_center': (center_x, center_y),
                        'lidar_confirmed': False
                    })

        if not forward_obstacles:
            return False, None, None

        closest_obstacle = min(forward_obstacles, key=lambda x: x['distance'])
        closest_distance = closest_obstacle['distance']

        if closest_distance <= self.camera_detection_distance:
            return True, closest_distance, closest_obstacle

        return False, closest_distance, closest_obstacle

    def get_lidar_forward_distance(self):
        scan = self.ftg_navigator.lidar.get_scan()
        if not scan:
            return None

        forward_distances = []
        for angle, dist in scan:
            if angle < 30 or angle > 330:
                forward_distances.append(dist / 1000.0)

        return min(forward_distances) if forward_distances else None

    def calculate_navigation_speed_radius(self, angle, dist):
        if dist > 3:
            speed = self.base_speed
        elif dist != 0:
            if dist < self.waypoint_navigator.waypoint_rad:
                self.waypoint_navigator.next_waypoint()
            speed = self.base_speed * min(1.0, self.safe_distance / dist)
        else:
            speed = 0

        if abs(angle) < 0.05:
            radius = float('inf')
        else:
            direction = -1 if angle < 0 else 1
            radius = direction * max(0.8, min(2.0, 4.5 / abs(angle)))

        return speed, radius

    def calculate_avoidance_speed_radius(self, gap_angle, min_dist):
        if min_dist <= 0:
            return 0, 1.0

        speed_factor = min(1.0, min_dist / self.safe_distance)
        speed = self.base_speed * speed_factor * 0.7

        if gap_angle is None or abs(gap_angle) < 0.1:
            radius = float('inf')
        else:
            radius = -max(0.5, min(1.5, 0.8 / abs(gap_angle)))

        return speed, radius

    def execute_gps_navigation(self, nav_error, nav_distance):
        if nav_error is None or nav_distance is None:
            print("GPS navigation data not available")
            self.stop_robot()
            return

        speed, radius = self.calculate_navigation_speed_radius(nav_error, nav_distance)

        print(f"GPS Nav - Error: {nav_error:.3f} rad ({math.degrees(nav_error):.1f}°), "
              f"Distance: {nav_distance:.2f}m, Speed: {speed:.2f}, Radius: {radius:.2f}")

        if speed <= 0:
            self.stop_robot()
        elif radius > 10.0:
            self.send_command(Commands["drive_straight"], speed)
        else:
            turn_radius = radius if nav_error >= 0 else -radius
            self.send_command(Commands["turn_while_moving"], turn_radius, speed)

    def execute_obstacle_avoidance(self, gap_angle, min_dist):
        if min_dist and min_dist <= self.stop_distance:
            print(f"Emergency stop - Obstacle at {min_dist:.2f}m")
            self.stop_robot()
            time.sleep(0.1)
            print("Reversing...")
            self.send_command(Commands["reverse"], 20)
            time.sleep(1.5)
            return

        if gap_angle is None or min_dist is None:
            print("Avoidance data not available - stopping")
            self.stop_robot()
            return

        speed, radius = self.calculate_avoidance_speed_radius(gap_angle, min_dist)

        print(f"Avoidance - Gap angle: {gap_angle:.3f} rad ({math.degrees(gap_angle):.1f}°), "
              f"Min dist: {min_dist:.2f}m, Speed: {speed:.2f}, Radius: {radius:.2f}")

        if speed <= 0:
            self.stop_robot()
        elif radius > 10.0:
            self.send_command(Commands["drive_straight"], speed)
        else:
            turn_radius = radius if gap_angle >= 0 else -radius
            self.send_command(Commands["turn_while_moving"], turn_radius, speed)

    def run(self):
        print("Starting enhanced hybrid navigation...")
        while True:
            try:
                camera_obstacle, camera_distance, obstacle_info = self.detect_forward_obstacles()
                lidar_min_dist = self.get_lidar_forward_distance()
                gap_angle = self.ftg_navigator.get_current_gap_angle()
                nav_error, nav_distance, _ = self.waypoint_navigator.get_navigation_command()

                previous_mode = self.current_mode

                if camera_obstacle and camera_distance and camera_distance <= self.camera_detection_distance:
                    if self.current_mode != self.MODE_OBSTACLE_AVOIDANCE:
                        print(f"Switching to avoidance: Camera detected obstacle at {camera_distance:.2f}m")
                    self.current_mode = self.MODE_OBSTACLE_AVOIDANCE
                elif lidar_min_dist and lidar_min_dist <= self.safe_distance:
                    if self.current_mode != self.MODE_OBSTACLE_AVOIDANCE:
                        print(f"Switching to avoidance: Lidar detected obstacle at {lidar_min_dist:.2f}m")
                    self.current_mode = self.MODE_OBSTACLE_AVOIDANCE
                else:
                    if self.current_mode == self.MODE_OBSTACLE_AVOIDANCE:
                        print("Path clear - switching back to GPS navigation")
                    self.current_mode = self.MODE_GPS_NAVIGATION

                if self.current_mode == self.MODE_GPS_NAVIGATION:
                    self.execute_gps_navigation(nav_error, nav_distance)
                elif self.current_mode == self.MODE_OBSTACLE_AVOIDANCE:
                    effective_min_dist = lidar_min_dist if obstacle_info is None or not obstacle_info.get('lidar_confirmed', False) else camera_distance
                    self.execute_obstacle_avoidance(gap_angle, effective_min_dist)

                time.sleep(0.1)

            except Exception as e:
                print(f"Error in navigation loop: {e}")
                self.stop_robot()
                time.sleep(0.5)

    def __del__(self):
        self.stop_robot()
