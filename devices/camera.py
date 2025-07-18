import cv2
import numpy as np
import threading
from threading import Thread
import time
import os
from datetime import datetime

class Camera:
    def __init__(self, camera_id=0, width=640, height=480, fps=30, auto_record=True):
        self.camera_id = camera_id
        self.width = width
        self.height = height
        self.fps = fps
        self.auto_record = auto_record  # New parameter to control automatic recording
        self.cap = None
        self.latest_frame = None
        self.detected_objects = []
        self.lock = threading.Lock()
        self.running = False
        
        # Video recording variables
        self.video_writer = None
        self.recording = False
        self.video_filename = None
        self.videos_dir = "videos"
        
        # Ensure videos directory exists
        self._ensure_videos_directory()
        
        # Initialize object detection
        self.net = None
        self.output_layers = None
        self.classes = []
        self.colors = []
        
        # Load YOLO model (you'll need to download these files)
        self.load_yolo_model()
        self.initialize_camera()
    
    def _ensure_videos_directory(self):
        """Ensure the videos directory exists"""
        try:
            os.makedirs(self.videos_dir, exist_ok=True)
            print(f"Videos directory ready: {os.path.abspath(self.videos_dir)}")
        except Exception as e:
            print(f"Warning: Could not create videos directory: {e}")
            # Fallback to current directory
            self.videos_dir = "."
    
    def is_running(self):
        """Check if the camera is currently running and capturing frames"""
        return self.running and self.cap is not None and self.cap.isOpened()

    def is_recording(self):
        """Check if currently recording video"""
        return self.recording and self.video_writer is not None

    def get_camera_status(self):
        """Get detailed camera status information"""
        status = {
            'running': self.running,
            'recording': self.recording,
            'video_filename': self.video_filename,
            'camera_initialized': self.cap is not None,
            'camera_opened': self.cap.isOpened() if self.cap else False,
            'has_latest_frame': self.latest_frame is not None,
            'objects_detected': len(self.detected_objects),
            'yolo_loaded': self.net is not None,
            'videos_directory': os.path.abspath(self.videos_dir),
            'auto_record': self.auto_record
        }
        return status

    def start_recording(self, filename=None):
        """Start recording video to file"""
        if self.recording:
            print("Already recording. Stop current recording first.")
            return False
        
        if filename is None:
            # Generate filename with current date and time
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            filename = f"recording_{timestamp}.mp4"
        
        # Ensure filename doesn't already exist
        counter = 1
        base_name = filename.replace('.mp4', '')
        while os.path.exists(os.path.join(self.videos_dir, filename)):
            filename = f"{base_name}_{counter}.mp4"
            counter += 1
        
        self.video_filename = os.path.join(self.videos_dir, filename)
        
        # Define codec and create VideoWriter
        fourcc = cv2.VideoWriter_fourcc(*'mp4v')
        self.video_writer = cv2.VideoWriter(
            self.video_filename, 
            fourcc, 
            self.fps, 
            (self.width, self.height)
        )
        
        if not self.video_writer.isOpened():
            print(f"Error: Could not open video writer for {self.video_filename}")
            return False
        
        self.recording = True
        print(f"Started recording to: {self.video_filename}")
        return True

    def stop_recording(self):
        """Stop recording video"""
        if not self.recording:
            print("Not currently recording.")
            return False
        
        self.recording = False
        if self.video_writer:
            self.video_writer.release()
            self.video_writer = None
        
        print(f"Stopped recording. Video saved to: {self.video_filename}")
        return True

    def load_yolo_model(self):
        """Load YOLO model for object detection"""
        try:
            import os
            
            # Check if YOLO files exist
            yolo_files = ["yolov3.weights", "yolov3.cfg", "coco.names"]
            missing_files = [f for f in yolo_files if not os.path.exists(f)]
            
            if missing_files:
                print(f"Missing YOLO files: {missing_files}")
                print("Download them with:")
                print("  wget https://pjreddie.com/media/files/yolov3.weights")
                print("  wget https://raw.githubusercontent.com/pjreddie/darknet/master/cfg/yolov3.cfg")
                print("  wget https://raw.githubusercontent.com/pjreddie/darknet/master/data/coco.names")
                print("Using enhanced basic detection instead")
                return
            
            # Load YOLO model
            self.net = cv2.dnn.readNet("yolov3.weights", "yolov3.cfg")
            layer_names = self.net.getLayerNames()
            self.output_layers = [layer_names[i[0] - 1] for i in self.net.getUnconnectedOutLayers()]
            
            # Load class names
            with open("coco.names", "r") as f:
                self.classes = [line.strip() for line in f.readlines()]
            
            # Generate colors for each class
            self.colors = np.random.uniform(0, 255, size=(len(self.classes), 3))
            print("YOLO model loaded successfully")
        except Exception as e:
            print(f"Could not load YOLO model: {e}")
            print("Using enhanced basic detection instead")
    
    def initialize_camera(self):
        """Initialize camera connection"""
        self.cap = cv2.VideoCapture(self.camera_id)
        if not self.cap.isOpened():
            raise Exception(f"Could not open camera {self.camera_id}")
        
        self.cap.set(cv2.CAP_PROP_FRAME_WIDTH, self.width)
        self.cap.set(cv2.CAP_PROP_FRAME_HEIGHT, self.height)
        self.cap.set(cv2.CAP_PROP_FPS, self.fps)
        print(f"Camera initialized: {self.width}x{self.height} @ {self.fps}fps")
    
    def detect_objects_yolo(self, frame):
        """Detect objects using YOLO"""
        if self.net is None:
            return []
        
        height, width, channels = frame.shape
        
        # Prepare image for YOLO
        blob = cv2.dnn.blobFromImage(frame, 0.00392, (416, 416), (0, 0, 0), True, crop=False)
        self.net.setInput(blob)
        outputs = self.net.forward(self.output_layers)
        
        # Process detections
        boxes = []
        confidences = []
        class_ids = []
        
        for output in outputs:
            for detection in output:
                scores = detection[5:]
                class_id = np.argmax(scores)
                confidence = scores[class_id]
                
                if confidence > 0.5:  # Confidence threshold
                    center_x = int(detection[0] * width)
                    center_y = int(detection[1] * height)
                    w = int(detection[2] * width)
                    h = int(detection[3] * height)
                    
                    x = int(center_x - w / 2)
                    y = int(center_y - h / 2)
                    
                    boxes.append([x, y, w, h])
                    confidences.append(float(confidence))
                    class_ids.append(class_id)
        
        # Apply non-maximum suppression
        indexes = cv2.dnn.NMSBoxes(boxes, confidences, 0.5, 0.4)
        
        detected_objects = []
        if len(indexes) > 0:
            for i in indexes.flatten():
                x, y, w, h = boxes[i]
                label = str(self.classes[class_ids[i]])
                confidence = confidences[i]
                
                detected_objects.append({
                    'label': label,
                    'confidence': confidence,
                    'bbox': (x, y, w, h),
                    'center': (x + w // 2, y + h // 2)
                })
        
        return detected_objects
    
    def detect_objects_simple(self, frame):
        """Enhanced object detection using multiple methods (fallback when YOLO not available)"""
        detected_objects = []
        
        # Method 1: Motion detection (if we have a previous frame)
        if hasattr(self, 'prev_frame') and self.prev_frame is not None:
            motion_objects = self._detect_motion(frame, self.prev_frame)
            detected_objects.extend(motion_objects)
        
        # Method 2: Color-based detection (detect bright/distinct objects)
        color_objects = self._detect_by_color(frame)
        detected_objects.extend(color_objects)
        
        # Method 3: Edge-based detection
        edge_objects = self._detect_by_edges(frame)
        detected_objects.extend(edge_objects)
        
        # Store current frame for next motion detection
        self.prev_frame = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
        
        # Remove duplicate detections (simple overlap check)
        detected_objects = self._remove_overlapping_detections(detected_objects)
        
        return detected_objects
    
    def _detect_motion(self, current_frame, prev_frame):
        """Detect moving objects"""
        current_gray = cv2.cvtColor(current_frame, cv2.COLOR_BGR2GRAY)
        diff = cv2.absdiff(current_gray, prev_frame)
        
        # Threshold the difference
        _, thresh = cv2.threshold(diff, 30, 255, cv2.THRESH_BINARY)
        
        # Dilate to fill gaps
        kernel = np.ones((5, 5), np.uint8)
        dilated = cv2.dilate(thresh, kernel, iterations=2)
        
        # Find contours
        contours, _ = cv2.findContours(dilated, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
        
        objects = []
        for contour in contours:
            area = cv2.contourArea(contour)
            if area > 800:  # Minimum area for motion
                x, y, w, h = cv2.boundingRect(contour)
                objects.append({
                    'label': 'moving_object',
                    'confidence': 0.8,
                    'bbox': (x, y, w, h),
                    'center': (x + w // 2, y + h // 2),
                    'area': area
                })
        
        return objects
    
    def _detect_by_color(self, frame):
        """Detect objects by distinctive colors"""
        objects = []
        
        # Convert to HSV for better color detection
        hsv = cv2.cvtColor(frame, cv2.COLOR_BGR2HSV)
        
        # Define color ranges for common objects
        color_ranges = {
            'red_object': [
                (np.array([0, 50, 50]), np.array([10, 255, 255])),
                (np.array([170, 50, 50]), np.array([180, 255, 255]))
            ],
            'blue_object': [(np.array([100, 50, 50]), np.array([130, 255, 255]))],
            'green_object': [(np.array([40, 50, 50]), np.array([80, 255, 255]))],
            'yellow_object': [(np.array([20, 50, 50]), np.array([30, 255, 255]))]
        }
        
        for color_name, ranges in color_ranges.items():
            mask = np.zeros(hsv.shape[:2], dtype=np.uint8)
            for lower, upper in ranges:
                color_mask = cv2.inRange(hsv, lower, upper)
                mask = cv2.bitwise_or(mask, color_mask)
            
            # Clean up the mask
            kernel = np.ones((5, 5), np.uint8)
            mask = cv2.morphologyEx(mask, cv2.MORPH_CLOSE, kernel)
            mask = cv2.morphologyEx(mask, cv2.MORPH_OPEN, kernel)
            
            # Find contours
            contours, _ = cv2.findContours(mask, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
            
            for contour in contours:
                area = cv2.contourArea(contour)
                if area > 500:
                    x, y, w, h = cv2.boundingRect(contour)
                    objects.append({
                        'label': color_name,
                        'confidence': 0.7,
                        'bbox': (x, y, w, h),
                        'center': (x + w // 2, y + h // 2),
                        'area': area
                    })
        
        return objects
    
    def _detect_by_edges(self, frame):
        """Detect objects using edge detection"""
        # Convert to grayscale
        gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
        
        # Apply Gaussian blur
        blurred = cv2.GaussianBlur(gray, (5, 5), 0)
        
        # Edge detection
        edges = cv2.Canny(blurred, 50, 150)
        
        # Dilate edges to connect nearby edges
        kernel = np.ones((3, 3), np.uint8)
        dilated = cv2.dilate(edges, kernel, iterations=2)
        
        # Find contours
        contours, _ = cv2.findContours(dilated, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
        
        objects = []
        for contour in contours:
            area = cv2.contourArea(contour)
            if area > 1000:  # Minimum area threshold
                x, y, w, h = cv2.boundingRect(contour)
                
                # Calculate aspect ratio to filter out thin lines
                aspect_ratio = w / h if h > 0 else 0
                if 0.3 < aspect_ratio < 3.0:  # Reasonable aspect ratio
                    objects.append({
                        'label': 'edge_object',
                        'confidence': 0.6,
                        'bbox': (x, y, w, h),
                        'center': (x + w // 2, y + h // 2),
                        'area': area
                    })
        
        return objects
    
    def _remove_overlapping_detections(self, objects):
        """Remove overlapping detections (simple version)"""
        if len(objects) < 2:
            return objects
        
        # Sort by area (largest first)
        objects.sort(key=lambda x: x['area'], reverse=True)
        
        filtered = []
        for obj in objects:
            x1, y1, w1, h1 = obj['bbox']
            overlaps = False
            
            for filtered_obj in filtered:
                x2, y2, w2, h2 = filtered_obj['bbox']
                
                # Check for overlap
                if (x1 < x2 + w2 and x1 + w1 > x2 and 
                    y1 < y2 + h2 and y1 + h1 > y2):
                    overlaps = True
                    break
            
            if not overlaps:
                filtered.append(obj)
        
        return filtered
    
    def _draw_detections_on_frame(self, frame, objects):
        """Draw bounding boxes and labels on frame"""
        for obj in objects:
            x, y, w, h = obj['bbox']
            label = obj['label']
            confidence = obj['confidence']
            
            # Choose color based on label
            if self.net is not None and label in self.classes:
                color = self.colors[self.classes.index(label)]
            else:
                # Default colors for simple detection
                color_map = {
                    'moving_object': (0, 255, 0),
                    'red_object': (0, 0, 255),
                    'blue_object': (255, 0, 0),
                    'green_object': (0, 255, 0),
                    'yellow_object': (0, 255, 255),
                    'edge_object': (128, 128, 128)
                }
                color = color_map.get(label, (255, 255, 255))
            
            # Draw bounding box
            cv2.rectangle(frame, (x, y), (x + w, y + h), color, 2)
            
            # Draw label
            label_text = f"{label}: {confidence:.2f}"
            cv2.putText(frame, label_text, (x, y - 10), 
                       cv2.FONT_HERSHEY_SIMPLEX, 0.5, color, 2)
        
        return frame
    
    def _capture_loop(self):
        """Main capture loop running in separate thread"""
        while self.running:
            ret, frame = self.cap.read()
            if not ret:
                print("Failed to capture frame")
                continue
            
            # Detect objects
            if self.net is not None:
                objects = self.detect_objects_yolo(frame)
            else:
                objects = self.detect_objects_simple(frame)
            
            # Record frame with detections if recording is active
            if self.recording and self.video_writer:
                frame_with_detections = self._draw_detections_on_frame(frame.copy(), objects)
                self.video_writer.write(frame_with_detections)
            
            # Update shared data
            with self.lock:
                self.latest_frame = frame.copy()
                self.detected_objects = objects
            
            time.sleep(1.0 / self.fps)  # Control frame rate
    
    def start(self):
        """Start camera capture and object detection"""
        if not self.cap or not self.cap.isOpened():
            self.initialize_camera()
        
        self.running = True
        self.capture_thread = Thread(target=self._capture_loop, daemon=True)
        self.capture_thread.start()
        print("Camera started")
        
        # Auto-start recording if enabled
        if self.auto_record:
            if self.start_recording():
                print("Auto-recording started - videos will be saved automatically")
            else:
                print("Warning: Auto-recording failed to start")
    
    def stop(self):
        """Stop camera capture and recording"""
        self.running = False
        
        # Stop recording if active
        if self.recording:
            self.stop_recording()
        
        if self.cap:
            self.cap.release()
        print("Camera stopped")
    
    def get_frame(self):
        """Get the latest frame"""
        with self.lock:
            return self.latest_frame.copy() if self.latest_frame is not None else None
    
    def get_objects(self):
        """Get detected objects from latest frame"""
        with self.lock:
            return self.detected_objects.copy()
    
    def get_frame_with_detections(self):
        """Get frame with bounding boxes drawn around detected objects"""
        with self.lock:
            if self.latest_frame is None:
                return None
            
            frame = self.latest_frame.copy()
            return self._draw_detections_on_frame(frame, self.detected_objects)
    
    def find_objects_by_label(self, target_label):
        """Find specific objects by label"""
        with self.lock:
            return [obj for obj in self.detected_objects if obj['label'].lower() == target_label.lower()]
    
    def get_closest_object(self):
        """Get the closest object (largest bounding box area)"""
        with self.lock:
            if not self.detected_objects:
                return None
            
            largest_obj = max(self.detected_objects, key=lambda obj: obj['bbox'][2] * obj['bbox'][3])
            return largest_obj
  
    def list_recorded_videos(self):
        """List all recorded videos in the videos directory"""
        if not os.path.exists(self.videos_dir):
            return []
        
        videos = [f for f in os.listdir(self.videos_dir) if f.endswith('.mp4')]
        videos.sort(reverse=True)  # Most recent first
        return videos

# Example usage (headless mode)
if __name__ == "__main__":
    # Camera will automatically start recording when started
    camera = Camera(auto_record=True)
    
    try:
        camera.start()
        print("Camera started with automatic recording enabled (headless mode)")
        print(f"Videos are being saved to: {camera.videos_dir}")
        print("Press Ctrl+C to stop")
        
        while True:
            # Get detected objects
            objects = camera.get_objects()
            status = camera.get_camera_status()
            
            if objects:
                print(f"Detected {len(objects)} objects:")
                for obj in objects:
                    print(f"  - {obj['label']}: {obj['confidence']:.2f} at {obj['center']}")
            
            # Show status periodically (every 30 seconds)
            if int(time.time()) % 30 == 0:
                print(f"Recording status: {'Recording' if camera.is_recording() else 'Not recording'}")
                print(f"Total videos: {len(camera.list_recorded_videos())}")
            
            time.sleep(1.0)  # Check every second
    
    except KeyboardInterrupt:
        print("\nStopping...")
    finally:
        camera.stop()
        print("Final recorded videos:", camera.list_recorded_videos())