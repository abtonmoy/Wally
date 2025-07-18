# main.py

from operations.face_recognition import FaceRecognition
from operations.data_management import DataManager
from operations.lock_system import LockSystem
import cv2
import os
import json
import atexit
import signal
import sys


class FaceRecognitionLock(FaceRecognition, DataManager, LockSystem):
    def __init__(self, confidence_threshold=0.3, lock_timeout=10):
        """Initialize the complete face recognition lock system"""
        # Initialize parent classes
        FaceRecognition.__init__(self)
        DataManager.__init__(self)
        LockSystem.__init__(self, confidence_threshold, lock_timeout)
        

        # Train recognizer after loading data
        self.train_recognizer()
        print("Face recognizer initialized with training data")
        # Register cleanup function to save data on exit
        atexit.register(self.cleanup_on_exit)
        
        # Register signal handlers for graceful shutdown
        signal.signal(signal.SIGINT, self.signal_handler)
        signal.signal(signal.SIGTERM, self.signal_handler)

        print(f"\nFace Recognition Lock System Initialized")
        print(f"Confidence threshold set to: {confidence_threshold * 100}%")
        print(f"Registered users: {len(self.users)}")

    def cleanup_on_exit(self):
        """Ensure data is saved when program exits"""
        print("\nSaving data before exit...")
        self.save_data()
        print("Data saved successfully!")

    def signal_handler(self, signum, frame):
        """Handle system signals for graceful shutdown"""
        print(f"\nReceived signal {signum}, shutting down gracefully...")
        self.cleanup_on_exit()
        sys.exit(0)

    def capture_user_faces(self, user_id, num_samples=100):
        """Override to ensure data is saved after capturing faces"""
        result = super().capture_user_faces(user_id, num_samples)
        if result:
            print("Saving face data...")
            self.save_data()
            print("Face data saved successfully!")
        return result

    def run_lock_system(self):
        """Override to ensure data is saved after running lock system"""
        try:
            super().run_lock_system()
        except KeyboardInterrupt:
            print("\nLock system interrupted by user")
        except Exception as e:
            print(f"Error in lock system: {e}")
        finally:
            print("Saving data...")
            self.save_data()
            print("Data saved!")


