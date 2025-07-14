import time
import serial
import struct
import math
import signal
import sys
import cv2
import os
from datetime import datetime
import threading
import queue

Commands = {
    "turn_wheel":        0,
    "turn_while_moving": 1,
    "turn_inplace":      2,
    "drive_straight":    3,
    "drive_m_meters":    4,
    "reverse":           5,
}

class VideoRecorder:
    def __init__(self, output_dir="recordings", fps=20, resolution=(640, 480)):
        self.output_dir = output_dir
        self.fps = fps
        self.resolution = resolution
        self.recording = False
        self.video_writer = None
        self.frame_queue = queue.Queue(maxsize=100)
        self.recording_thread = None
        self.current_filename = None
        
        # Create output directory if it doesn't exist
        os.makedirs(output_dir, exist_ok=True)
        
    def start_recording(self, session_name=None):
        """Start video recording"""
        if self.recording:
            print("Recording already in progress")
            return False
            
        # Generate filename with timestamp
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        if session_name:
            self.current_filename = f"{session_name}_{timestamp}.avi"
        else:
            self.current_filename = f"robot_navigation_{timestamp}.avi"
        
        filepath = os.path.join(self.output_dir, self.current_filename)
        
        # Initialize video writer
        fourcc = cv2.VideoWriter_fourcc(*'XVID')
        self.video_writer = cv2.VideoWriter(filepath, fourcc, self.fps, self.resolution)
        
        if not self.video_writer.isOpened():
            print(f"Error: Could not open video writer for {filepath}")
            return False
            
        self.recording = True
        
        # Start recording thread
        self.recording_thread = threading.Thread(target=self._recording_worker)
        self.recording_thread.daemon = True
        self.recording_thread.start()
        
        print(f"Started recording to: {filepath}")
        return True
    
    def stop_recording(self):
        """Stop video recording"""
        if not self.recording:
            print("No recording in progress")
            return False
            
        self.recording = False
        
        # Wait for recording thread to finish
        if self.recording_thread and self.recording_thread.is_alive():
            self.recording_thread.join(timeout=5)
        
        # Release video writer
        if self.video_writer:
            self.video_writer.release()
            self.video_writer = None
            
        # Clear any remaining frames
        while not self.frame_queue.empty():
            try:
                self.frame_queue.get_nowait()
            except queue.Empty:
                break
                
        print(f"Recording stopped and saved to: {self.current_filename}")
        return True
    
    def add_frame(self, frame):
        """Add a frame to the recording queue"""
        if not self.recording:
            return False
            
        # Resize frame if necessary
        if frame.shape[:2][::-1] != self.resolution:
            frame = cv2.resize(frame, self.resolution)
            
        try:
            self.frame_queue.put(frame, timeout=0.01)
            return True
        except queue.Full:
            print("Warning: Frame queue full, dropping frame")
            return False
    
    def _recording_worker(self):
        """Worker thread for writing frames to video file"""
        while self.recording or not self.frame_queue.empty():
            try:
                frame = self.frame_queue.get(timeout=0.1)
                if self.video_writer:
                    self.video_writer.write(frame)
                self.frame_queue.task_done()
            except queue.Empty:
                continue
            except Exception as e:
                print(f"Error writing frame: {e}")
                break
    
    def is_recording(self):
        """Check if currently recording"""
        return self.recording
    
    def get_current_filename(self):
        """Get current recording filename"""
        return self.current_filename if self.recording else None


