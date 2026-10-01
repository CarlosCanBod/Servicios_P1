#!/usr/bin/python
# encoding: utf-8

import rds2026simulation
import rds2026environment
import rds2026mapperdraw


#
# Robot que explora y construye un mapa
#

robot = rds2026mapperdraw.vacuum_mapper(
    position=(21, 21),
    orientation=0
)


simulation = rds2026simulation.simulation(
    size=(700, 700),
    fps=75,
    environment=rds2026environment.floorplan("cfg_2.py"),
    machine=robot
)


simulation.start()

while simulation.is_running:

    #
    # Q -> salir
    # SPACE -> parar/continuar
    # D -> mostrar/ocultar información de debug
    #
    simulation.update()


simulation.stop()