def setup_system():
    """Setup the face recognition lock system"""
    lock_system = None
    
    try:
        lock_system = FaceRecognitionLock(
            confidence_threshold=0.3,  # Set to 30% confidence threshold
            lock_timeout=10            # Seconds to keep door unlocked
        )

        while True:
            print("\n" + "="*50)
            print("FACE RECOGNITION LOCK SYSTEM - 30% CONFIDENCE")
            print("="*50)
            print("1. Add new user")
            print("2. Capture face samples for user")
            print("3. Start lock system")
            print("4. View users")
            print("5. View access logs")
            print("6. Delete user")
            print("7. Save data manually")
            print("8. View system statistics")
            print("9. Export logs to CSV")
            print("10. Clean up orphaned data")
            print("11. Exit")
            
            try:
                choice = input("Select option (1-11): ").strip()
            except KeyboardInterrupt:
                print("\nExiting...")
                break

            if choice == '1':
                try:
                    name = input("Enter user name: ").strip()
                    if not name:
                        print("Name cannot be empty")
                        continue
                    is_admin = input("Is admin user? (y/n): ").lower().strip() == 'y'
                    user_id = lock_system.add_user(name, is_admin)
                    print(f"User added with ID: {user_id}")
                    # Data is already saved in add_user method
                except KeyboardInterrupt:
                    print("\nOperation cancelled")
                    continue

            elif choice == '2':
                if not lock_system.users:
                    print("No users found. Add a user first.")
                    continue
                print("Available users:")
                for uid, user in lock_system.users.items():
                    sample_count = lock_system.get_face_sample_count(uid)
                    print(f"  {uid}: {user['name']} ({sample_count} samples)")
                
                try:
                    user_id = int(input("Enter user ID to capture faces: "))
                    if user_id in lock_system.users:
                        num_samples = int(input("Number of samples to capture (default 50): ") or "50")
                        print(f"\nStarting face capture for {lock_system.users[user_id]['name']}")
                        print("Note: Press 'q' during capture to save progress and exit early")
                        lock_system.capture_user_faces(user_id, num_samples)
                    else:
                        print("Invalid user ID")
                except ValueError:
                    print("Invalid input - please enter a number")
                except KeyboardInterrupt:
                    print("\nFace capture interrupted - saving data...")
                    lock_system.save_data()
                    print("Data saved!")

            elif choice == '3':
                if not lock_system.users:
                    print("No users registered. Add users first.")
                    continue
                if len(lock_system.faces_data['faces']) == 0:
                    print("No face samples captured. Capture faces first.")
                    continue
                
                print("Starting lock system...")
                print("Press 'q' in the camera window to exit")
                try:
                    lock_system.run_lock_system()
                except KeyboardInterrupt:
                    print("\nLock system stopped")

            elif choice == '4':
                if lock_system.users:
                    print("\nRegistered Users:")
                    print("-" * 40)
                    for uid, user in lock_system.users.items():
                        admin_status = " (Admin)" if user.get('is_admin', False) else ""
                        sample_count = lock_system.get_face_sample_count(uid)
                        created_date = user.get('created', 'Unknown')
                        print(f"  ID: {uid}")
                        print(f"  Name: {user['name']}{admin_status}")
                        print(f"  Face samples: {sample_count}")
                        print(f"  Created: {created_date}")
                        print("-" * 40)
                else:
                    print("No users registered")

            elif choice == '5':
                try:
                    if os.path.exists(lock_system.log_file):
                        with open(lock_system.log_file, 'r') as f:
                            logs = json.load(f)
                        if logs:
                            print(f"\nLast 10 access attempts:")
                            print("-" * 80)
                            for log in logs[-10:]:
                                status = "✓ SUCCESS" if log['success'] else "✗ FAILED"
                                conf_display = log.get('confidence_percentage', 'N/A')
                                timestamp = log['timestamp'][:19].replace('T', ' ')  # Format timestamp
                                print(f"  {status} | {timestamp} | {log['user_name']} | Confidence: {conf_display}")
                            print("-" * 80)
                        else:
                            print("No access logs found")
                    else:
                        print("No access log file found")
                except Exception as e:
                    print(f"Error reading logs: {e}")

            elif choice == '6':
                if not lock_system.users:
                    print("No users to delete")
                    continue
                print("Users:")
                for uid, user in lock_system.users.items():
                    sample_count = lock_system.get_face_sample_count(uid)
                    print(f"  {uid}: {user['name']} ({sample_count} samples)")
                
                try:
                    user_id = int(input("Enter user ID to delete: "))
                    if user_id in lock_system.users:
                        user_name = lock_system.users[user_id]['name']
                        confirm = input(f"Are you sure you want to delete '{user_name}'? (y/n): ").lower().strip()
                        if confirm == 'y':
                            if lock_system.delete_user(user_id):
                                print(f"User '{user_name}' deleted successfully")
                            else:
                                print("Error deleting user")
                        else:
                            print("Deletion cancelled")
                    else:
                        print("Invalid user ID")
                except ValueError:
                    print("Invalid input - please enter a number")

            elif choice == '7':
                print("Saving data manually...")
                lock_system.save_data()
                print("Data saved successfully!")

            elif choice == '8':
                # View system statistics
                stats = lock_system.get_data_statistics()
                print("\n" + "="*50)
                print("SYSTEM STATISTICS")
                print("="*50)
                print(f"Total Users: {stats['total_users']}")
                print(f"Admin Users: {stats['admin_users']}")
                print(f"Regular Users: {stats['total_users'] - stats['admin_users']}")
                print(f"Total Face Samples: {stats['total_face_samples']}")
                print(f"Users with Face Samples: {stats['users_with_samples']}")
                print(f"Users without Face Samples: {stats['users_without_samples']}")
                print(f"Data Folder: {stats['data_folder_path']}")
                print(f"Log Folder: {stats['log_folder_path']}")
                print("="*50)

            elif choice == '9':
                # Export logs to CSV
                print("Exporting access logs to CSV...")
                if lock_system.export_logs_to_csv():
                    print("Logs exported successfully!")
                else:
                    print("Failed to export logs")

            elif choice == '10':
                # Clean up orphaned data
                print("Checking for orphaned face data...")
                cleaned_count = lock_system.cleanup_orphaned_data()
                if cleaned_count > 0:
                    print(f"Cleaned up {cleaned_count} orphaned face samples")
                else:
                    print("No orphaned data found")

            elif choice == '11':
                print("Saving data before exit...")
                lock_system.save_data()
                print("Data saved successfully!")
                print("Goodbye!")
                break

            else:
                print("Invalid choice - please select 1-11")

    except KeyboardInterrupt:
        print("\nProgram interrupted by user")
    except Exception as e:
        print(f"Unexpected error: {e}")
    finally:
        # Ensure data is saved even if there's an unexpected error
        if lock_system:
            print("Final data save...")
            lock_system.save_data()
            print("Data saved!")


if __name__ == "__main__":
    try:
        import cv2
        # Check if face recognition module is available
        cv2.face.LBPHFaceRecognizer_create()
    except AttributeError:
        print("Error: opencv-contrib-python is required for face recognition")
        print("Install it with: pip install opencv-contrib-python")
        exit(1)
    except ImportError:
        print("Error: OpenCV is not installed")
        print("Install it with: pip install opencv-python")
        exit(1)

    setup_system()