#!/usr/bin/python
# encoding: utf-8

import pygame
from pygame.locals import *

class simulation():

    environment = None
    machine = None
    is_running = False

    def __init__(self, size, fps, environment, machine = None):
        self.screen = {
            'display': None,
            'window': {
                'size': size,
                'density': -1,
                'fps': fps,
            },
            'debugging': False
        }
        self.clock = None
        self.screen['window']['density'] = min(
            size[0] // environment.size[0],
            size[1] // environment.size[1]
        )

        # init models
        self.environment = environment
        self.environment.init_images(self.screen)

        self.machine = machine
        if machine is not None:
            self.machine.init_images(
                self.screen,
                self.environment.objects,
                self.environment.recharge_tiles
            )

    def start(self, debug = False):
        pygame.init()
        self.screen['display'] = pygame.display.set_mode((
            self.screen['window']['size'][0],
            self.screen['window']['size'][1]
        ))
        pygame.display.set_caption('rds2026 SIM')
        self.clock = pygame.time.Clock()
        self.is_running = True
        if debug == True:
            self.screen['debugging'] = True
        if self.machine is not None:
            self.machine.start()
        if debug == True:
            print("DEBUG: window: {}".format(self.screen))

    def stop(self):
        if self.machine is not None:
            self.machine.stop()
        pygame.quit()

    def read_keyboard(self):
        return pygame.event.get()

    def update(self):
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                self.is_running = False
            if event.type == pygame.KEYDOWN:
                if event.key == pygame.K_q:
                    self.is_running = False
                elif event.key == pygame.K_SPACE:
                    if self.machine.is_running:
                        self.machine.stop()
                    else:
                        self.machine.start()
                elif event.key == pygame.K_d:
                    if self.screen['debugging'] == True:
                        self.screen['debugging'] = False
                    else:
                        self.screen['debugging'] = True

        if self.environment is not None:
            self.environment.update()
        if self.machine is not None:
            self.machine.update()
        if self.environment is not None:
            self.environment.update_extra()
        pygame.display.update()
        self.clock.tick(self.screen['window']['fps'])

