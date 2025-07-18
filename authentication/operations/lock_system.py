# lock_system.py
import os
import threading
import time
import cv2

class LockSystem:
    def __init__(self, confidence_threshold=0.6, lock_timeout=5):
        """Initialize the lock system component"""
        self.confidence_threshold = confidence_threshold
        self.lock_timeout = lock_timeout
        # Lock state
        self.is_locked = True
        self.lock_timer = None
        self.current_user = None
        # Performance tracking
        self.fps_counter = 0
        self.fps_start_time = time.time()
        self.current_fps = 0
        print("Lock System Initialized")
        print(f"Confidence threshold set to: {confidence_threshold*100}%")

    def unlock_door(self, user_id, confidence):
        """Unlock the door for a specific user"""
        if hasattr(self, 'users') and user_id in self.users:
            self.is_locked = False
            self.current_user = user_id
            user_name = self.users[user_id]['name']
            print(f"🔓 DOOR UNLOCKED for {user_name} (Confidence: {confidence*100:.1f}%)")
            # Log successful access
            self.log_access(user_id, True, confidence)
            # Set timer to automatically lock again
            if self.lock_timer:
                self.lock_timer.cancel()
            self.lock_timer = threading.Timer(self.lock_timeout, self.lock_door)
            self.lock_timer.start()
            return True
        return False

    def lock_door(self):
        """Lock the door"""
        self.is_locked = True
        self.current_user = None
        print("🔒 DOOR LOCKED")

    def manual_lock(self):
        """Manually lock the door"""
        if self.lock_timer:
            self.lock_timer.cancel()
        self.lock_door()

    def calculate_fps(self):
        """Calculate FPS for performance monitoring"""
        self.fps_counter += 1
        if self.fps_counter >= 10:
            end_time = time.time()
            self.current_fps = self.fps_counter / (end_time - self.fps_start_time)
            self.fps_counter = 0
            self.fps_start_time = time.time()

    def draw_lock_interface(self, frame, faces):
        """Draw the lock interface overlay with proper colors"""
        height, width = frame.shape[:2]
        # Lock status with proper colors
        if self.is_locked:
            lock_color = (0, 0, 255)  # Red for locked
            lock_text = ":O LOCKED"
        else:
            lock_color = (0, 255, 0)  # Green for unlocked
            lock_text = "=^.^= UNLOCKED"

        # Draw status box with proper colors
        cv2.rectangle(frame, (10, 10), (350, 120), (0, 0, 0), -1)  # Black background
        cv2.rectangle(frame, (10, 10), (350, 120), lock_color, 3)  # Colored border
        cv2.putText(frame, lock_text, (20, 40),
                cv2.FONT_HERSHEY_SIMPLEX, 0.8, lock_color, 2)
        # Show confidence threshold
        cv2.putText(frame, f"Threshold: {self.confidence_threshold*100:.0f}%", (20, 65),
                cv2.FONT_HERSHEY_SIMPLEX, 0.5, (255, 255, 255), 1)

        # Show current user if unlocked
        if not self.is_locked and self.current_user:
            user_name = self.users[self.current_user]['name']
            cv2.putText(frame, f"Welcome, {user_name}", (20, 90),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.6, (0, 255, 0), 2)

        # System info (Change color to black)
        cv2.putText(frame, f'FPS: {self.current_fps:.1f}', (width - 150, 30),
                cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0, 0, 0), 1)  # Changed to black
        cv2.putText(frame, f'Users: {len(self.users)}', (width - 150, 50),
                cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0, 0, 0), 1)  # Changed to black
        cv2.putText(frame, f'Faces: {len(faces)}', (width - 150, 70),
                cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0, 0, 0), 1)  # Changed to black

        # Instructions
        cv2.putText(frame, "Press 'l' to lock manually, 'q' to quit", (10, height - 20),
                cv2.FONT_HERSHEY_SIMPLEX, 0.5, (255, 255, 255), 1)

        return frame

    def run_lock_system(self):
        """Run the main face recognition lock system"""
        cap = cv2.VideoCapture(0, cv2.CAP_DSHOW)
        cap.set(cv2.CAP_PROP_FRAME_WIDTH, 640)
        cap.set(cv2.CAP_PROP_FRAME_HEIGHT, 480)
        if not cap.isOpened():
            print("Error: Could not open camera")
            return
        print("Face Recognition Lock System Active")
        print(f"Confidence threshold: {self.confidence_threshold*100}%")
        print("Press 'l' to lock manually, 'q' to quit")
        while True:
            ret, frame = cap.read()
            if not ret:
                break
            frame = cv2.flip(frame, 1)
            gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
            # Detect faces
            faces = self.face_cascade.detectMultiScale(
                gray, 1.3, 5, minSize=(100, 100)
            )
            # Process faces for recognition
            frame = self.process_faces(frame, faces)
            # Draw interface
            frame = self.draw_lock_interface(frame, faces)
            # Calculate FPS
            self.calculate_fps()
            # Display frame
            cv2.imshow('Face Recognition Lock', frame)
            # Handle key presses
            key = cv2.waitKey(1) & 0xFF
            if key == ord('q'):
                break
            elif key == ord('l'):
                self.manual_lock()
        # Cleanup
        cap.release()
        cv2.destroyAllWindows()
        if self.lock_timer:
            self.lock_timer.cancel()