#!/usr/bin/python
# encoding: utf-8
"""Ejemplo original de batería y depuración con reacción aleatoria al bloqueo.

simulate_battery=True descuenta energía al avanzar/girar. La práctica no
implementa retorno automático al cargador; este ejemplo no demuestra esa función.
"""

import rds2026simulation, rds2026environment, rds2026machines
from random import randint

# init system
simulation = rds2026simulation.simulation(
    size = (700, 700),
    fps = 15,
    environment = rds2026environment.floorplan("cfg_0.py"),
    machine = rds2026machines.vacuum_rotator(
        position = (21, 21),
        orientation = 0,
        simulate_battery = True)
    )

simulation.start(debug = True)
while simulation.is_running:

    #
    # update world
    # press Q to quit, SPACE to stop/run and D to show/hide tiles
    #
    simulation.update()

# end
simulation.stop()
