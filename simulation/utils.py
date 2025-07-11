import pygame
import math

def draw_arrow(
        surface: pygame.Surface,
        start: pygame.Vector2,
        end: pygame.Vector2,
        color: pygame.Color,
        body_width: int = 2,
        head_width: int = 4,
        head_height: int = 2,
    ):
    """Draw an arrow between start and end with the arrow head at the end.

    Args:
        surface (pygame.Surface): The surface to draw on
        start (pygame.Vector2): Start position
        end (pygame.Vector2): End position
        color (pygame.Color): Color of the arrow
        body_width (int, optional): Defaults to 2.
        head_width (int, optional): Defaults to 4.
        head_height (float, optional): Defaults to 2.
    """
    arrow = start - end
    angle = arrow.angle_to(pygame.Vector2(0, -1))
    body_length = arrow.length() - head_height

    # Create the triangle head around the origin
    head_verts = [
        pygame.Vector2(0, head_height / 2),  # Center
        pygame.Vector2(head_width / 2, -head_height / 2),  # Bottomright
        pygame.Vector2(-head_width / 2, -head_height / 2),  # Bottomleft
    ]
    # Rotate and translate the head into place
    translation = pygame.Vector2(0, arrow.length() - (head_height / 2)).rotate(-angle)
    for i in range(len(head_verts)):
        head_verts[i].rotate_ip(-angle)
        head_verts[i] += translation
        head_verts[i] += start

    pygame.draw.polygon(surface, color, head_verts)

    # Stop weird shapes when the arrow is shorter than arrow head
    if arrow.length() >= head_height:
        # Calculate the body rect, rotate and translate into place
        body_verts = [
            pygame.Vector2(-body_width / 2, body_length / 2),  # Topleft
            pygame.Vector2(body_width / 2, body_length / 2),  # Topright
            pygame.Vector2(body_width / 2, -body_length / 2),  # Bottomright
            pygame.Vector2(-body_width / 2, -body_length / 2),  # Bottomleft
        ]
        translation = pygame.Vector2(0, body_length / 2).rotate(-angle)
        for i in range(len(body_verts)):
            body_verts[i].rotate_ip(-angle)
            body_verts[i] += translation
            body_verts[i] += start

        pygame.draw.polygon(surface, color, body_verts)


def sign(x):
    if x > 0:
        return 1
    elif x < 0:
        return -1
    else:
        return 0

def normalize_angle(angle):
    return angle - (math.ceil((angle + math.pi)/(2*math.pi))-1)*2*math.pi

def haversine_distance(p1, p2):
    R = 6371000  # Earth radius in meters
    lat1 = math.radians(p1['latitude'])
    lon1 = math.radians(p1['longitude'])
    lat2 = math.radians(p2['latitude'])
    lon2 = math.radians(p2['longitude'])

    dlat = lat2 - lat1
    dlon = lon2 - lon1

    a = math.sin(dlat / 2) ** 2 + math.cos(lat1) * math.cos(lat2) * math.sin(dlon / 2) ** 2
    c = 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))
    return R * c  # in meters

VECTOR_COLOR = (255,255,255)
POINT_COLOR = (0,0,255)


class Point:
    def __init__(self, x, y):
        self.x = x
        self.y = y
    def __sub__(self, other):
        return Vector(self.x - other.x, self.y - other.y)

    def add_vector(self, vect):
        return Point(self.x + vect.x, self.y + vect.y)

    def __str__(self):
        return f"({self.x}, {self.y})"

    def to_pg(self):
        return pygame.Vector2(self.x, self.y)
    
    def draw(self, screen=None, color=POINT_COLOR):
        pygame.draw.circle(screen, color, pygame.Vector2(self.x, self.y), 5)


class Vector:
    def __init__(self, x, y):
        self.x = x
        self.y = y

    @staticmethod
    def from_mag_and_dir(mag, dir):
        return Vector(mag * math.cos(dir), mag*math.sin(dir))

    @staticmethod
    def from_angle(angle):
        return Vector.from_mag_and_dir(1, angle)

    @staticmethod 
    def angle_between(v1, v2):
        dot = v1 * v2
        cross = v1.x * v2.y - v1.y * v2.x

        return math.atan2(cross, dot)

    def __add__(self, other):
        return Vector(self.x + other.x, self.y + other.y)

    def __radd__(self, other):
        return Vector(self.x + other.x, self.y + other.y)

    def __sub__(self, other):
        return Vector(self.x - other.x, self.y - other.y)

    def __neg__(self):
        return Vector(-self.x, -self.y)

    def __mul__(self, other): # dot product / scalar multiplication
        if type(other) != Vector:
            return Vector(other * self.x, other * self.y)
        return self.x * other.x + self.y * other.y
    def __rmul__(self, other): # dot product / scalar multiplication
        if type(other) != Vector:
            return Vector(other * self.x, other * self.y)
        return self.x * other.x + self.y * other.y
    def mag(self):
        return math.sqrt(self.x**2+self.y**2)

    def dir(self):
        return math.atan2(self.y, self.x)

    def normalized(self):
        direction = self.dir()
        return Vector(1 * math.cos(direction), 1 * math.sin(direction))
    
    def __len__(self):
        return self.mag()
    def __str__(self):
        return f"<{self.x}, {self.y}>"

    def to_pg(self):
        return pygame.Vector2(self.x, self.y)

    def draw(self, origin, screen=None, color=VECTOR_COLOR):
        end = origin + self
        draw_arrow(screen, pygame.Vector2(origin.x, origin.y), pygame.Vector2(end.x, end.y), color, 2, 10, 10)