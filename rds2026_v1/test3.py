#!/usr/bin/python
# encoding: utf-8

import pygame
import rds2026simulation, rds2026environment, rds2026machines

# init system
robot = rds2026machines.vacuum(position = (21, 21), orientation = 0)
simulation = rds2026simulation.simulation(
    size = (700, 700),
    fps = 15,
    environment = rds2026environment.floorplan("cfg_0.py"),
    machine = robot)

simulation.start()
robot.stop()
while simulation.is_running:

    #
    # update world
    #
    
    # teleoperation
    # capture some keys: K_UP, K_RIGHT, K_LEFT, SPACE, Q
    for event in simulation.read_keyboard():
        if event.type == pygame.KEYDOWN:
            if event.key == pygame.K_LEFT:
                robot.rotate(15)
            elif event.key == pygame.K_RIGHT:
                robot.rotate(-15)
            elif event.key == pygame.K_UP:
                robot.start()
            elif event.key == pygame.K_SPACE:
                if robot.is_running:
                    robot.stop()
                else:
                    robot.start()
            elif event.key == pygame.K_q:
                simulation.is_running = False
                break
            elif event.key == pygame.K_b:
                robot.recharge()
            elif event.key == pygame.K_d:
                if simulation.screen['debugging'] == True:
                    simulation.screen['debugging'] = False
                else:
                    simulation.screen['debugging'] = True
        elif event.type == pygame.KEYUP:
            if event.key == pygame.K_UP:
                robot.stop()

    simulation.update()

# end
simulation.stop()

