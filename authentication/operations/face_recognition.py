# face_recognition.py
import os
import cv2
import numpy as np

class FaceRecognition:
    def __init__(self):
        """Initialize the face recognition component"""
        # Face detection
        self.face_cascade = cv2.CascadeClassifier(cv2.data.haarcascades + 'haarcascade_frontalface_default.xml')
        # Face recognition with optimized parameters
        self.face_recognizer = cv2.face.LBPHFaceRecognizer_create(
            radius=1,
            neighbors=8,
            grid_x=8,
            grid_y=8,
            threshold=80.0
        )
        self.confidence_threshold = 0.6
        print("Face Recognition Initialized")

    def train_recognizer(self):
        """Train the face recognizer with current faces_data"""
        if hasattr(self, 'faces_data') and len(self.faces_data['faces']) > 0:
            try:
                print("Training face recognition model...")
                faces_array = np.array(self.faces_data['faces'])
                labels_array = np.array(self.faces_data['labels'])
                self.face_recognizer.train(faces_array, labels_array)
                print("Training completed!")
                return True
            except Exception as e:
                print(f"Error training recognizer: {e}")
                return False
        else:
            print("No face data available for training")
            return False

    

    def recognize_face(self, face_roi):
        """Recognize a face and return user_id and confidence with improved preprocessing"""
        if not hasattr(self, 'faces_data') or len(self.faces_data['faces']) == 0:
            return None, 0
        try:
            # Preprocess face the same way as during training
            face_roi = cv2.resize(face_roi, (100, 100))
            face_roi = cv2.GaussianBlur(face_roi, (3, 3), 0)
            face_roi = cv2.equalizeHist(face_roi)
            user_id, confidence = self.face_recognizer.predict(face_roi)
            # LBPH confidence: lower is better, convert to similarity percentage
            # Typical range: 0-100, where 0 is perfect match
            if confidence < 100:
                similarity = max(0, (100 - confidence) / 100.0)
            else:
                similarity = 0
            # Debug output
            print(f"Recognition result - User ID: {user_id}, Raw confidence: {confidence:.2f}, Similarity: {similarity:.3f} ({similarity*100:.1f}%)")
            return user_id, similarity
        except Exception as e:
            print(f"Error in face recognition: {e}")
            return None, 0

    def capture_user_faces(self, user_id, num_samples=100):
        """Capture face samples for a specific user with improved quality"""
        if user_id not in self.users:
            print(f"User ID {user_id} not found")
            return False
        user_name = self.users[user_id]['name']
        print(f"Capturing face samples for {user_name}")
        print("IMPORTANT INSTRUCTIONS:")
        print("1. Look directly at the camera")
        print("2. Keep your face well-lit and clearly visible")
        print("3. Slowly move your head left/right and up/down")
        print("4. Try different expressions (smile, neutral, etc.)")
        print("5. Ensure good lighting from front")
        print("Press SPACE to capture samples, 'q' to finish early")
        cap = cv2.VideoCapture(0, cv2.CAP_DSHOW)
        cap.set(cv2.CAP_PROP_FRAME_WIDTH, 640)
        cap.set(cv2.CAP_PROP_FRAME_HEIGHT, 480)
        samples_captured = 0
        capture_mode = False
        while samples_captured < num_samples:
            ret, frame = cap.read()
            if not ret:
                break
            frame = cv2.flip(frame, 1)
            gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
            # Apply histogram equalization for better face detection
            gray = cv2.equalizeHist(gray)
            faces = self.face_cascade.detectMultiScale(
                gray, 
                scaleFactor=1.1, 
                minNeighbors=5, 
                minSize=(120, 120),  # Larger minimum size
                maxSize=(300, 300)   # Maximum size to avoid very large faces
            )
            for (x, y, w, h) in faces:
                # Only capture if in capture mode (SPACE pressed)
                if capture_mode and len(faces) == 1:  # Only one face visible
                    # Extract and preprocess face
                    face_roi = gray[y:y+h, x:x+w]
                    # Resize to consistent size
                    face_roi = cv2.resize(face_roi, (100, 100))
                    # Apply Gaussian blur to reduce noise
                    face_roi = cv2.GaussianBlur(face_roi, (3, 3), 0)
                    # Normalize lighting
                    face_roi = cv2.equalizeHist(face_roi)
                    # Store face data
                    self.faces_data['faces'].append(face_roi)
                    self.faces_data['labels'].append(user_id)
                    self.faces_data['user_ids'].append(user_id)
                    samples_captured += 1
                    capture_mode = False  # Reset capture mode
                    print(f"Sample {samples_captured} captured!")
                # Visual feedback
                color = (0, 255, 0) if len(faces) == 1 else (0, 255, 255)
                cv2.rectangle(frame, (x, y), (x+w, y+h), color, 2)
                # Face quality indicators
                face_roi = gray[y:y+h, x:x+w]
                brightness = np.mean(face_roi)
                cv2.putText(frame, f'Brightness: {brightness:.0f}', (x, y-30),
                           cv2.FONT_HERSHEY_SIMPLEX, 0.5, color, 1)
            # Instructions and status
            cv2.putText(frame, f'Capturing for: {user_name}', (10, 30),
                       cv2.FONT_HERSHEY_SIMPLEX, 0.7, (255, 255, 255), 2)
            cv2.putText(frame, f'Samples: {samples_captured}/{num_samples}', (10, 60),
                       cv2.FONT_HERSHEY_SIMPLEX, 0.7, (255, 255, 255), 2)
            # Status messages
            if len(faces) == 0:
                cv2.putText(frame, 'No face detected', (10, 90),
                           cv2.FONT_HERSHEY_SIMPLEX, 0.6, (0, 0, 255), 2)
            elif len(faces) > 1:
                cv2.putText(frame, 'Multiple faces - ensure only you are visible', (10, 90),
                           cv2.FONT_HERSHEY_SIMPLEX, 0.6, (0, 255, 255), 2)
            else:
                cv2.putText(frame, 'Press SPACE to capture sample', (10, 90),
                           cv2.FONT_HERSHEY_SIMPLEX, 0.6, (0, 255, 0), 2)
            cv2.imshow('Face Capture', frame)
            key = cv2.waitKey(1) & 0xFF
            if key == ord('q'):
                break
            elif key == ord(' '):  # Spacebar to capture
                capture_mode = True
        cap.release()
        cv2.destroyAllWindows()
        # Retrain the recognizer with better parameters
        if len(self.faces_data['faces']) > 0:
            faces_array = np.array(self.faces_data['faces'])
            labels_array = np.array(self.faces_data['labels'])
            print("Training face recognition model...")
            self.face_recognizer.train(faces_array, labels_array)
            print("Training completed!")

        if samples_captured > 0:
            self.train_recognizer()  # Call the training method
        
        return True

    def process_faces(self, frame, faces):
        gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
        gray = cv2.equalizeHist(gray)  # Improve lighting consistency
        for (x, y, w, h) in faces:
            # Extract face region with some padding
            padding = 10
            y1 = max(0, y - padding)
            y2 = min(gray.shape[0], y + h + padding)
            x1 = max(0, x - padding)
            x2 = min(gray.shape[1], x + w + padding)
            face_roi = gray[y1:y2, x1:x2]

            # Skip if face is too small or too large
            if face_roi.shape[0] < 50 or face_roi.shape[1] < 50:
                continue

            # Recognize face
            user_id, confidence = self.recognize_face(face_roi)

            # Check if recognized with sufficient confidence
            is_recognized = (user_id is not None and 
                            user_id in self.users and 
                            confidence >= self.confidence_threshold)

            if is_recognized:
                # Recognized user with sufficient confidence
                user_name = self.users[user_id]['name']
                color = (0, 255, 0)  # Green for recognized
                cv2.rectangle(frame, (x, y), (x+w, y+h), color, 3)
                cv2.putText(frame, f'{user_name}', (x, y-10),
                        cv2.FONT_HERSHEY_SIMPLEX, 0.8, color, 2)
                cv2.putText(frame, f'Conf: {confidence*100:.1f}%', (x, y+h+20),
                        cv2.FONT_HERSHEY_SIMPLEX, 0.5, color, 1)
                cv2.putText(frame, 'AUTHORIZED', (x, y+h+35),
                        cv2.FONT_HERSHEY_SIMPLEX, 0.5, color, 2)

                # Unlock the door if it's currently locked
                if self.is_locked:
                    print(f"[DEBUG] Unlocking door for {user_name}")
                    self.unlock_door(user_id, confidence)
            else:
                # Unknown face or confidence too low
                color = (0, 0, 255)  # Red for unknown/low confidence
                cv2.rectangle(frame, (x, y), (x+w, y+h), color, 2)
                if user_id and user_id in self.users:
                    user_name = self.users[user_id]['name']
                    cv2.putText(frame, f'{user_name}?', (x, y-10),
                            cv2.FONT_HERSHEY_SIMPLEX, 0.7, color, 2)
                    cv2.putText(frame, f'Low: {confidence*100:.1f}%', (x, y+h+20),
                            cv2.FONT_HERSHEY_SIMPLEX, 0.5, color, 1)
                    cv2.putText(frame, f'Need ≥{self.confidence_threshold*100:.0f}%', (x, y+h+35),
                            cv2.FONT_HERSHEY_SIMPLEX, 0.4, color, 1)
                else:
                    cv2.putText(frame, 'Unknown', (x, y-10),
                            cv2.FONT_HERSHEY_SIMPLEX, 0.7, color, 2)
                    cv2.putText(frame, f'Conf: {confidence*100:.1f}% if confidence else 0:.1f %', (x, y+h+20),
                            cv2.FONT_HERSHEY_SIMPLEX, 0.5, color, 1)
                    cv2.putText(frame, 'ACCESS DENIED', (x, y+h+35),
                            cv2.FONT_HERSHEY_SIMPLEX, 0.5, color, 2)
        return frame