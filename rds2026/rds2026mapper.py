#!/usr/bin/python
# encoding: utf-8

import math
from collections import deque

import rds2026machines


# ============================================================
# VALORES DEL MAPA
# ============================================================

UNKNOWN = None
WALL = 0
FREE = 1


class vacuum_mapper(rds2026machines.vacuum):

    def __init__(self, position, orientation=0, simulate_battery=False):

        super().__init__(
            position,
            orientation,
            simulate_battery
        )

        # ----------------------------------------------------
        # MAPA
        #
        # (x, y) -> 0 pared / 1 libre
        #
        # Las posiciones que no aparecen son UNKNOWN.
        # ----------------------------------------------------

        self.map = {}

        # Celdas libres conocidas pero todavía no exploradas
        self.frontier = set()

        # Celdas que ya hemos explorado
        self.explored = set()

        # Camino que estamos siguiendo
        self.path = []

        # Objetivo actual
        self.target = None

        # Estado del robot
        #
        # explore:
        #       estudiar la celda actual
        #
        # navigate:
        #       desplazarse hasta una frontier
        #
        # finished:
        #       mapa terminado
        self.behaviour = "explore"

        # Orientaciones que vamos a utilizar
        self.directions = {
            "right": 0,
            "up": 90,
            "left": 180,
            "down": 270
        }

        # Para saber cuándo hemos cambiado de celda
        self.previous_cell = self.current_cell()

        # Matriz final
        self.final_matrix = None

        # Mensaje para no imprimir continuamente
        self.finished_printed = False

    # ============================================================
    # COORDENADAS
    # ============================================================

    def current_cell(self):
        """
        Convierte la posición real del robot a una celda.

        Como el robot se mueve en pasos de VACUUM_SPEED,
        utilizamos round para identificar la celda más cercana.
        """

        return (
            int(round(self.position[0])),
            int(round(self.position[1]))
        )

    # ============================================================
    # VECINOS
    # ============================================================

    def get_neighbour(self, cell, direction):

        x, y = cell

        if direction == "right":
            return (x + 1, y)

        if direction == "left":
            return (x - 1, y)

        if direction == "up":
            return (x, y - 1)

        if direction == "down":
            return (x, y + 1)

        return None

    # ============================================================
    # ORIENTACIÓN
    # ============================================================

    def direction_from_orientation(self):

        orientation = self.orientation % 360

        if orientation < 45 or orientation >= 315:
            return "right"

        if orientation < 135:
            return "up"

        if orientation < 225:
            return "left"

        return "down"

    def turn_to(self, direction):

        desired = self.directions[direction]

        current = self.orientation % 360

        difference = desired - current

        # Convertir a [-180, 180]
        while difference > 180:
            difference -= 360

        while difference < -180:
            difference += 360

        if abs(difference) < 1:
            return True

        self.stop()

        self.rotate(difference)

        return True

    # ============================================================
    # SENSOR
    # ============================================================

    def sense_direction(self, direction):
        """
        Hace que el sensor frontal mire en una dirección concreta.

        No movemos el robot.
        Solamente utilizamos temporalmente velocity para que
        check_proximity() calcule correctamente el sensor.
        """

        desired = self.directions[direction]

        current = self.orientation % 360

        difference = desired - current

        while difference > 180:
            difference -= 360

        while difference < -180:
            difference += 360

        if abs(difference) > 0:
            self.stop()
            self.rotate(difference)

        # check_proximity utiliza velocity para calcular
        # la posición del sensor frontal.
        old_velocity = self.velocity

        angle = self.orientation * math.pi / 180.0

        self.velocity = (
            rds2026machines.VACUUM_SPEED * math.cos(angle),
            -rds2026machines.VACUUM_SPEED * math.sin(angle)
        )

        self.forward_path_is_blocked = False

        self.check_proximity()

        blocked = self.sensor["proximity"]["front"]

        detection = self.sensor["detection"]

        # Restaurar velocidad
        self.velocity = old_velocity

        return blocked, detection

    # ============================================================
    # MAPA
    # ============================================================

    def set_wall(self, cell):

        self.map[cell] = WALL

        # Una pared nunca puede estar en frontier
        if cell in self.frontier:
            self.frontier.remove(cell)

    def set_free(self, cell):

        self.map[cell] = FREE

        # Si ya está explorada no hace falta frontier
        if cell not in self.explored:
            self.frontier.add(cell)

    # ============================================================
    # EXPLORACIÓN
    # ============================================================

    def explore_current_cell(self):

        current = self.current_cell()

        print("")
        print("Explorando celda:", current)

        # La celda donde estamos es libre
        self.set_free(current)

        # La estamos explorando ahora
        self.explored.add(current)

        if current in self.frontier:
            self.frontier.remove(current)

        # --------------------------------------------------------
        # Miramos las cuatro direcciones
        # --------------------------------------------------------

        for direction in [
            "up",
            "right",
            "down",
            "left"
        ]:

            neighbour = self.get_neighbour(
                current,
                direction
            )

            blocked, detection = self.sense_direction(direction)

            if blocked:

                self.set_wall(neighbour)

                print(
                    "  {} -> PARED ({})".format(
                        direction,
                        detection
                    )
                )

            else:

                self.set_free(neighbour)

                print(
                    "  {} -> LIBRE".format(
                        direction
                    )
                )

        self.stop()

    # ============================================================
    # BFS
    # ============================================================

    def find_path(self, start, goal):
        """
        BFS sobre las celdas conocidas como libres.
        """

        if start == goal:
            return []

        queue = deque()

        queue.append(start)

        previous = {
            start: None
        }

        while queue:

            current = queue.popleft()

            neighbours = [
                self.get_neighbour(current, "up"),
                self.get_neighbour(current, "right"),
                self.get_neighbour(current, "down"),
                self.get_neighbour(current, "left")
            ]

            for neighbour in neighbours:

                # Solo podemos atravesar celdas conocidas
                # como libres.
                if self.map.get(neighbour) != FREE:
                    continue

                # Ya visitada por BFS
                if neighbour in previous:
                    continue

                previous[neighbour] = current

                if neighbour == goal:

                    # Reconstruir camino
                    path = []

                    node = goal

                    while node != start:

                        path.append(node)

                        node = previous[node]

                    path.reverse()

                    return path

                queue.append(neighbour)

        return None

    # ============================================================
    # ELEGIR FRONTIER
    # ============================================================

    def choose_frontier(self):

        if not self.frontier:
            return None

        current = self.current_cell()

        # Buscamos la frontier más cercana utilizando BFS.
        #
        # Esto evita recorrer innecesariamente todo el mapa.
        best_target = None
        best_path = None

        for candidate in list(self.frontier):

            path = self.find_path(
                current,
                candidate
            )

            if path is None:
                continue

            if best_path is None or len(path) < len(best_path):

                best_target = candidate
                best_path = path

        if best_target is not None:

            self.frontier.discard(best_target)

            return best_target, best_path

        return None

    # ============================================================
    # MOVERSE
    # ============================================================

    def move_one_step(self):

        if not self.path:
            return True

        current = self.current_cell()

        target = self.path[0]

        # -----------------------------------------------
        # Comprobamos que el objetivo sea vecino
        # -----------------------------------------------

        dx = target[0] - current[0]
        dy = target[1] - current[1]

        if dx == 1:
            direction = "right"

        elif dx == -1:
            direction = "left"

        elif dy == 1:
            direction = "down"

        elif dy == -1:
            direction = "up"

        else:

            print(
                "ERROR: camino incorrecto:",
                current,
                "->",
                target
            )

            self.path = []

            return False

        # -----------------------------------------------
        # Orientamos el robot
        # -----------------------------------------------

        if self.direction_from_orientation() != direction:

            self.turn_to(direction)

            return False

        # -----------------------------------------------
        # Comprobamos que no haya aparecido una pared
        # -----------------------------------------------

        self.check_proximity()

        if self.sensor["proximity"]["front"]:

            print(
                "Obstáculo inesperado delante en",
                current
            )

            # El objetivo ya no es válido
            self.set_wall(target)

            self.path = []

            self.behaviour = "explore"

            return False

        # -----------------------------------------------
        # Avanzamos
        # -----------------------------------------------

        self.start()

        return False

    # ============================================================
    # MATRIZ
    # ============================================================

    def build_matrix(self):

        if not self.map:
            return []

        xs = [cell[0] for cell in self.map]
        ys = [cell[1] for cell in self.map]

        min_x = min(xs)
        max_x = max(xs)

        min_y = min(ys)
        max_y = max(ys)

        width = max_x - min_x + 1
        height = max_y - min_y + 1

        matrix = []

        for y in range(height):

            row = []

            for x in range(width):

                real_x = min_x + x
                real_y = min_y + y

                value = self.map.get(
                    (real_x, real_y),
                    UNKNOWN
                )

                # Para la matriz final:
                # UNKNOWN -> 0
                if value is None:
                    value = 0

                row.append(value)

            matrix.append(row)

        return matrix

    # ============================================================
    # IMPRIMIR MAPA
    # ============================================================

    def print_map(self):

        if not self.map:
            return

        xs = [cell[0] for cell in self.map]
        ys = [cell[1] for cell in self.map]

        min_x = min(xs)
        max_x = max(xs)

        min_y = min(ys)
        max_y = max(ys)

        print("")
        print("========== MAPA ==========")

        for y in range(min_y, max_y + 1):

            row = ""

            for x in range(min_x, max_x + 1):

                cell = (x, y)

                if cell == self.current_cell():

                    row += "R"

                elif self.map.get(cell) == WALL:

                    row += "#"

                elif self.map.get(cell) == FREE:

                    if cell in self.explored:
                        row += "."

                    else:
                        row += "+"

                else:

                    row += "?"

            print(row)

        print("==========================")
        print("")

    # ============================================================
    # UPDATE
    # ============================================================

    def update(self):

        # --------------------------------------------------------
        # MAPEO TERMINADO
        # --------------------------------------------------------

        if self.behaviour == "finished":

            self.stop()

            if not self.finished_printed:

                self.finished_printed = True

                print("")
                print("==============================")
                print("       MAPEO TERMINADO")
                print("==============================")

                self.print_map()

                self.final_matrix = self.build_matrix()

                print("MATRIZ FINAL:")

                for row in self.final_matrix:

                    print(
                        " ".join(
                            str(value)
                            for value in row
                        )
                    )

                print("==============================")

            # Dibujar robot
            super().update()

            return

        # --------------------------------------------------------
        # EXPLORAR
        # --------------------------------------------------------

        if self.behaviour == "explore":

            self.stop()

            current = self.current_cell()

            # Solo exploramos una celda una vez
            if current not in self.explored:

                self.explore_current_cell()

            # ----------------------------------------------------
            # Buscar siguiente frontier
            # ----------------------------------------------------

            result = self.choose_frontier()

            if result is None:

                # No queda ninguna casilla accesible pendiente
                # de explorar.
                self.behaviour = "finished"

                self.stop()

                return

            self.target, self.path = result

            print(
                "Nuevo objetivo:",
                self.target
            )

            print(
                "Camino:",
                self.path
            )

            self.behaviour = "navigate"

        # --------------------------------------------------------
        # NAVEGAR
        # --------------------------------------------------------

        if self.behaviour == "navigate":

            current = self.current_cell()

            # Hemos llegado
            if current == self.target:

                self.stop()

                self.behaviour = "explore"

                self.path = []

                return

            # ----------------------------------------------------
            # Si hemos llegado a la siguiente celda del camino
            # ----------------------------------------------------

            if self.path:

                if current == self.path[0]:

                    self.path.pop(0)

            # Si ya no queda camino
            if not self.path:

                self.stop()

                self.behaviour = "explore"

                return

            # ----------------------------------------------------
            # Continuamos el movimiento
            # ----------------------------------------------------

            self.move_one_step()

        # --------------------------------------------------------
        # UPDATE DEL ROBOT ORIGINAL
        # --------------------------------------------------------

        super().update()

        # --------------------------------------------------------
        # Detectamos cambio de celda
        # --------------------------------------------------------

        current = self.current_cell()

        if current != self.previous_cell:

            self.previous_cell = current

