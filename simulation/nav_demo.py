import math
import random
import pygame
import time
import copy
import threading
import sys

from utils import Vector, Point, normalize_angle

BOT_COLOR = (255, 0, 0)
OBSTACLE_COLOR = (0,255, 0)

pygame.init()

# Constants
WIDTH, HEIGHT = 800, 600
FPS = 60
delta_time = 1/FPS
BG_COLOR = (0, 0, 0)
screen = pygame.display.set_mode((WIDTH, HEIGHT))


class Bot:
    def __init__(self, start_point, initial_angle): 
        self.coords = copy.deepcopy(start_point)
        self.radius = 10
        self.num_rays = 25
        self.max_distance = 300
        self.safe_distance = 30
        self.distances = []
        self.angle = initial_angle
        self.speed = 0
        self.angular_velocity = 0

    def update(self, obstacles):
        if not any( bot.collides_with(obstacle.rect) for obstacle in obstacles):
            self.coords.x += self.speed * delta_time * math.cos(self.angle)
            self.coords.y += self.speed * delta_time * math.sin(self.angle)
        self.angle += self.angular_velocity
      

    def turn_inplace(self, theta):
        self.angle += theta
    
    def set_speed(self, speed):
        self.speed = speed

    def set_angular_velocity(self, v):
        self.angular_velocity = v

    def collides_with(self, rect):
        # Find the closest point on the rectangle to the circle center
        closest_point = Point(
            max(rect.left, min(self.coords.x, rect.right)),
            max(rect.top, min(self.coords.y, rect.bottom))
        )

        d = self.coords - closest_point
        if d.x**2 + d.y**2 >= self.radius**2:
            return False  # no collision

        # Check if we're moving into the surface
        movement_dir = Vector.from_angle(self.angle)
        return d.normalized() * movement_dir < 0
  
    def raycast_all(self, obstacles):
        self.distances = []
        turn_angle = 0
        for i in range(self.num_rays):
            angle = 2 * math.pi * i / self.num_rays + self.angle
            dx = math.cos(angle)
            dy = math.sin(angle)
            distance = 0


            while distance < self.max_distance:
                test_point = self.coords + Vector(dx, dy) * distance

                if any(ob.collidepoint(test_point) for ob in obstacles):
                    break

                distance += 1
            angle = normalize_angle(angle - self.angle) 
            
            if distance != 0 and distance < self.max_distance and -math.pi/3 <= angle <= math.pi/3:
                if angle == 0:
                    angle = 2 * math.pi / self.num_rays
                turn_angle += -(1/angle)/(0.1*distance**2)
                
            
            self.distances.append((distance, angle))
        self.turn_inplace(turn_angle)
        
    

    def draw_rays(self, screen):
        for i, dist in enumerate(self.distances):
            dist = dist[0]
            angle = 2 * math.pi * i / self.num_rays + self.angle
            end = self.coords + Vector(math.cos(angle), math.sin(angle)) * dist
            pygame.draw.line(screen, (255, 0, 0), self.coords.to_pg(), end.to_pg(), 1)


    def draw(self):
        direction_vector = Vector.from_mag_and_dir(15, self.angle)
        pygame.draw.circle(screen, BOT_COLOR, self.coords.to_pg(), self.radius)
        direction_vector.draw(self.coords, screen, BOT_COLOR)



class Obstacle:
    def __init__(self, coords, width, height):
        self.coords = coords
        self.rect = pygame.Rect((coords.x, coords.y), (width, height))
    def collidepoint(self, pt):
        return self.rect.collidepoint((pt.x, pt.y))
    def draw(self, color = OBSTACLE_COLOR):
        pygame.draw.rect(screen, color, self.rect)

    

state = {
    "old_coords": Vector(0,0),
    "real_vector": Vector(0,0),
    "ideal_vector": Vector(0,0),
    "error": Vector(0,0)
}



# Set up display

pygame.display.set_caption("Pygame Sample")

i = 0
goals = [Point(100, 100), Point(500, 200), Point(300, 500)]



bot = Bot(Point(500, 500), math.pi)

obstacles = [Obstacle(Point(random.randrange(0, WIDTH//2 + WIDTH//3), random.randrange(0, HEIGHT//2 + HEIGHT//3)), random.randrange(10,40), random.randrange(10,40)) for i in range(15)]
#obstacles = []
# Clock to control FPS
clock = pygame.time.Clock()

# Initial circle position
x, y = WIDTH // 2, HEIGHT // 2


    
def draw():
    bot.draw()
    for goal in goals:
        goal.draw(screen)
    bot.draw_rays(screen)
    for obstacle in obstacles:
        obstacle.draw()
    state["ideal_vector"].draw(state["old_coords"], screen)
    state["real_vector"].draw(state["old_coords"], screen)
    state["error"].draw(state["old_coords"] + state["real_vector"], screen)



def nav_loop(smoothness):
    while True:
        state["old_coords"] = copy.copy(bot.coords)
        bot.set_speed(50)
        time.sleep(1/smoothness)
        bot.set_speed(0)
        turning_angle = Vector.angle_between(state["real_vector"], state["error"])
        #bot.turn_inplace(turning_angle/smoothness) #simulate smaller turns
        bot.set_angular_velocity(turning_angle / (5 * smoothness))

t = threading.Thread(target=nav_loop, args=[10])
t.start()

running = True
while running:
    clock.tick(FPS)

    # Event handling
    for event in pygame.event.get():
        if event.type == pygame.QUIT:
            running = False

    # Drawing
    screen.fill(BG_COLOR)

    bot.raycast_all(obstacles)
    bot.update(obstacles)

    state["ideal_vector"] = goals[i] - state["old_coords"]
    state["real_vector"] =  bot.coords - state["old_coords"]
    state["error"] = state["ideal_vector"] - state["real_vector"]

    draw()
    if (bot.coords - goals[i]).mag() < 30:
        i += 1

    pygame.display.flip()

# Cleanup
pygame.quit()
sys.exit()