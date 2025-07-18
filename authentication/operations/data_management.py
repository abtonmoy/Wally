# data_management.py
import os
import pickle
import json
from datetime import datetime

class DataManager:
    def __init__(self):
        """Initialize the data management component"""
        # Create required directories
        self.data_folder = 'data'
        self.log_folder = 'log_files'
        self.create_directories()
        
        # Set file paths with proper directory structure
        self.users_db_path = os.path.join(self.data_folder, 'users_database.pkl')
        self.faces_data_path = os.path.join(self.data_folder, 'faces_data.pkl')
        self.log_file = os.path.join(self.log_folder, 'access_log.json')
        
        # User database
        self.users = {}  # {user_id: {'name': str, 'is_admin': bool, 'created': datetime}}
        self.faces_data = {'faces': [], 'labels': [], 'user_ids': []}
        
        # Load existing data
        self.load_data()
        print("Data Management Initialized")
        print(f"Data folder: {os.path.abspath(self.data_folder)}")
        print(f"Log folder: {os.path.abspath(self.log_folder)}")

    def create_directories(self):
        """Create required directories if they don't exist"""
        try:
            # Create data folder
            if not os.path.exists(self.data_folder):
                os.makedirs(self.data_folder)
                print(f"Created data directory: {self.data_folder}")
            
            # Create log files folder
            if not os.path.exists(self.log_folder):
                os.makedirs(self.log_folder)
                print(f"Created log directory: {self.log_folder}")
                
        except Exception as e:
            print(f"Error creating directories: {e}")
            # Fallback to current directory if folder creation fails
            self.data_folder = '.'
            self.log_folder = '.'
            print("Falling back to current directory for file storage")

    def load_data(self):
        """Load user database and face data from files"""
        try:
            # Load users database
            if os.path.exists(self.users_db_path):
                with open(self.users_db_path, 'rb') as f:
                    self.users = pickle.load(f)
                print(f"Loaded {len(self.users)} users from database")
            else:
                print("No existing users database found - starting fresh")
            
            # Load faces data
            if os.path.exists(self.faces_data_path):
                with open(self.faces_data_path, 'rb') as f:
                    self.faces_data = pickle.load(f)
                print(f"Loaded {len(self.faces_data['faces'])} face samples from database")
            else:
                print("No existing faces data found - starting fresh")
                
            print("Data loaded successfully")
            
        except Exception as e:
            print(f"Error loading data: {e}")
            print("Starting with empty database")
            # Reset to empty data structures on error
            self.users = {}
            self.faces_data = {'faces': [], 'labels': [], 'user_ids': []}

    def save_data(self):
        """Save user database and face data to files"""
        try:
            # Ensure directories exist before saving
            self.create_directories()
            
            # Save users database
            with open(self.users_db_path, 'wb') as f:
                pickle.dump(self.users, f)
            
            # Save faces data
            with open(self.faces_data_path, 'wb') as f:
                pickle.dump(self.faces_data, f)
            
            print(f"Data saved successfully:")
            print(f"  - Users: {len(self.users)} saved to {self.users_db_path}")
            print(f"  - Face samples: {len(self.faces_data['faces'])} saved to {self.faces_data_path}")
            
        except Exception as e:
            print(f"Error saving data: {e}")
            try:
                # Try to save in current directory as backup
                backup_users_path = 'users_database_backup.pkl'
                backup_faces_path = 'faces_data_backup.pkl'
                
                with open(backup_users_path, 'wb') as f:
                    pickle.dump(self.users, f)
                with open(backup_faces_path, 'wb') as f:
                    pickle.dump(self.faces_data, f)
                    
                print(f"Data saved as backup files in current directory")
                
            except Exception as backup_error:
                print(f"Critical error: Unable to save data - {backup_error}")

    def log_access(self, user_id, success, confidence=None):
        """Log access attempts"""
        log_entry = {
            'timestamp': datetime.now().isoformat(),
            'user_id': user_id,
            'user_name': self.users.get(user_id, {}).get('name', 'Unknown'),
            'success': success,
            'confidence': confidence,
            'confidence_percentage': f"{confidence*100:.1f}%" if confidence else None
        }
        
        try:
            # Ensure log directory exists
            self.create_directories()
            
            # Load existing logs
            logs = []
            if os.path.exists(self.log_file):
                try:
                    with open(self.log_file, 'r') as f:
                        logs = json.load(f)
                except json.JSONDecodeError:
                    print("Warning: Corrupted log file, starting new log")
                    logs = []
            
            # Add new log entry
            logs.append(log_entry)
            
            # Keep only last 1000 entries to prevent file from growing too large
            if len(logs) > 1000:
                logs = logs[-1000:]
            
            # Save updated logs
            with open(self.log_file, 'w') as f:
                json.dump(logs, f, indent=2)
            
            # Print log entry for console output
            status = "SUCCESS" if success else "FAILED"
            conf_text = f" (confidence: {confidence*100:.1f}%)" if confidence else ""
            print(f"[LOG] {status}: {log_entry['user_name']}{conf_text}")
            
        except Exception as e:
            print(f"Error logging access: {e}")
            # Try to save log in current directory as backup
            try:
                backup_log_file = 'access_log_backup.json'
                logs = []
                if os.path.exists(backup_log_file):
                    with open(backup_log_file, 'r') as f:
                        logs = json.load(f)
                logs.append(log_entry)
                with open(backup_log_file, 'w') as f:
                    json.dump(logs, f, indent=2)
                print(f"Log saved as backup in current directory")
            except Exception as backup_error:
                print(f"Unable to save log entry: {backup_error}")

    def add_user(self, name, is_admin=False):
        """Add a new user to the system"""
        # Generate new user ID (find the next available ID)
        if self.users:
            user_id = max(self.users.keys()) + 1
        else:
            user_id = 1
            
        self.users[user_id] = {
            'name': name,
            'is_admin': is_admin,
            'created': datetime.now().isoformat()
        }
        
        # Save data immediately
        self.save_data()
        print(f"User '{name}' added with ID: {user_id}")
        return user_id

    def delete_user(self, user_id):
        """Delete a user and their associated face data"""
        if user_id in self.users:
            user_name = self.users[user_id]['name']
            
            # Remove user from database
            del self.users[user_id]
            
            # Remove associated face data
            indices_to_remove = [i for i, uid in enumerate(self.faces_data['user_ids']) if uid == user_id]
            for i in reversed(indices_to_remove):  # Remove in reverse order to maintain indices
                del self.faces_data['faces'][i]
                del self.faces_data['labels'][i]
                del self.faces_data['user_ids'][i]
            
            # Save data immediately
            self.save_data()
            print(f"User '{user_name}' and {len(indices_to_remove)} face samples deleted successfully")
            return True
        else:
            print(f"User ID {user_id} not found")
            return False

    def get_user_count(self):
        """Get the number of registered users"""
        return len(self.users)

    def get_face_sample_count(self, user_id):
        """Get the number of face samples for a specific user"""
        return self.faces_data['user_ids'].count(user_id)

    def get_total_face_samples(self):
        """Get the total number of face samples across all users"""
        return len(self.faces_data['faces'])

    def get_data_statistics(self):
        """Get comprehensive statistics about the data"""
        stats = {
            'total_users': len(self.users),
            'admin_users': sum(1 for user in self.users.values() if user.get('is_admin', False)),
            'total_face_samples': len(self.faces_data['faces']),
            'users_with_samples': len(set(self.faces_data['user_ids'])),
            'users_without_samples': len(self.users) - len(set(self.faces_data['user_ids'])),
            'data_folder_path': os.path.abspath(self.data_folder),
            'log_folder_path': os.path.abspath(self.log_folder)
        }
        return stats

    def cleanup_orphaned_data(self):
        """Remove face data for users who no longer exist"""
        valid_user_ids = set(self.users.keys())
        indices_to_remove = []
        
        for i, user_id in enumerate(self.faces_data['user_ids']):
            if user_id not in valid_user_ids:
                indices_to_remove.append(i)
        
        # Remove orphaned data
        for i in reversed(indices_to_remove):
            del self.faces_data['faces'][i]
            del self.faces_data['labels'][i]
            del self.faces_data['user_ids'][i]
        
        if indices_to_remove:
            self.save_data()
            print(f"Cleaned up {len(indices_to_remove)} orphaned face samples")
        
        return len(indices_to_remove)

    def export_logs_to_csv(self, output_file=None):
        """Export access logs to CSV format"""
        try:
            import csv
            
            if output_file is None:
                output_file = os.path.join(self.log_folder, 'access_log_export.csv')
            
            if os.path.exists(self.log_file):
                with open(self.log_file, 'r') as f:
                    logs = json.load(f)
                
                with open(output_file, 'w', newline='') as csvfile:
                    fieldnames = ['timestamp', 'user_id', 'user_name', 'success', 'confidence', 'confidence_percentage']
                    writer = csv.DictWriter(csvfile, fieldnames=fieldnames)
                    writer.writeheader()
                    writer.writerows(logs)
                
                print(f"Logs exported to: {output_file}")
                return True
            else:
                print("No log file found to export")
                return False
                
        except ImportError:
            print("CSV module not available")
            return False
        except Exception as e:
            print(f"Error exporting logs: {e}")
            return False