import serial
import threading
import time
import sys
from devices.compass import Compass
from devices.gps import GPS
from devices.lidar import Lidar
from devices.camera import Camera  # Add camera import
from devices.ultrasonic import UltrasonicSensor
from navigation.ftg import FollowTheGapWorker
from navigation.waypoint import WaypointNavigator
from navigation.nav_video_w_cp import HybridNavigator
import Jetson.GPIO as GPIO

def main():
    GPIO.setmode(GPIO.BOARD) 
    # Initialize devices
    right_uv = UltrasonicSensor(11, 13, 1)
    #left_uv = UltrasonicSensor(15, 16)
    while True:
        print(right_uv.get_distance())
        #print(left_uv.get_distance())
        time.sleep(1)
    sys.exit(0)
    compass = Compass()
    gps = GPS()
    lidar = Lidar("/dev/ttyUSB2")
    camera = Camera()  # Initialize camera
    
    # Initialize navigation components
    ftg = FollowTheGapWorker(lidar)
    waypoint = WaypointNavigator(gps, compass, [(40.0370259, -86.90659)])
    
    # Connect to Arduino and start navigation
    try:
        with serial.Serial("/dev/ttyACM0", 9600, timeout=2) as ser:
            time.sleep(2)
            print("Connected to Arduino")
            
            # Create hybrid navigator with all required parameters
            nav = HybridNavigator(
        base_speed=base_speed,
        ftg_navigator=ftg_navigator,
        waypoint_navigator=waypoint_navigator,
        camera=camera,
        ser=ser,
        enable_recording=True,
        recording_dir="robot_recordings"
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