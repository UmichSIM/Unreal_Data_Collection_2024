#!/usr/bin/env python


import pygame
import os
import sys
import pygame
import math
import time
import carla
import argparse
import matplotlib.pyplot as plt
import matplotlib.animation as animation
import random
import numpy as np
# from manual_control_steeringwheel import World, HUD
os.environ["SDL_JOYSTICK_ALLOW_BACKGROUND_EVENTS"] = "1"
if sys.version_info >= (3, 0):

    from configparser import ConfigParser

else:

    from ConfigParser import RawConfigParser as ConfigParser


# Constants
SCREEN_WIDTH = 1000
SCREEN_HEIGHT = 800
BACKGROUND_COLOR = (255, 255, 255)
SURFACE_WIDTH = 300
SURFACE_HEIGHT = 250
MAX_DATA_POINTS = 85  # Number of data points to display idk why its 85
DATA_UPDATE_INTERVAL = 100  # Update data every 100 milliseconds
LINE_COLOR = (0, 0, 0)

# ==============================================================================
# -- World --------NO NEED-----------------------------------------
# ==============================================================================


class DualControl(object):
    def __init__(self ):
 
        # initialize steering wheel
        pygame.joystick.init()

        joystick_count = pygame.joystick.get_count()
        if joystick_count > 1:
            raise ValueError("Please Connect Just One Joystick")

        self._joystick = pygame.joystick.Joystick(0)
        self._joystick.init()

        self._parser = ConfigParser()
        self._parser.read('wheel_config.ini')
        self._steer_idx = int(
            self._parser.get('G29 Racing Wheel', 'steering_wheel'))
        self._throttle_idx = int(
            self._parser.get('G29 Racing Wheel', 'throttle'))
        self._brake_idx = int(self._parser.get('G29 Racing Wheel', 'brake'))
        self._reverse_idx = int(self._parser.get('G29 Racing Wheel', 'reverse'))
        self._handbrake_idx = int(
            self._parser.get('G29 Racing Wheel', 'handbrake'))
        
        self.brake = 0
        self.throttle = 0
        self.steer = 0
        self._overlay_button_idx = 7
        self.button_press = 0
    def _parse_vehicle_wheel(self):
        #self.button_press = 0
        pygame.joystick.init()

        self._joystick = pygame.joystick.Joystick(0)
        self._joystick.init()
        numAxes = self._joystick.get_numaxes()
        jsInputs = [float(self._joystick.get_axis(i)) for i in range(numAxes)]
        # print (jsInputs)
        jsButtons = [float(self._joystick.get_button(i)) for i in
                     range(self._joystick.get_numbuttons())]

        # Custom function to map range of inputs [1, -1] to outputs [0, 1] i.e 1 from inputs means nothing is pressed
        # For the steering, it seems fine as it is
        K1 = 1.0  # 0.55
        steerCmd = K1 * math.tan(1.1 * jsInputs[self._steer_idx])

        K2 = 1.6  # 1.6
        throttleCmd = K2 + (2.05 * math.log10(
            -0.7 * jsInputs[self._throttle_idx] + 1.4) - 1.2) / 0.92
        if throttleCmd <= 0:
            throttleCmd = 0
        elif throttleCmd > 1:
            throttleCmd = 1

        brakeCmd = 1.6 + (2.05 * math.log10(
            -0.7 * jsInputs[self._brake_idx] + 1.4) - 1.2) / 0.92
        if brakeCmd <= 0:
            brakeCmd = 0
        elif brakeCmd > 1:
            brakeCmd = 1
        
        self.brake = brakeCmd
        self.throttle=throttleCmd
        self.steer = steerCmd
        #toggle = jsButtons[self._reverse_idx]
        for event in pygame.event.get():
            if event.type == pygame.JOYBUTTONDOWN:
                if event.button == self._overlay_button_idx:
                    self.button_press = 1
            if event.type == pygame.JOYBUTTONUP:
                if event.button == self._overlay_button_idx:
                    self.button_press = 0
            
def get_Car(client):
    world = client.get_world()
        
    #print(world.get_actors())
    player_vehicle = None
    while True:
        if player_vehicle is not None:
            break
        for actor in world.get_actors():
            if 'vehicle' in actor.type_id:
                player_vehicle = actor
                break

    return player_vehicle

def get_car_velocity(player_vehicle):
    vector3D = player_vehicle.get_velocity()
    return vector3D

def get_car_speed(player_vehicle):
    vector3D = player_vehicle.get_velocity()
    return vector3D.length();

def get_car_location(player_vehicle):
    vector3D = player_vehicle.get_location()
    return vector3D

def get_car_acceleration(player_vehicle):
    vector3D = player_vehicle.get_acceleration()
    return vector3D;

