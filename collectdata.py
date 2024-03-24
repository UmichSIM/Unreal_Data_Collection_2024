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
# from manual_control_steeringwheel import World, HUD
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
DATA_UPDATE_INTERVAL = 500  # Update data every 100 milliseconds
LINE_COLOR = (0, 0, 0)

# ==============================================================================
# -- World ---------------------------------------------------------------------
# ==============================================================================


class World(object):
    def __init__(self, carla_world, hud, actor_filter):
        self.world = carla_world
        self.hud = hud
        self.player = None
        self.collision_sensor = None
        self.lane_invasion_sensor = None
        self.gnss_sensor = None
        self.camera_manager = None
        self._weather_presets = find_weather_presets()
        self._weather_index = 0
        self._actor_filter = actor_filter
        # self.restart()
        self.world.on_tick(hud.on_world_tick)

    def restart(self):
        # Keep same camera config if the camera manager exists.
        cam_index = self.camera_manager.index if self.camera_manager is not None else 0
        cam_pos_index = self.camera_manager.transform_index if self.camera_manager is not None else 0
        # Get a random blueprint.
        blueprint = random.choice(self.world.get_blueprint_library().filter(self._actor_filter))
        blueprint.set_attribute('role_name', 'hero')
        if blueprint.has_attribute('color'):
            color = random.choice(blueprint.get_attribute('color').recommended_values)
            blueprint.set_attribute('color', color)
        # Spawn the player.
        if self.player is not None:
            spawn_point = self.player.get_transform()
            spawn_point.location.z += 2.0
            spawn_point.rotation.roll = 0.0
            spawn_point.rotation.pitch = 0.0
            self.destroy()
            self.player = self.world.try_spawn_actor(blueprint, spawn_point)
        while self.player is None:
            spawn_points = self.world.get_map().get_spawn_points()
            spawn_point = random.choice(spawn_points) if spawn_points else carla.Transform()
            self.player = self.world.try_spawn_actor(blueprint, spawn_point)
        # Set up the sensors.
        self.collision_sensor = CollisionSensor(self.player, self.hud)
        self.lane_invasion_sensor = LaneInvasionSensor(self.player, self.hud)
        self.gnss_sensor = GnssSensor(self.player)
        self.camera_manager = CameraManager(self.player, self.hud)
        self.camera_manager.transform_index = cam_pos_index
        self.camera_manager.set_sensor(cam_index, notify=False)
        actor_type = get_actor_display_name(self.player)
        self.hud.notification(actor_type)

    def next_weather(self, reverse=False):
        self._weather_index += -1 if reverse else 1
        self._weather_index %= len(self._weather_presets)
        preset = self._weather_presets[self._weather_index]
        self.hud.notification('Weather: %s' % preset[1])
        self.player.get_world().set_weather(preset[0])

    def tick(self, clock):
        self.hud.tick(self, clock)

    def render(self, display):
        self.camera_manager.render(display)
        self.hud.render(display)

    def destroy(self):
        sensors = [
            self.camera_manager.sensor,
            self.collision_sensor.sensor,
            self.lane_invasion_sensor.sensor,
            self.gnss_sensor.sensor]
        for sensor in sensors:
            if sensor is not None:
                sensor.stop()
                sensor.destroy()
        if self.player is not None:
            self.player.destroy()


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
        
    def _parse_vehicle_wheel(self):
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

def get_Car(client):
    world = client.get_world()
        
    print(world.get_actors())
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