class HybridNavigator:
    def __init__(self, base_speed, ftg_navigator, waypoint_navigator, camera, ser, 
                 enable_recording=True, recording_dir="recordings"):
        self.ftg_navigator = ftg_navigator
        self.waypoint_navigator = waypoint_navigator
        self.camera = camera
        self.base_speed = base_speed
        self.safe_distance = 1.5
        self.stop_distance = 0.5
        self.camera_detection_distance = 2.0
        self.ser = ser
        self.last_command_time = time.time()
        
        # Navigation modes
        self.MODE_GPS_NAVIGATION = 0
        self.MODE_OBSTACLE_AVOIDANCE = 1
        self.current_mode = self.MODE_GPS_NAVIGATION
        
        # Camera-based obstacle detection parameters
        self.frame_width = 640
        self.frame_height = 480
        self.center_zone_width = 200
        self.center_zone_height = 150
        
        # Video recording setup
        self.enable_recording = enable_recording
        self.video_recorder = VideoRecorder(
            output_dir=recording_dir,
            fps=20,
            resolution=(self.frame_width, self.frame_height)
        ) if enable_recording else None
        
        # Auto-start recording flag
        self.auto_record = True
        self.recording_started = False

        signal.signal(signal.SIGINT, self.signal_handler)
        
    def signal_handler(self, sig, frame):
        """Handle shutdown gracefully"""
        print("Shutting down...")
        self.stop_robot()
        if self.video_recorder and self.video_recorder.is_recording():
            self.video_recorder.stop_recording()
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

    def start_recording(self, session_name=None):
        """Start video recording with optional session name"""
        if self.video_recorder:
            return self.video_recorder.start_recording(session_name)
        return False
    
    def stop_recording(self):
        """Stop video recording"""
        if self.video_recorder:
            return self.video_recorder.stop_recording()
        return False
    
    def toggle_recording(self):
        """Toggle recording on/off"""
        if self.video_recorder:
            if self.video_recorder.is_recording():
                return self.stop_recording()
            else:
                return self.start_recording()
        return False

    def get_lidar_distance_at_angle(self, target_angle_deg):
        """Get lidar distance at a specific angle (in degrees)"""
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
        """Get object distance using lidar data based on object's horizontal position"""
        camera_center_x = self.frame_width / 2
        pixel_offset = obj_center_x - camera_center_x
        
        camera_fov = 60
        angle_per_pixel = camera_fov / self.frame_width
        object_angle = pixel_offset * angle_per_pixel
        
        lidar_angle = -object_angle
        lidar_angle = lidar_angle % 360
        
        return self.get_lidar_distance_at_angle(lidar_angle)

    def is_object_in_path(self, obj):
        """Check if detected object is in the robot's forward path"""
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
        """Use camera to detect obstacles and record the frame"""
        # Get camera frame and objects
        frame = self.camera.get_frame()  # Assuming camera has get_frame() method
        objects = self.camera.get_objects()
        
        # Record the frame if recording is enabled
        if self.video_recorder and self.video_recorder.is_recording() and frame is not None:
            # Add navigation info overlay to the frame
            display_frame = self.add_navigation_overlay(frame.copy())
            self.video_recorder.add_frame(display_frame)
        
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
                    print(f"Warning: No lidar data for object at pixel {center_x}, using camera estimation")
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

    def add_navigation_overlay(self, frame):
        """Add navigation information overlay to the frame"""
        if frame is None:
            return frame
            
        # Add mode indicator
        mode_text = "GPS NAV" if self.current_mode == self.MODE_GPS_NAVIGATION else "OBSTACLE AVOID"
        cv2.putText(frame, f"Mode: {mode_text}", (10, 30), 
                   cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 255, 0), 2)
        
        # Add speed indicator
        cv2.putText(frame, f"Speed: {self.base_speed:.1f}", (10, 60), 
                   cv2.FONT_HERSHEY_SIMPLEX, 0.7, (255, 255, 0), 2)
        
        # Add timestamp
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        cv2.putText(frame, timestamp, (10, frame.shape[0] - 20), 
                   cv2.FONT_HERSHEY_SIMPLEX, 0.5, (255, 255, 255), 1)
        
        # Add recording indicator
        if self.video_recorder and self.video_recorder.is_recording():
            cv2.circle(frame, (frame.shape[1] - 30, 30), 10, (0, 0, 255), -1)
            cv2.putText(frame, "REC", (frame.shape[1] - 60, 40), 
                       cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0, 0, 255), 2)
        
        # Draw forward detection zone
        zone_left = (self.frame_width - self.center_zone_width) // 2
        zone_right = zone_left + self.center_zone_width
        zone_top = (self.frame_height - self.center_zone_height) // 2
        zone_bottom = zone_top + self.center_zone_height
        
        cv2.rectangle(frame, (zone_left, zone_top), (zone_right, zone_bottom), 
                     (0, 255, 255), 2)
        
        return frame

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
        
        if abs(angle) < 0.1:
            radius = float('inf')
        else:
            radius = max(0.5, min(2.0, 1.5 / abs(angle)))
        
        return speed, radius

    def calculate_avoidance_speed_radius(self, gap_angle, min_dist):
        """Calculate speed and radius for obstacle avoidance mode"""
        if min_dist <= 0:
            return 0, 1.0
        
        speed_factor = min(1.0, min_dist / self.safe_distance)
        speed = self.base_speed * speed_factor * 0.7
        
        if gap_angle is None or abs(gap_angle) < 0.1:
            radius = float('inf')
        else:
            radius = max(0.5, min(1.5, 0.8 / abs(gap_angle)))
        
        return speed, radius

    def get_lidar_forward_distance(self):
        """Get minimum distance from lidar in forward-facing direction"""
        scan = self.ftg_navigator.lidar.get_scan()
        if not scan:
            return None
        
        forward_distances = []
        for angle, dist in scan:
            if (angle < 30 or angle > 330):
                forward_distances.append(dist / 1000.0)
        
        return min(forward_distances) if forward_distances else None

    def run(self):
        """Main navigation loop with video recording"""
        print("Starting hybrid navigation with camera integration and video recording...")
        
        # Auto-start recording if enabled
        if self.auto_record and self.video_recorder:
            session_name = f"nav_session_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
            self.start_recording(session_name)
            self.recording_started = True
        
        try:
            while True:
                try:
                    # Get camera obstacle detection with lidar distance measurement
                    camera_obstacle, camera_distance, obstacle_info = self.detect_forward_obstacles()
                    
                    # Get lidar data for general area scanning
                    lidar_min_dist = self.get_lidar_forward_distance()
                    gap_angle = self.ftg_navigator.get_current_gap_angle()
                    
                    # Get GPS navigation data
                    nav_error, nav_distance, desired_bearing = self.waypoint_navigator.get_navigation_command()
                    
                    # Determine navigation mode
                    previous_mode = self.current_mode
                    
                    if camera_obstacle and camera_distance and camera_distance <= self.camera_detection_distance:
                        self.current_mode = self.MODE_OBSTACLE_AVOIDANCE
                        lidar_confirmed = obstacle_info.get('lidar_confirmed', False) if obstacle_info else False
                        confirmation_text = "lidar-confirmed" if lidar_confirmed else "camera-estimated"
                        print(f"Camera detected obstacle at {camera_distance:.2f}m ({confirmation_text}) - Switching to avoidance mode")
                    elif lidar_min_dist and lidar_min_dist <= self.safe_distance:
                        self.current_mode = self.MODE_OBSTACLE_AVOIDANCE
                        print(f"Lidar detected obstacle at {lidar_min_dist:.2f}m - Continuing avoidance mode")
                    else:
                        self.current_mode = self.MODE_GPS_NAVIGATION
                        if previous_mode == self.MODE_OBSTACLE_AVOIDANCE:
                            print("Clear path - Switching back to GPS navigation")
                    
                    # Calculate navigation parameters based on mode
                    if self.current_mode == self.MODE_GPS_NAVIGATION:
                        if nav_error is not None and nav_distance is not None:
                            speed, radius = self.calculate_navigation_speed_radius(nav_error, nav_distance)
                            print(f"GPS Nav - Error: {nav_error:.3f}, Distance: {nav_distance:.2f}m, Speed: {speed:.2f}, Radius: {radius:.2f}")
                        else:
                            print("GPS navigation data not available")
                            speed, radius = 0, 1.0
                    else:
                        if camera_distance and obstacle_info and obstacle_info.get('lidar_confirmed', False):
                            effective_min_dist = camera_distance
                            print(f"Using camera-detected object distance: {effective_min_dist:.2f}m")
                        else:
                            effective_min_dist = lidar_min_dist
                            print(f"Using lidar minimum distance: {effective_min_dist:.2f}m")
                        
                        if effective_min_dist and effective_min_dist <= self.stop_distance:
                            print(f"Emergency stop - Obstacle at {effective_min_dist:.2f}m")
                            self.stop_robot()
                            time.sleep(0.1)
                            print("Reversing...")
                            self.send_command(Commands["reverse"], 20)
                            time.sleep(1.5)
                            continue
                        
                        if gap_angle is not None and effective_min_dist:
                            speed, radius = self.calculate_avoidance_speed_radius(gap_angle, effective_min_dist)
                            print(f"Avoidance - Gap angle: {gap_angle:.3f}, Min dist: {effective_min_dist:.2f}m, Speed: {speed:.2f}, Radius: {radius:.2f}")
                        else:
                            print("Avoidance data not available - stopping")
                            speed, radius = 0, 1.0
                    
                    # Send movement command
                    if speed <= 0:
                        self.stop_robot()
                    elif radius > 2.0:
                        self.send_command(Commands["drive_straight"], speed)
                    else:
                        if self.current_mode == self.MODE_GPS_NAVIGATION:
                            turn_radius = radius if nav_error >= 0 else -radius
                        else:
                            turn_radius = radius if gap_angle >= 0 else -radius
                        print("We ARE turning")
                        self.send_command(Commands["turn_while_moving"], turn_radius, speed)
                    
                    time.sleep(0.1)
                    
                except Exception as e:
                    print(f"Error in navigation loop: {e}")
                    self.stop_robot()
                    time.sleep(0.5)
                    
        finally:
            # Ensure recording stops when navigation ends
            if self.video_recorder and self.video_recorder.is_recording():
                self.stop_recording()

    def get_status(self):
        """Get current navigation status including recording info"""
        status = {
            'mode': 'GPS_NAVIGATION' if self.current_mode == self.MODE_GPS_NAVIGATION else 'OBSTACLE_AVOIDANCE',
            'base_speed': self.base_speed,
            'safe_distance': self.safe_distance,
            'camera_trigger_distance': self.camera_detection_distance,
            'recording_enabled': self.enable_recording,
            'currently_recording': self.video_recorder.is_recording() if self.video_recorder else False,
            'current_video_file': self.video_recorder.get_current_filename() if self.video_recorder else None
        }
        
        # Add camera status if available
        if hasattr(self.camera, 'get_status'):
            status.update(self.camera.get_status())
            
        return status


# Example usage and helper functions
def create_navigator_with_recording(base_speed, ftg_navigator, waypoint_navigator, camera, ser):
    """Create a navigator with video recording enabled"""
    return HybridNavigator(
        base_speed=base_speed,
        ftg_navigator=ftg_navigator,
        waypoint_navigator=waypoint_navigator,
        camera=camera,
        ser=ser,
        enable_recording=True,
        recording_dir="robot_recordings"
    )

def manual_recording_controls(navigator):
    """Example function showing manual recording controls"""
    print("\nRecording Controls:")
    print("1. Start recording: navigator.start_recording('custom_session_name')")
    print("2. Stop recording: navigator.stop_recording()")
    print("3. Toggle recording: navigator.toggle_recording()")
    print("4. Check if recording: navigator.video_recorder.is_recording()")
    print("5. Get current filename: navigator.video_recorder.get_current_filename()")