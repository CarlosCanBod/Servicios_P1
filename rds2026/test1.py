#!/usr/bin/python
# encoding: utf-8
"""Ejemplo original: abrir y dibujar el mundo sin robot. No resuelve A/B/C.

El bucle repinta mientras la ventana esté abierta; Q o cerrar termina.
Para enseñar la solución final utilizar apartado_a.py, apartado_b.py y apartado_c.py.
"""

import rds2026simulation, rds2026environment, rds2026machines

# init system
simulation = rds2026simulation.simulation(
    size = (700, 700),
    fps = 15,
    environment = rds2026environment.floorplan("cfg_0.py"))

simulation.start()
while simulation.is_running:

    #
    # update world
    # press Q to quit and SPACE to stop/run
    #
    simulation.update()

# end
simulation.stop()
