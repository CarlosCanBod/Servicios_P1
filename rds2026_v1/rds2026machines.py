#!/usr/bin/python
# encoding: utf-8

import math, pygame
from random import randint

VACUUM_SIZE = 2
VACUUM_SPEED = VACUUM_SIZE/4.0

BATTERY_SIZE = 100_000_000

#
# básico
#
class vacuum():

    objects = None
    chargers = None

    vacuum_img = None
    vacuum_img_bak = None

    position = (0, 0)
    velocity = (0, 0)
    orientation = 0
    is_running = False
    running_on_battery = False

    stats_collisions = 0
    current_collision_already_counted = False
    forward_path_is_blocked = False

    sensor = {
        'position': (0, 0),
        'orientation': 0,
        'proximity': {'left':False, 'front':False, 'right':False},
        'detection': '',
        'cells': [None, None, None, None],
        'battery': BATTERY_SIZE
    }

    screen = None
    proximity_bbox = {'left':None, 'front':None, 'right':None}

    def __init__(self, position, orientation, simulate_battery = False):
        self.position = (position[0], position[1])
        self.orientation = orientation
        self.running_on_battery = simulate_battery

    def init_images(self, screen, static_objects, recharge_tiles):
        self.screen = screen
        dd = screen['window']['density']
        self.objects = static_objects
        self.chargers = recharge_tiles
        # image
        img = pygame.transform.scale(
            pygame.image.load("img/vacuum.png"),
                (VACUUM_SIZE * dd, VACUUM_SIZE * dd)
        )
        img_rect = img.get_rect()
        img_rect.x = (self.position[0] - VACUUM_SIZE//2) * dd
        img_rect.y = (self.position[1] - VACUUM_SIZE//2) * dd
        self.vacuum_img = {'img':img, 'bbox':img_rect.copy()}
        self.vacuum_img_bak = {'img':img.copy(), 'bbox':img_rect.copy()}
        # sensors
        self.check_proximity()
        self.check_cells()

    def check_proximity(self):
        if self.forward_path_is_blocked:
            return
        # front
        dd = self.screen['window']['density']
        t1 = self.vacuum_img['bbox'].copy()
        t1.x = (self.position[0] - VACUUM_SIZE//2) * dd
        t1.y = (self.position[1] - VACUUM_SIZE//2) * dd
        t1.x += (self.velocity[0] * dd)
        t1.y += (self.velocity[1] * dd)
        # left
        t0 = t1.copy()
        t0.x += (self.velocity[1] * dd)
        t0.y -= (self.velocity[0] * dd)
        # right
        t2 = t1.copy()
        t2.x -= (self.velocity[1] * dd)
        t2.y += (self.velocity[0] * dd)
        self.sensor['proximity'] = {'left':False, 'front':False, 'right':False}
        self.sensor['detection'] = ''
        for i in self.objects:
            if self.sensor['proximity']['front'] == False and i['bbox'].colliderect(t1):
                self.sensor['proximity']['front'] = True
                self.sensor['detection'] = i['desc']
            if self.sensor['proximity']['left'] == False and i['bbox'].colliderect(t0):
                self.sensor['proximity']['left'] = True
            if self.sensor['proximity']['right'] == False and i['bbox'].colliderect(t2):
                self.sensor['proximity']['right'] = True
        self.proximity_bbox = {'left':t0, 'front':t1, 'right':t2}

    def check_cells(self):
        self.sensor['cells'][0] = (
            math.floor(self.sensor['position'][0] - VACUUM_SIZE/4.0),
            math.floor(self.sensor['position'][1] - VACUUM_SIZE/4.0)
        )
        self.sensor['cells'][1] = (
            math.floor(self.sensor['position'][0] + VACUUM_SIZE/4.0),
            math.floor(self.sensor['position'][1] - VACUUM_SIZE/4.0)
        )
        self.sensor['cells'][2] = (
            math.floor(self.sensor['position'][0] - VACUUM_SIZE/4.0),
            math.floor(self.sensor['position'][1] + VACUUM_SIZE/4.0)
        )
        self.sensor['cells'][3] = (
            math.floor(self.sensor['position'][0] + VACUUM_SIZE/4.0),
            math.floor(self.sensor['position'][1] + VACUUM_SIZE/4.0)
        )

    def check_collision_in_next_step(self):
        self.check_proximity()
        return self.sensor['proximity']['front']

    def start(self):
        self.is_running = True
        self.velocity = (
            (VACUUM_SPEED * math.cos(self.orientation * math.pi/180.0)),
            -(VACUUM_SPEED * math.sin(self.orientation * math.pi/180.0))
        )

    def stop(self):
        self.is_running = False
        self.velocity = (0, 0)

    def recharge(self):
        ll = pygame.Rect(
            (self.position[0] - VACUUM_SIZE//2,
            self.position[0] + VACUUM_SIZE//2),
            (VACUUM_SIZE, VACUUM_SIZE)
        )
        for r in self.chargers:
            tile = pygame.Rect((r[0], r[1]), (1, 1))
            if ll.colliderect(tile):
                self.sensor['battery'] = BATTERY_SIZE
                print("DEBUG: recharged battery")
                return
        print("DEBUG: not over a recharge tile!")

    def rotate(self, n):
        if self.running_on_battery: self.sensor['battery'] -= (abs(math.floor(n/15.0)))
        if self.sensor['battery'] > 0:
            self.forward_path_is_blocked = False
            self.orientation += n
            self.orientation %= 360
            if self.is_running == True:
                self.velocity = (
                    (VACUUM_SPEED * math.cos(self.orientation*math.pi/180.0)),
                    -(VACUUM_SPEED * math.sin(self.orientation*math.pi/180.0))
                )
            # update
            self.sensor['orientation'] += n
            self.sensor['orientation'] %= 360
            # sensors
            #self.check_proximity()
            #self.check_cells()
            # update image
            r_img = pygame.transform.rotate(self.vacuum_img_bak['img'], self.orientation)
            p_img = r_img.get_rect().center
            c_img = r_img.subsurface(pygame.Rect(
                ((p_img[0] - self.vacuum_img['bbox'].width//2),
                (p_img[1] - self.vacuum_img['bbox'].height//2)),
                (self.vacuum_img['bbox'].width, self.vacuum_img['bbox'].height))
            )
            self.vacuum_img = {'img':c_img, 'bbox':self.vacuum_img['bbox']}
        else:
            print("DEBUG: empty battery!")
            self.stop()

    def collision_strategy(self):
        self.stop()

    def update(self):
        dd = self.screen['window']['density']
        self.check_proximity()
        if self.is_running:
            if not self.check_collision_in_next_step():
                # running free and moving
                if self.running_on_battery: self.sensor['battery'] -= 1
                if self.sensor['battery'] > 0:
                    self.position = (
                        self.position[0] + self.velocity[0],
                        self.position[1] + self.velocity[1]
                    )
                    self.current_collision_already_counted = False
                    # update
                    self.sensor['position'] = (
                        self.sensor['position'][0] + self.velocity[0],
                        self.sensor['position'][1] + self.velocity[1]
                    )
                    # sensors
                    self.check_proximity()
                    self.check_cells()
                else:
                    print("DEBUG: empty battery!")
                    self.stop()
            else:
                # collision
                self.collision_strategy()
                if self.current_collision_already_counted == False:
                    self.current_collision_already_counted = True
                    self.stats_collisions += 1
                    self.forward_path_is_blocked = True
                    if self.screen['debugging']:
                        print("DEBUG: collision with '{}'".format(self.sensor['detection']))
            self.check_cells()
        # show
        rect = self.vacuum_img['bbox'].copy()
        rect.x = (self.position[0] - VACUUM_SIZE//2) * dd
        rect.y = (self.position[1] - VACUUM_SIZE//2) * dd
        # robot main image
        self.screen['display'].blit(self.vacuum_img['img'], rect.copy())
        # lines after collision
        if self.current_collision_already_counted:
            if not self.screen['debugging']:
                # lines
                pygame.draw.circle(self.screen['display'], (250, 0, 0),
                    (rect.x+rect.width//2, rect.y+rect.height//2),
                    int(0.6*VACUUM_SIZE * dd), 1)
                pygame.draw.circle(self.screen['display'], (250, 0, 0),
                    (rect.x+rect.width//2, rect.y+rect.height//2),
                    int(0.7*VACUUM_SIZE * dd), 1)
        if self.screen['debugging']:
            # robot
            pygame.draw.rect(self.screen['display'], (250, 50, 50), rect, 2)
            # proximity sensor
            pygame.draw.rect(self.screen['display'], (250, 50, 250), self.proximity_bbox['left'],
                 2 if self.sensor['proximity']['left'] else 1)
            pygame.draw.rect(self.screen['display'], (250, 50, 250), self.proximity_bbox['front'],
                 2 if self.sensor['proximity']['front'] else 1)
            pygame.draw.rect(self.screen['display'], (250, 50, 250), self.proximity_bbox['right'],
                 2 if self.sensor['proximity']['right'] else 1)
                 
class vacuum_rotator(vacuum):
    # random rotate on collision
    def collision_strategy(self):
        self.rotate(randint(-45, +45))

class vacuum_zero(vacuum):
    # do nothing on collision
    def collision_strategy(self):
        None

