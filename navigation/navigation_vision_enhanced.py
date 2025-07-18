import time
import serial
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

class HybridNavigator:
    def __init__(self, base_speed, ftg_navigator, waypoint_navigator, camera, ser):
        self.ftg_navigator = ftg_navigator
        self.waypoint_navigator = waypoint_navigator
        self.camera = camera
        self.base_speed = base_speed
        self.safe_distance = 1.5
        self.stop_distance = 0.5
        self.camera_detection_distance = 2.0  # 2 meters trigger distance for camera
        self.ser = ser
        self.last_command_time = time.time()
        
        # Navigation modes
        self.MODE_GPS_NAVIGATION = 0
        self.MODE_OBSTACLE_AVOIDANCE = 1
        self.current_mode = self.MODE_GPS_NAVIGATION
        
        # Camera-based obstacle detection parameters
        self.frame_width = 640
        self.frame_height = 480
        self.center_zone_width = 200  # Width of center zone to monitor
        self.center_zone_height = 150  # Height of center zone to monitor

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
            except serial.SerialException as e:
                print(f"Serial write error: {e}")
                return False
        return False

    def stop_robot(self):
        print("Stopping robot...")
        self.send_command(Commands["drive_straight"], 0)
        time.sleep(0.1)

    def get_lidar_distance_at_angle(self, target_angle_deg):
        """
        Get lidar distance at a specific angle (in degrees)
        Returns distance in meters, or None if no data available
        """
        scan = self.ftg_navigator.lidar.get_scan()
        if not scan:
            return None
        
        # Find the closest lidar point to the target angle
        min_angle_diff = float('inf')
        closest_distance = None
        
        for angle, dist in scan:
            angle_diff = abs(angle - target_angle_deg)
            # Handle wrap-around (e.g., 359° vs 1°)
            if angle_diff > 180:
                angle_diff = 360 - angle_diff
            
            if angle_diff < min_angle_diff:
                min_angle_diff = angle_diff
                closest_distance = dist / 1000.0  # Convert mm to meters
        
        return closest_distance if min_angle_diff < 5 else None  # Within 5 degrees

    def get_object_distance_from_lidar(self, obj_center_x):
        """
        Get object distance using lidar data based on object's horizontal position in camera frame
        """
        # Convert camera X position to lidar angle
        # Camera center X corresponds to 0° (straight ahead)
        # Adjust this mapping based on your camera/lidar alignment
        
        # Calculate angle from camera center
        camera_center_x = self.frame_width / 2
        pixel_offset = obj_center_x - camera_center_x
        
        # Convert pixel offset to angle (adjust FOV as needed)
        # Assuming camera horizontal FOV is about 60 degrees
        camera_fov = 60  # degrees
        angle_per_pixel = camera_fov / self.frame_width
        object_angle = pixel_offset * angle_per_pixel
        
        # Convert to lidar coordinate system (0° = forward, positive = clockwise)
        lidar_angle = -object_angle  # Negative because camera X increases left-to-right
        
        # Normalize angle to 0-360 range
        lidar_angle = lidar_angle % 360
        
        return self.get_lidar_distance_at_angle(lidar_angle)

    def is_object_in_path(self, obj):
        """
        Check if detected object is in the robot's forward path
        """
        x, y, w, h = obj['bbox']
        center_x, center_y = obj['center']
        
        # Define the forward path zone (center portion of the frame)
        zone_left = (self.frame_width - self.center_zone_width) // 2
        zone_right = zone_left + self.center_zone_width
        zone_top = (self.frame_height - self.center_zone_height) // 2
        zone_bottom = zone_top + self.center_zone_height
        
        # Check if object center or significant portion is in the forward zone
        if (zone_left <= center_x <= zone_right and 
            zone_top <= center_y <= zone_bottom):
            return True
            
        # Also check if object significantly overlaps with the forward zone
        overlap_left = max(x, zone_left)
        overlap_right = min(x + w, zone_right)
        overlap_top = max(y, zone_top)
        overlap_bottom = min(y + h, zone_bottom)
        
        if overlap_left < overlap_right and overlap_top < overlap_bottom:
            overlap_area = (overlap_right - overlap_left) * (overlap_bottom - overlap_top)
            obj_area = w * h
            overlap_ratio = overlap_area / obj_area
            
            # If more than 30% of object is in forward zone, consider it in path
            if overlap_ratio > 0.3:
                return True
        
        return False

    def detect_forward_obstacles(self):
        """
        Use camera to detect obstacles in the forward path and lidar for accurate distance
        Returns: (obstacle_detected, closest_distance, obstacle_info)
        """
        objects = self.camera.get_objects()
        
        if not objects:
            return False, None, None
        
        forward_obstacles = []
        
        for obj in objects:
            if self.is_object_in_path(obj):
                # Use lidar to get accurate distance
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
                    # Fallback: if no lidar data available, use camera-based estimation
                    print(f"Warning: No lidar data for object at pixel {center_x}, using camera estimation")
                    # Simple fallback based on object size and position
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
        
        # Find closest obstacle
        closest_obstacle = min(forward_obstacles, key=lambda x: x['distance'])
        closest_distance = closest_obstacle['distance']
        
        # Check if closest obstacle is within trigger distance
        if closest_distance <= self.camera_detection_distance:
            return True, closest_distance, closest_obstacle
        
        return False, closest_distance, closest_obstacle

    def calculate_navigation_speed_radius(self, angle, dist):
        """Calculate speed and radius for GPS navigation mode"""
        if dist > 3:
            speed = self.base_speed
        elif dist != 0:
            if dist < self.waypoint_navigator.waypoint_rad:
                self.waypoint_navigator.next_waypoint()
            speed = self.base_speed * min(1.0, self.safe_distance / dist)
        else:
            speed = 0
        
        # Calculate turning radius based on heading error
        if abs(angle) < 0.05:  # ~3 degrees, go straight
            radius = float('inf')
        else:
            #positive radius for testing
            direction = -1 if angle < 0 else 1 
            radius = direction * max(0.8, min(2.0, 4.5 / abs(angle)))
        
        return speed, radius

    def calculate_avoidance_speed_radius(self, gap_angle, min_dist):
        """Calculate speed and radius for obstacle avoidance mode"""
        if min_dist <= 0:
            return 0, 1.0
        
        # Reduce speed when obstacles are close
        speed_factor = min(1.0, min_dist / self.safe_distance)
        speed = self.base_speed * speed_factor * 0.7  # Slower during avoidance
        
        # Calculate turning radius based on gap angle
        if gap_angle is None or abs(gap_angle) < 0.1:
            radius = float('inf')
        else:
            #negative radius for testing
            radius = -max(0.5, min(1.5, 0.8 / abs(gap_angle)))
        
        return speed, radius

    def get_lidar_forward_distance(self):
        """Get minimum distance from lidar in forward-facing direction"""
        scan = self.ftg_navigator.lidar.get_scan()
        if not scan:
            return None
        
        forward_distances = []
        for angle, dist in scan:
            # Consider forward-facing angles (adjust range as needed)
            if (angle < 30 or angle > 330):  # Forward cone
                forward_distances.append(dist / 1000.0)  # Convert to meters
        
        return min(forward_distances) if forward_distances else None

    def execute_gps_navigation(self, nav_error, nav_distance):
        """Execute GPS navigation mode - clean separation from obstacle avoidance"""
        if nav_error is None or nav_distance is None:
            print("GPS navigation data not available")
            self.stop_robot()
            return
        
        speed, radius = self.calculate_navigation_speed_radius(nav_error, nav_distance)
        
        print(f"GPS Nav - Error: {nav_error:.3f} rad ({math.degrees(nav_error):.1f}°), "
              f"Distance: {nav_distance:.2f}m, Speed: {speed:.2f}, Radius: {radius:.2f}")
        
        # Execute movement command
        if speed <= 0:
            self.stop_robot()
        elif radius > 10.0:  # Actually straight
            self.send_command(Commands["drive_straight"], speed)
        else:
            # Turn in direction of navigation error
            turn_radius = radius if nav_error >= 0 else -radius
            print(f"GPS turning with radius: {turn_radius:.2f}")
            self.send_command(Commands["turn_while_moving"], turn_radius, speed)

    def execute_obstacle_avoidance(self, gap_angle, min_dist):
        """Execute obstacle avoidance mode - clean separation from GPS navigation"""
        # Emergency stop for very close obstacles
        if min_dist and min_dist <= self.stop_distance:
            print(f"Emergency stop - Obstacle at {min_dist:.2f}m")
            self.stop_robot()
            time.sleep(0.1)
            print("Reversing...")
            self.send_command(Commands["reverse"], 20)
            time.sleep(1.5)
            return
        
        # Calculate avoidance maneuver
        if gap_angle is None or min_dist is None:
            print("Avoidance data not available - stopping")
            self.stop_robot()
            return
        
        speed, radius = self.calculate_avoidance_speed_radius(gap_angle, min_dist)
        
        print(f"Avoidance - Gap angle: {gap_angle:.3f} rad ({math.degrees(gap_angle):.1f}°), "
              f"Min dist: {min_dist:.2f}m, Speed: {speed:.2f}, Radius: {radius:.2f}")
        
        # Execute movement command
        if speed <= 0:
            self.stop_robot()
        elif radius > 10.0:  # Actually straight
            self.send_command(Commands["drive_straight"], speed)
        else:
            # Turn in direction of gap
            turn_radius = radius if gap_angle >= 0 else -radius
            print(f"Avoidance turning with radius: {turn_radius:.2f}")
            self.send_command(Commands["turn_while_moving"], turn_radius, speed)

    def should_switch_to_avoidance(self, camera_obstacle, camera_distance, lidar_min_dist):
        """Determine if we should switch to obstacle avoidance mode"""
        # Camera detected obstacle within trigger distance
        if camera_obstacle and camera_distance and camera_distance <= self.camera_detection_distance:
            return True, f"Camera detected obstacle at {camera_distance:.2f}m"
        
        # Lidar detected obstacle within safe distance
        if lidar_min_dist and lidar_min_dist <= self.safe_distance:
            return True, f"Lidar detected obstacle at {lidar_min_dist:.2f}m"
        
        return False, None

    def should_switch_to_gps(self, camera_obstacle, camera_distance, lidar_min_dist):
        """Determine if we should switch back to GPS navigation mode"""
        # No camera obstacles beyond trigger distance
        camera_clear = not camera_obstacle or (camera_distance and camera_distance > self.camera_detection_distance)
        
        # No lidar obstacles beyond safe distance
        lidar_clear = not lidar_min_dist or lidar_min_dist > self.safe_distance
        
        return camera_clear and lidar_clear

    def run(self):
        print("Starting hybrid navigation with camera integration...")
        
        while True:
            try:
                # Gather all sensor data
                camera_obstacle, camera_distance, obstacle_info = self.detect_forward_obstacles()
                lidar_min_dist = self.get_lidar_forward_distance()
                gap_angle = self.ftg_navigator.get_current_gap_angle()
                nav_error, nav_distance, desired_bearing = self.waypoint_navigator.get_navigation_command()
                
                # Determine navigation mode with clear logic
                previous_mode = self.current_mode
                
                if self.current_mode == self.MODE_GPS_NAVIGATION:
                    # Check if we need to switch to avoidance
                    should_avoid, avoid_reason = self.should_switch_to_avoidance(
                        camera_obstacle, camera_distance, lidar_min_dist)
                    
                    if should_avoid:
                        self.current_mode = self.MODE_OBSTACLE_AVOIDANCE
                        print(f"Switching to avoidance mode: {avoid_reason}")
                
                elif self.current_mode == self.MODE_OBSTACLE_AVOIDANCE:
                    # Check if we can switch back to GPS
                    if self.should_switch_to_gps(camera_obstacle, camera_distance, lidar_min_dist):
                        self.current_mode = self.MODE_GPS_NAVIGATION
                        print("Clear path - Switching back to GPS navigation")
                
                # Execute navigation based on current mode
                if self.current_mode == self.MODE_GPS_NAVIGATION:
                    self.execute_gps_navigation(nav_error, nav_distance)
                else:
                    # Determine which distance to use for avoidance
                    if camera_distance and obstacle_info and obstacle_info.get('lidar_confirmed', False):
                        effective_min_dist = camera_distance
                        print(f"Using camera-detected object distance: {effective_min_dist:.2f}m")
                    else:
                        effective_min_dist = lidar_min_dist
                        if effective_min_dist:
                            print(f"Using lidar minimum distance: {effective_min_dist:.2f}m")
                    
                    self.execute_obstacle_avoidance(gap_angle, effective_min_dist)
                
                time.sleep(0.1)
                
            except Exception as e:
                print(f"Error in navigation loop: {e}")
                self.stop_robot()
                time.sleep(0.5)

    def get_status(self):
        """Get current navigation status"""
        return {
            'mode': 'GPS_NAVIGATION' if self.current_mode == self.MODE_GPS_NAVIGATION else 'OBSTACLE_AVOIDANCE',
            'base_speed': self.base_speed,
            'safe_distance': self.safe_distance,
            'camera_trigger_distance': self.camera_detection_distance
        }
