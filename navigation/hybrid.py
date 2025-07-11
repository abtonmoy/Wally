import time
import serial
import struct

Commands = {
    "turn_wheel":        0,
    "turn_while_moving": 1,
    "turn_inplace":      2,
    "drive_straight":    3,
    "drive_m_meters":    4,
    "reverse":           5,
}
    


class HybridNavigator:
    def __init__(self, base_speed, ftg_navigator, waypoint_navigator, ser):
        self.ftg_navigator = ftg_navigator
        self.waypoint_navigator = waypoint_navigator
        self.base_speed = base_speed
        self.safe_distance = 1.5
        self.stop_distance = 0.5
        self.ser = ser
        self.last_command_time = time.time()
        
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

    def calculate_navigation_speed_radius(self, angle, dist):
        if dist > 3:
            speed = self.base_speed
        elif dist != 0:
            if dist < self.waypoint_navigator.waypoint_rad:
                self.waypoint_navigator.next_waypoint()
            speed = self.base_speed * (self.safe_distance * 1 / dist)
        else:
            speed = 0
        radius = 1.5 / angle  

        return speed, radius

    def calculate_avoidance_speed_radius(self, angle, min_dist):
        speed = self.base_speed * (1000 / min_dist) # If the nearest obstacle is a meter away, go at base speed
        radius =  0.8  / angle

        return speed, radius

    def run(self):
        while True:
            ftg_min_dist, gap_angle = self.ftg_navigator.min_distance, self.ftg_navigator.get_current_gap_angle()
            error, distance, desired = self.waypoint_navigator.get_navigation_command()

            if error != None and distance != None:
                nav_speed, nav_radius = self.calculate_navigation_speed_radius(error, distance)
                print(nav_speed, nav_radius)
            else:
                pass

            if ftg_min_dist != None and  ftg_min_dist < self.safe_distance:
                ftg_speed, ftg_radius = self.calculate_avoidance_speed_radius(gap_angle, ftg_min_dist)
                speed = ftg_speed 
                radius = (ftg_radius + nav_radius)/2
            else:
                speed = nav_speed 
                radius =  nav_radius
                print(f"Final speed {speed}, final radius: {radius}")
            
            if ftg_min_dist != None and ftg_min_dist < self.stop_distance:
                print("Stopping robot")
                self.stop_robot()
            elif radius > 1.5:
                self.send_command(Commands["drive_straight"], speed)
            else:
                self.send_command(Commands["turn_while_moving"], radius, speed)
                
            time.sleep(0.1)

           





