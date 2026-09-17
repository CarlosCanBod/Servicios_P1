#!/usr/bin/python
# encoding: utf-8

"""
Apartado A: Mapeo y Cobertura Completa del Entorno (CCPP)
- Algoritmo de seguimiento de paredes (Wall Following - Regla de la mano derecha)
- Mapeo en rejilla de ocupación (Occupancy Grid: 0=Desconocido, 1=Libre, 2=Obstáculo)
- Visualización en tiempo real del área explorada y exportación del mapa
"""

import math
import pygame
import rds2026simulation
import rds2026environment
import rds2026machines

# Estados de las celdas
CELL_UNKNOWN = 0
CELL_FREE = 1
CELL_OBSTACLE = 2

# Parámetros de navegación
TURN_DEG = 90
COOLDOWN_FRAMES = 2

# Estados del robot
STATE_SEARCH_WALL = "search_wall"
STATE_FOLLOW_WALL = "follow_wall"


class OccupancyGridMap:
    """Rejilla de ocupación para mapeo del piso."""

    def __init__(self, cols, rows):
        self.cols = cols
        self.rows = rows
        # 0: Desconocido, 1: Libre, 2: Obstáculo
        self.grid = [[CELL_UNKNOWN for _ in range(cols)] for _ in range(rows)]

    def mark_cell(self, x, y, state):
        if 0 <= x < self.cols and 0 <= y < self.rows:
            # Una celda que el robot ya pisó físicamente se mantiene libre
            if self.grid[y][x] == CELL_FREE and state == CELL_OBSTACLE:
                return
            self.grid[y][x] = state

    def update(self, robot):
        """Actualiza el mapa según la posición y sensores del robot."""
        # 1. Posición real del robot en coordenadas de celda
        rx, ry = robot.position
        
        # Sincronizar el sensor de odometría del robot por si la clase base no lo inicializó
        robot.sensor['position'] = (rx, ry)
        robot.sensor['orientation'] = robot.orientation
        robot.check_cells()

        # Marcar todas las celdas que cubre el cuerpo del robot (radio ~1 celda)
        for dy in (-1, 0, 1):
            for dx in (-1, 0, 1):
                if dx * dx + dy * dy <= 1.5:
                    cx = int(math.floor(rx + dx * 0.5))
                    cy = int(math.floor(ry + dy * 0.5))
                    self.mark_cell(cx, cy, CELL_FREE)

        # También incluir las celdas calculadas por el robot
        for cell in robot.sensor['cells']:
            if cell is not None:
                self.mark_cell(cell[0], cell[1], CELL_FREE)

        # 2. Vectores direccionales para proyectar obstáculos detectados
        theta_rad = robot.orientation * math.pi / 180.0
        f_dx = math.cos(theta_rad)
        f_dy = -math.sin(theta_rad)

        r_dx = math.sin(theta_rad)
        r_dy = math.cos(theta_rad)

        l_dx = -math.sin(theta_rad)
        l_dy = -math.cos(theta_rad)

        # Obstáculo frontal
        if robot.sensor['proximity']['front'] or getattr(robot, 'forward_path_is_blocked', False):
            ox = int(round(rx + f_dx * 1.5))
            oy = int(round(ry + f_dy * 1.5))
            self.mark_cell(ox, oy, CELL_OBSTACLE)

        # Pared lateral derecha
        if robot.sensor['proximity']['right']:
            ox = int(round(rx + r_dx * 1.5))
            oy = int(round(ry + r_dy * 1.5))
            self.mark_cell(ox, oy, CELL_OBSTACLE)

        # Pared lateral izquierda
        if robot.sensor['proximity']['left']:
            ox = int(round(rx + l_dx * 1.5))
            oy = int(round(ry + l_dy * 1.5))
            self.mark_cell(ox, oy, CELL_OBSTACLE)

    def get_stats(self):
        """Devuelve número de celdas libres, obstáculos y desconocidas."""
        free = sum(row.count(CELL_FREE) for row in self.grid)
        obstacles = sum(row.count(CELL_OBSTACLE) for row in self.grid)
        unknown = sum(row.count(CELL_UNKNOWN) for row in self.grid)
        return free, obstacles, unknown

    def draw_overlay(self, surface, density):
        """Superpone en pantalla el área mapeada con transparencia."""
        overlay = pygame.Surface(surface.get_size(), pygame.SRCALPHA)
        for y in range(self.rows):
            for x in range(self.cols):
                val = self.grid[y][x]
                if val == CELL_FREE:
                    # Verde translúcido para celdas transitadas
                    pygame.draw.rect(
                        overlay,
                        (50, 220, 100, 80),
                        (x * density, y * density, density, density)
                    )
                elif val == CELL_OBSTACLE:
                    # Rojo translúcido para obstáculos detectados
                    pygame.draw.rect(
                        overlay,
                        (230, 50, 50, 130),
                        (x * density, y * density, density, density)
                    )
        surface.blit(overlay, (0, 0))

    def save_to_file(self, filename="mapa_grid.txt"):
        """Exporta la matriz del mapa a un archivo."""
        with open(filename, "w") as f:
            for row in self.grid:
                f.write("".join(str(c) for c in row) + "\n")
        print(f"\n[MAPA] Guardado correctamente en {filename}")


