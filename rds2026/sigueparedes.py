#!/usr/bin/python
# encoding: utf-8

import rds2026simulation, rds2026environment, rds2026machines

# --- Parámetros simples ---
TURN_DEG = 90
COOLDOWN_FRAMES = 2

# --- Estados ---
SEARCH_WALL   = "search_wall"
FOLLOW_WALL_R = "follow_wall_right"

# --- Robot y simulación ---
robot = rds2026machines.vacuum(position=(25,25), orientation=0)
sim = rds2026simulation.simulation(
    size=(700,700), fps=30,
    environment=rds2026environment.floorplan("cfg_0.py"),
    machine=robot
)
sim.start()

state = SEARCH_WALL
cooldown = 0

def prox_f():  # frente bloqueado
    return robot.sensor['proximity']['front'] or getattr(robot, 'forward_path_is_blocked', False)

def prox_r():  # pared a la derecha (pegada)
    return robot.sensor['proximity']['right']

def rotate(deg):
    global cooldown
    robot.stop()
    robot.rotate(deg)
    cooldown = COOLDOWN_FRAMES
    robot.start()

# Arranca en avance
if not robot.is_running:
    robot.start()

while sim.is_running:
    sim.update()

    # respetar cooldown tras un giro (seguimos avanzando si es posible)
    if cooldown > 0:
        cooldown -= 1
        # si estamos en búsqueda y hay bloqueo, ya giraremos al acabar el cooldown
        continue

    if state == SEARCH_WALL:
        # Avanza hasta tocar pared de frente
        if prox_f():
            # enganchar pared a la derecha: giro a la IZQUIERDA 90°
            rotate(+TURN_DEG)
            state = FOLLOW_WALL_R
        else:
            if not robot.is_running:
                robot.start()

    elif state == FOLLOW_WALL_R:
        # Regla mano derecha (prioridad exacta solicitada):
        # 1) Frente bloqueado -> girar IZQUIERDA
        # 2) No hay pared a la derecha -> girar DERECHA
        # 3) Si hay pared a la derecha y frente libre -> seguir recto
        if prox_f():
            rotate(+TURN_DEG)          # esquina cerrada
        elif not prox_r():
            rotate(-TURN_DEG)          # se "pierde" la pared: dobla a la derecha
        else:
            # pared a la derecha y frente libre -> seguir recto
            if not robot.is_running:
                robot.start()

# end
sim.stop()