def draw_labels(surface,screen, x_label, y_label, lower_bound, upper_bound, sections):
    font = pygame.font.Font(None, 16)
    
    # X label
    x_label = font.render(x_label, True, LINE_COLOR)
    x_label_rect = x_label.get_rect()
    x_label_rect.center = (SURFACE_WIDTH // 2, SURFACE_HEIGHT-15)
    surface.blit(x_label, x_label_rect)
    
    # Y label
    y_label = font.render(y_label, True, LINE_COLOR)
    y_label = pygame.transform.rotate(y_label, 90)  # Rotate for vertical display
    y_label_rect = y_label.get_rect()
    y_label_rect.center = (10, SURFACE_HEIGHT // 2)
    surface.blit(y_label, y_label_rect)

    # Draw y Axis Rulers
    for i in np.linspace(lower_bound, upper_bound, sections):
        y_axis_value = font.render("{:.2f}".format(i), True, (255, 165, 0))  # Display "0" at the left
        y_axis_value_rect = y_axis_value.get_rect()
        y_axis_value_rect.center = (30, (1 - ((i - lower_bound) / (upper_bound - lower_bound)))* (SURFACE_HEIGHT*0.8) + 10)
        surface.blit(y_axis_value, y_axis_value_rect)

    # pygame.draw.line(screen, (255, 165, 0), (GRAPH_X, GRAPH_Y + GRAPH_HEIGHT - 50), (GRAPH_X + GRAPH_WIDTH, GRAPH_Y + GRAPH_HEIGHT - 50), 2)

    
    return x_label, x_label_rect, y_label, y_label_rect, y_axis_value, y_axis_value_rect
    
def draw_line(graph_surface,data,color, lower_bound, upper_bound, legend = None):
    # Draw data points and lines
    font = pygame.font.Font(None, 20)
    if len(data) > 1:
        for i in range(len(data) - 1):
            x1 = i * (SURFACE_WIDTH // (MAX_DATA_POINTS - 1))
            y1 = (1 - ((data[i] - lower_bound) / (upper_bound - lower_bound)))* (SURFACE_HEIGHT*0.8)+10
            x2 = (i + 1) * (SURFACE_WIDTH // (MAX_DATA_POINTS - 1))
            y2 = (1 - ((data[i+1] - lower_bound) / (upper_bound - lower_bound)))* (SURFACE_HEIGHT*0.8)+10
            pygame.draw.line(graph_surface, color, (x1+40, y1), (x2+40, y2), 2)
        
        if legend is not None:
            print(legend)
            last_value_label = font.render(legend, True, color)
            last_value_rect = (last_value_label.get_rect())
            last_value_rect.midleft = (SURFACE_WIDTH-10, (1 - ((data[-1] - lower_bound) / (upper_bound - lower_bound)))* (SURFACE_HEIGHT*0.8) + 10)
            graph_surface.blit(last_value_label, last_value_rect)

def draw_graph(surface, screen, datas, colors, x, y, lower_bound, upper_bound, sections, legends = None):
    surface.fill(BACKGROUND_COLOR)
    # Draw grid lines
    for i in np.linspace(lower_bound, upper_bound, sections):
        pygame.draw.line(surface, (200, 200, 200), (40, (1 - ((i - lower_bound) / (upper_bound - lower_bound)))* (SURFACE_HEIGHT*0.8)+10), (SURFACE_WIDTH, (1 - ((i - lower_bound) / (upper_bound - lower_bound)))* (SURFACE_HEIGHT*0.8)+10), 1)
    for i, data in enumerate(datas):
        if legends is not None:
            draw_line(surface, data, colors[i], lower_bound, upper_bound, legends[i])
        else:
            draw_line(surface, data, colors[i], lower_bound, upper_bound)
    
def update_data(datas, points):
    # Simulate data update (replace this with your data source)
    for i, data in enumerate(datas):
        data.append(points[i])
    # print("updating", data)
    # Keep only the last MAX_DATA_POINTS data points
        if len(data) > MAX_DATA_POINTS:
            data.pop(0)
            # print("deleting")
    return datas

# Function to take a screenshot of the entire display with a timestamp
def take_screenshot(screen):
    timestamp = datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
    screenshot_name = f"graph_screenshot_{timestamp}.png"
    screenshot = pygame.Surface((SCREEN_WIDTH, SCREEN_HEIGHT))
    screenshot.blit(screen, (0, 0))
    x_label, x_label_rect, y_label, y_label_rect, y_axis_value, y_axis_value_rect, last_value_label, last_value_rect = draw_labels(None)
    screenshot.blit(x_label, x_label_rect)
    screenshot.blit(y_label, y_label_rect)
    screenshot.blit(y_axis_value, y_axis_value_rect)
    if last_value_label is not None:
        screenshot.blit(last_value_label, last_value_rect)
    pygame.image.save(screenshot, screenshot_name)

def display_subscreen(screen, data, color, x, y, x_label, y_label, lower_bound, upper_bound, sections, legends = None):
    surface = pygame.Surface((SURFACE_WIDTH, SURFACE_HEIGHT))
    draw_graph(surface, screen, data, color, 30, 600, lower_bound, upper_bound, sections, legends)
            # Draw labels and the last value
    x_label, x_label_rect, y_label, y_label_rect, y_axis_value, y_axis_value_rect = \
    draw_labels(surface, screen, x_label, y_label, lower_bound, upper_bound, sections)
    surface.blit(x_label, x_label_rect)
    surface.blit(y_label, y_label_rect)
    surface.blit(y_axis_value, y_axis_value_rect)
    screen.blit(surface, (x, y))
        
def game_loop(args):
    pygame.init()
    pygame.font.init()
    clock = pygame.time.Clock()
    # Initialize the screen
    screen = pygame.display.set_mode((SCREEN_WIDTH, SCREEN_HEIGHT), pygame.HWSURFACE | pygame.DOUBLEBUF)
    pygame.display.set_caption("Line Graph")
    speed_data = []
    velocity_x_data = []
    datas = [speed_data, velocity_x_data]
    last_value = 0
    controller = DualControl()
    data1 = [[]]
    data2 = [[],[]]
    data3 = [[],[],[]]
    data4 = [[]]
    data5 = [[],[],[]]
    data6 = [[]]
    try:
        client = carla.Client(args.host, args.port)
        client.set_timeout(2.0)
        player_vehicle = get_Car(client)

        while True:
            clock.tick_busy_loop(60)
            controller._parse_vehicle_wheel()
           # print("wheel", controller.steer)
           # print("brake", controller.brake)
           # print("throttle", controller.throttle)
            location = get_car_location(player_vehicle)
          #  print("Car Location: ", location)
            velocity = get_car_velocity(player_vehicle)
         #   print("Car Velocity (m/s): ", velocity)
            speed = get_car_speed(player_vehicle) * 3.6
         #   print("Car Speed (km/h): ", speed)
            acceleration = get_car_acceleration(player_vehicle)
         #   print("Car Acceleration: ", acceleration)
            
            # Update data at regular intervals

          

            # update_data(data1, random.randint(0,10))
            # update_data(data2, random.randint(0,10))
            # update_data(data3, random.randint(0,10))
            # Keep only the last MAX_DATA_POINTS data point
            # speed_data = update_data(speed_data, get_car_speed(player_vehicle))
            # velocity_x_data = update_data(velocity_x_data, velocity.x)
            # Update the last value with the latest data point

            # Clear the screen
            screen.fill(BACKGROUND_COLOR)
            update_data(data1, [controller.steer])
            update_data(data2, [controller.throttle, controller.brake])
            update_data(data3, [velocity.x, velocity.y, velocity.z])
            update_data(data4, [speed])
            update_data(data5, [acceleration.x, acceleration.y, acceleration.z])
            update_data(data6, [controller.button_press])

            display_subscreen(screen, data1, [(0, 255, 0)], 30, 0, "time (s)", "Steer Angle",-2,2,5)
            
            display_subscreen(screen, data2, [(255, 0, 0), (0, 255, 0)], 30, SCREEN_HEIGHT//3, "time (s)", "Paddle Value", 0, 1, 4, ["T", "B"])
            display_subscreen(screen, data3, [(255, 0, 0), (0, 255, 0), (0, 0, 255)], 30, 2*SCREEN_HEIGHT//3, "time (s)","velocity (km/h)", -50, 50, 11, ["X", "Y", "Z"])
            display_subscreen(screen, data4, [(0, 255, 0)], 30 + SCREEN_WIDTH //2, 0, "time (s)","speed (km/h)",-100, 100, 11)
            display_subscreen(screen, data5, [(255, 0, 0), (0, 255, 0), (0, 0, 255)], 30 + SCREEN_WIDTH //2, SCREEN_HEIGHT//3, "time (s)","acceleration (km/h^2)", -25, 25, 11, ["X", "Y", "Z"])
            display_subscreen(screen, data6, [(255, 0, 0), (0, 255, 0), (0, 0, 255)], 30 + SCREEN_WIDTH //2, 2* SCREEN_HEIGHT//3, "time (s)","occlusion (button presss", 0, 1, 4)
            #time.sleep(DATA_UPDATE_INTERVAL/1000)
            # Update the display
            pygame.display.flip()
    finally:
        pygame.quit()


def main():
    argparser = argparse.ArgumentParser(
        description='CARLA Manual Control Client')
    argparser.add_argument(
        '-v', '--verbose',
        action='store_true',
        dest='debug',
        help='print debug information')
    argparser.add_argument(
        '--host',
        metavar='H',
        default='127.0.0.1',
        help='IP of the host server (default: 127.0.0.1)')
    argparser.add_argument(
        '-p', '--port',
        metavar='P',
        default=2000,
        type=int,
        help='TCP port to listen to (default: 2000)')
    argparser.add_argument(
        '-a', '--autopilot',
        action='store_true',
        help='enable autopilot')
    argparser.add_argument(
        '--res',
        metavar='WIDTHxHEIGHT',
        default='1280x720',
        help='window resolution (default: 1280x720)')
    argparser.add_argument(
        '--filter',
        metavar='PATTERN',
        default='vehicle.*',
        help='actor filter (default: "vehicle.*")')
    args = argparser.parse_args()

    args.width, args.height = [int(x) for x in args.res.split('x')]
    game_loop(args)

if __name__ == '__main__':        
    main()