def main():
    # 1. Inicializar robot y sincronizar posición de sensores
    robot = rds2026machines.vacuum(position=(25, 25), orientation=0)
    robot.sensor['position'] = (robot.position[0], robot.position[1])
    robot.sensor['orientation'] = robot.orientation

    floor = rds2026environment.floorplan("cfg_0.py")
    sim = rds2026simulation.simulation(
        size=(700, 700),
        fps=30,
        environment=floor,
        machine=robot
    )

    cols, rows = floor.size
    grid_map = OccupancyGridMap(cols, rows)

    # Enganchar el dibujado del mapa para que se pinte en cada frame
    original_update_extra = floor.update_extra
    def custom_update_extra():
        original_update_extra()
        dd = sim.screen['window']['density']
        grid_map.draw_overlay(sim.screen['display'], dd)
    floor.update_extra = custom_update_extra

    sim.start()

    state = STATE_SEARCH_WALL
    cooldown = 0

    def prox_f():
        return robot.sensor['proximity']['front'] or getattr(robot, 'forward_path_is_blocked', False)

    def prox_r():
        return robot.sensor['proximity']['right']

    def rotate(deg):
        nonlocal cooldown
        robot.stop()
        robot.rotate(deg)
        cooldown = COOLDOWN_FRAMES
        robot.start()

    if not robot.is_running:
        robot.start()

    step_counter = 0

    print("=== Apartado A: Mapeo y Seguimiento de Paredes ===")
    print("Controles: [Q] Salir y Guardar | [ESPACIO] Pausar/Reanudar | [D] Debug")

    while sim.is_running:
        # Control de simulación
        sim.update()

        # Actualizar mapa de ocupación con la posición real
        grid_map.update(robot)

        step_counter += 1
        if step_counter % 30 == 0:
            free, obs, unk = grid_map.get_stats()
            print(f"[Progreso] Libres: {free:3d} | Obstáculos: {obs:3d} | Inexploradas: {unk:4d} | Pos: ({robot.position[0]:.1f}, {robot.position[1]:.1f})")

        # Lógica de navegación (Seguidor de paredes)
        if cooldown > 0:
            cooldown -= 1
            continue

        if state == STATE_SEARCH_WALL:
            if prox_f():
                rotate(+TURN_DEG)
                state = STATE_FOLLOW_WALL
            else:
                if not robot.is_running:
                    robot.start()

        elif state == STATE_FOLLOW_WALL:
            if prox_f():
                rotate(+TURN_DEG)      # Esquina interior -> giro a la izquierda
            elif not prox_r():
                rotate(-TURN_DEG)      # Pérdida de pared -> doblar a la derecha
            else:
                if not robot.is_running:
                    robot.start()

    # Guardar mapa al salir
    grid_map.save_to_file("mapa_grid.txt")
    sim.stop()


if __name__ == "__main__":
    main()
