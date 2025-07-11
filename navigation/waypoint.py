import math

class WaypointNavigator:
    def __init__(self, gps, compass, waypoints):
        self.gps = gps
        self.compass = compass
        self.waypoints = waypoints
        self.waypoint_rad = 1
        self.waypoint_index = 0

    def haversine(self, lat1, lon1, lat2, lon2):
        R = 6371000 # radius of the earth
        phi1 = math.radians(lat1)
        phi2 = math.radians(lat2)
        dphi = math.radians(lat2 - lat1)
        dlambda = math.radians(lon2 - lon1)

        a = math.sin(dphi/2.0)**2 + \
            math.cos(phi1) * math.cos(phi2) * math.sin(dlambda/2.0)**2

        c = 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))
        return R * c

    def distance(self):
        pass

    def next_waypoint(self):
        if len(self.waypoints) - 1 > self.waypoint_index:
            self.waypoint_index += 1
         

    def bearing(self, lat1, lon1, lat2, lon2):
        phi1 = math.radians(lat1)
        phi2 = math.radians(lat2)
        dlambda = math.radians(lon2 - lon1)

        y = math.sin(dlambda) * math.cos(phi2)
        x = math.cos(phi1)*math.sin(phi2) - \
            math.sin(phi1)*math.cos(phi2)*math.cos(dlambda)
        theta = math.atan2(y, x)
        return (theta + 2 * math.pi) % (2 * math.pi)

    def get_navigation_command(self):
        current_pos = self.gps.read_location()
        if current_pos is None:
            print("GPS no fix")
            return None, None, None

        current_lat, current_lon = current_pos
        curr_waypoint = self.waypoints[self.waypoint_index]
        dist = self.haversine(current_lat, current_lon,
                              curr_waypoint[0], curr_waypoint[1])

       
        desired_bearing = self.bearing(current_lat, current_lon, curr_waypoint[0], curr_waypoint[1])
        heading = self.compass.get_heading()

        heading_error = (desired_bearing - heading + math.pi) % (2 * math.pi) - math.pi

        return heading_error, dist, desired_bearing
