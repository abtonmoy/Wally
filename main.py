import serial
import threading
import time
import sys
from devices.compass import Compass
from devices.gps import GPS
from devices.lidar import Lidar
from devices.camera import Camera  # Add camera import
#from devices.ultrasonic import UltrasonicSensor
from navigation.ftg import FollowTheGapWorker
from navigation.waypoint import WaypointNavigator
from navigation.navigation_vision_enhanced import HybridNavigator
from navigation.main_navigation import EnhancedHybridNavigator

def main():
    compass = Compass()
    gps = GPS()
    lidar = Lidar("/dev/ttyUSB2")
    camera = Camera()  # Initialize camera
    
    # Initialize navigation components
    ftg = FollowTheGapWorker(lidar)
    waypoint = WaypointNavigator(gps, compass, [(40.036920, -86.907327), (40.0368575, -86.9073315),(40.0367538, -86.9071431)])
    
    # Connect to Arduino and start navigation
    try:
        with serial.Serial("/dev/ttyACM0", 9600, timeout=2) as ser:
            time.sleep(2)
            print("Connected to Arduino")
            
            # Create hybrid navigator with all required parameters
            nav = EnhancedHybridNavigator(
                base_speed=60,
                ftg_navigator=ftg,
                waypoint_navigator=waypoint,
                camera=camera,
                ser=ser
            )
            time.sleep(2)
            print(camera.get_camera_status())
            # Start the navigation loop
            print("Starting hybrid navigation...")
            nav.run()
            
    except serial.SerialException as e:
        print(f"Serial connection error: {e}")
    except KeyboardInterrupt:
        print("\nNavigation stopped by user")
    except Exception as e:
        print(f"Navigation error: {e}")
    finally:
        # Cleanup
        if 'nav' in locals():
            nav.stop_robot()
        print("Navigation system shutdown")


if __name__ == "__main__":
    main()