def draw_labels(surface,screen):
    font = pygame.font.Font(None, 16)
    
    # X label
    x_label = font.render("Time (s)", True, LINE_COLOR)
    x_label_rect = x_label.get_rect()
    x_label_rect.center = (SURFACE_WIDTH // 2, SURFACE_HEIGHT-15)
    surface.blit(x_label, x_label_rect)
    
    # Y label
    y_label = font.render("Value", True, LINE_COLOR)
    y_label = pygame.transform.rotate(y_label, 90)  # Rotate for vertical display
    y_label_rect = y_label.get_rect()
    y_label_rect.center = (10, SURFACE_HEIGHT // 2)
    surface.blit(y_label, y_label_rect)

    # Draw y Axis Rulers
    for i in range(-2,7,1):
        y_axis_value = font.render("{:d}".format(i*10), True, (255, 165, 0))  # Display "0" at the left
        y_axis_value_rect = y_axis_value.get_rect()
        y_axis_value_rect.center = (30, ((1 - 10*i / 100) * SURFACE_HEIGHT) -75 )
        surface.blit(y_axis_value, y_axis_value_rect)

    # pygame.draw.line(screen, (255, 165, 0), (GRAPH_X, GRAPH_Y + GRAPH_HEIGHT - 50), (GRAPH_X + GRAPH_WIDTH, GRAPH_Y + GRAPH_HEIGHT - 50), 2)


    # Display the last value to the right of the graph
    # if last_value is None:
    #     last_value = 0

    # last_value_label = font.render(f"{last_value}", True, LINE_COLOR)
    # last_value_rect = last_value_label.get_rect()
    # last_value_rect.midleft = (SURFACE_WIDTH + 10,(1 - last_value / 100) * SURFACE_HEIGHT - 50)
    # surface.blit(last_value_label, last_value_rect)
    
    return x_label, x_label_rect, y_label, y_label_rect, y_axis_value, y_axis_value_rect
    
def draw_line(graph_surface,data,color ):
    # Draw data points and lines
    if len(data) > 1:
        for i in range(len(data) - 1):
            x1 = i * (SURFACE_WIDTH // (MAX_DATA_POINTS - 1))
            y1 = SURFACE_HEIGHT - (data[i] * (SURFACE_HEIGHT / 100)) - 3*(SURFACE_HEIGHT // 10)
            x2 = (i + 1) * (SURFACE_WIDTH // (MAX_DATA_POINTS - 1))
            y2 = SURFACE_HEIGHT - (data[i + 1] * (SURFACE_HEIGHT / 100)) - 3*(SURFACE_HEIGHT // 10)
            pygame.draw.line(graph_surface, color, (x1+40, y1), (x2+40, y2), 2)
            # pygame.draw.line(graph_surface, color, (x1, y1), (x2, y2), 2)

# def draw_graph(screen, speed_data, velocity_x_data, X):
#     graph_surface = pygame.Surface((SURFACE_WIDTH-200, SURFACE_HEIGHT-200))
#     graph_surface.fill(BACKGROUND_COLOR)
    
#     # Draw grid lines
#     for i in range(0, SURFACE_HEIGHT, 20):
#         pygame.draw.line(graph_surface, (200, 200, 200), (0, i), (SURFACE_WIDTH, i), 1)
    
#     draw_line(graph_surface, speed_data, (0, 255, 255))
#     draw_line(graph_surface, velocity_x_data, (255, 0, 0))

#     screen.blit(graph_surface, (GRAPH_X, GRAPH_Y))

def draw_graph2(surface, screen, data, color, x, y):
    surface.fill(BACKGROUND_COLOR)
    # Draw grid lines
    for i in range(SURFACE_HEIGHT // 10, SURFACE_HEIGHT, SURFACE_HEIGHT // 10):
        pygame.draw.line(surface, (200, 200, 200), (40, i), (SURFACE_WIDTH, i), 1)
    # for i, data in enumerate(datas):
    draw_line(surface, data, color)
    

def update_data(data, point):
    # Simulate data update (replace this with your data source)
    data.append(point)
    # print("updating", data)
    # Keep only the last MAX_DATA_POINTS data points
    if len(data) > MAX_DATA_POINTS:
        data.pop(0)
        # print("deleting")

    return data

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

def display_subscreen(screen, data, color, x, y):
    surface = pygame.Surface((SURFACE_WIDTH, SURFACE_HEIGHT))
    draw_graph2(surface, screen, data, color, 30, 600)
            # Draw labels and the last value
    x_label, x_label_rect, y_label, y_label_rect, y_axis_value, y_axis_value_rect = \
    draw_labels(surface, screen)
    surface.blit(x_label, x_label_rect)
    surface.blit(y_label, y_label_rect)
    surface.blit(y_axis_value, y_axis_value_rect)
    screen.blit(surface, (x, y))
        
def game_loop(args):
    pygame.init()
    pygame.font.init()
    clock = pygame.time.Clock()
    # Initialize the screen
    screen = pygame.display.set_mode((SCREEN_WIDTH, SCREEN_HEIGHT))
    pygame.display.set_caption("Line Graph")
    speed_data = []
    velocity_x_data = []
    datas = [speed_data, velocity_x_data]
    last_value = 0
    # controller = DualControl()
    data1 = []
    data2 = []
    data3 = []
    try:
        client = carla.Client(args.host, args.port)
        client.set_timeout(2.0)
        # hud = HUD(args.width, args.height)
        # world = World(client.get_world(), hud, args.filter)
        # player_vehicle = get_Car(client);



        while True:
            clock.tick_busy_loop(60)
            # controller._parse_vehicle_wheel()
            # print("wheel", controller.steer)
            # print("brake", controller.brake)
            # print("throttle", controller.throttle)
            # velocity = get_car_velocity(player_vehicle) 
            # print("Car Velocity (m/s): ", velocity)
            # print("Car Speed (km/h): ", get_car_speed(player_vehicle) * 3.6)
            # location = get_car_location(player_vehicle)
            # print("Car Location: ", location)
            # acceleration = get_car_acceleration(player_vehicle)
            # print("Car Acceleration: ", acceleration)
            # Update data at regular intervals
            # points = [get_car_speed(player_vehicle), velocity.x]

            
            # for i, data in enumerate(datas):
            #     data.append(points[i])
            #     if len(data) > MAX_DATA_POINTS:
            #         data.pop(0)

            # update_data(data1, random.randint(0,10))
            # update_data(data2, random.randint(0,10))
            # update_data(data3, random.randint(0,10))
            # Keep only the last MAX_DATA_POINTS data point
            # speed_data = update_data(speed_data, get_car_speed(player_vehicle))
            # velocity_x_data = update_data(velocity_x_data, velocity.x)
            # Update the last value with the latest data point
            # if speed_data:
            #     last_value = speed_data[-1]

            # Clear the screen
            screen.fill(BACKGROUND_COLOR)
            
            update_data(data1, random.randint(-20,50))
            update_data(data2, random.randint(-20,50))
            update_data(data3, random.randint(-20,50))
            
            display_subscreen(screen, data1, (0, 255, 0), 30, 0)
            display_subscreen(screen, data2, (255, 0, 0), 30, SCREEN_HEIGHT//3)
            display_subscreen(screen, data3, (255, 0, 0), 30, 2*SCREEN_HEIGHT//3)
            display_subscreen(screen, data1, (0, 255, 0), 30 + SCREEN_WIDTH //2, 0)
            display_subscreen(screen, data2, (255, 0, 0), 30 + SCREEN_WIDTH //2, SCREEN_HEIGHT//3)
            display_subscreen(screen, data3, (255, 0, 0), 30 + SCREEN_WIDTH //2, 2*SCREEN_HEIGHT//3)


            # Draw the graph
            # colors = [(0, 255, 255), (255, 0, 0)]
            # surface = pygame.Surface((SURFACE_WIDTH, SURFACE_HEIGHT))
            # surface1 = pygame.Surface((SURFACE_WIDTH, SURFACE_HEIGHT))
            # draw_graph2(surface, screen, datas, colors, 30, 30)
            # draw_graph2(surface1, screen, datas, colors, 30, 600)
            # # Draw labels and the last value
            # x_label, x_label_rect, y_label, y_label_rect, y_axis_value, y_axis_value_rect, last_value_label, last_value_rect = \
            #     draw_labels(surface, screen, last_value)
            # x_label1, x_label_rect1, y_label1, y_label_rect1, y_axis_value1, y_axis_value_rect1, last_value_label1, last_value_rect1 = \
            #     draw_labels(surface1, screen, last_value)
            # surface.blit(x_label, x_label_rect)
            # surface.blit(y_label, y_label_rect)
            # surface.blit(y_axis_value, y_axis_value_rect)
            # surface1.blit(x_label1, x_label_rect1)
            # surface1.blit(y_label1, y_label_rect1)
            # surface1.blit(y_axis_value1, y_axis_value_rect1)
            # screen.blit(surface1, (30, 30+SURFACE_HEIGHT))
            # screen.blit(surface, (30, 30))
            # if last_value_label is not None:
            #     screen.blit(last_value_label, last_value_rect)

            pygame.event.get()
            time.sleep(DATA_UPDATE_INTERVAL/1000)
            
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
