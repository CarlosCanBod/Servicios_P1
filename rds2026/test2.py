#!/usr/bin/python
# encoding: utf-8
"""Ejemplo original de movimiento aleatorio, no exploración completa.

vacuum_rotator cambia el rumbo al bloquearse. No guarda visitas ni un mapa,
por lo que puede repetir zonas y no demuestra que haya cubierto todo el suelo.
"""

import rds2026simulation, rds2026environment, rds2026machines
from random import randint

#
# robot básico con rotación aleatoria ante colisiones
#

# init system
robot = rds2026machines.vacuum_rotator(position = (21, 21), orientation = 0)
simulation = rds2026simulation.simulation(
    size = (700, 700),
    fps = 15,
    environment = rds2026environment.floorplan("cfg_0.py"),
    machine = robot)

simulation.start()
while simulation.is_running:

    #
    # update world
    # press Q to quit, SPACE to stop/run and D to show/hide tiles
    #
    simulation.update()

# end
simulation.stop()
