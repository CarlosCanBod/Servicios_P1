#!/usr/bin/python
# encoding: utf-8

import math
from collections import deque

from vacuum import vacuum


# Estados del mapa
WALL = 0
FREE = 1


class vacuum_mapper(vacuum):

    def __init__(self, position, orientation, simulate_battery=False):

        # Inicializamos el robot original
        super().__init__(position, orientation, simulate_battery)

        # ---------------------------------------------------------
        # MAPA
        #
        # No sabemos inicialmente las dimensiones.
        #
        # mapa[(x,y)] = 0 -> pared
        # mapa[(x,y)] = 1 -> libre
        #
        # Si una coordenada no está en el diccionario:
        # todavía no sabemos qué hay.
        # ---------------------------------------------------------
        self.map = {}

        # Casillas libres conocidas que todavía no hemos explorado
        self.frontier = []

        # Casillas que ya hemos explorado
        self.explored = set()

        # Camino que el robot está siguiendo actualmente
        self.path = []

        # Casilla objetivo actual
        self.target = None

        # Estado del comportamiento
        #
        # "explore"     -> explorar casilla actual
        # "go_frontier" -> desplazarse hacia una casilla pendiente
        # "finished"    -> exploración terminada
        self.behaviour = "explore"

        # Para saber si acabamos de cambiar de casilla
        self.last_cell = None

        # Para evitar añadir continuamente la misma casilla
        self.frontier_set = set()

        # Dirección hacia la que queremos movernos
        self.target_direction = None

        # Matriz final
        self.final_matrix = None

    # =============================================================
    # UTILIDADES DE COORDENADAS
    # =============================================================

    def current_cell(self):
        """
        Convierte la posición continua del robot en una celda.

        El robot puede tener posiciones:
            (3.0, 2.0)
            (3.5, 2.0)
            (4.0, 2.0)

        pero nosotros queremos trabajar con:
            (3,2)
            (4,2)
        """

        x = int(math.floor(self.position[0] + 0.5))
        y = int(math.floor(self.position[1] + 0.5))

        return (x, y)

    def neighbours(self, cell):
        """
        Devuelve las cuatro celdas vecinas.
        """

        x, y = cell

        return {
            'up':    (x, y - 1),
            'right': (x + 1, y),
            'down':  (x, y + 1),
            'left':  (x - 1, y)
        }

    # =============================================================
    # ORIENTACIÓN
    # =============================================================

    def direction_from_orientation(self):
        """
        Convierte la orientación del robot en una dirección cardinal.

        En este programa:

            0   grados -> derecha
            90  grados -> arriba
            180 grados -> izquierda
            270 grados -> abajo
        """

        orientation = self.orientation % 360

        if orientation >= 315 or orientation < 45:
            return 'right'

        elif orientation >= 45 and orientation < 135:
            return 'up'

        elif orientation >= 135 and orientation < 225:
            return 'left'

        else:
            return 'down'

    def direction_from_delta(self, current, target):
        """
        Devuelve la dirección cardinal necesaria para ir
        desde current hasta target.

        Solo funciona si target es una celda vecina.
        """

        dx = target[0] - current[0]
        dy = target[1] - current[1]

        if dx == 1:
            return 'right'

        if dx == -1:
            return 'left'

        if dy == 1:
            return 'down'

        if dy == -1:
            return 'up'

        return None

    def orientation_for_direction(self, direction):
        """
        Orientación necesaria para mirar en una dirección.
        """

        if direction == 'right':
            return 0

        if direction == 'up':
            return 90

        if direction == 'left':
            return 180

        if direction == 'down':
            return 270

        return 0

    # =============================================================
    # MAPEO
    # =============================================================

    def add_frontier(self, cell):
        """
        Añade una celda a frontier si:

        - es libre
        - todavía no ha sido explorada
        - no está ya en frontier
        """

        if cell in self.explored:
            return

        if self.map.get(cell) != FREE:
            return

        if cell in self.frontier_set:
            return

        self.frontier.append(cell)
        self.frontier_set.add(cell)

    def mark_cell_free(self, cell):
        """
        Marca una celda como libre.
        """

        self.map[cell] = FREE

        self.add_frontier(cell)

    def mark_cell_wall(self, cell):
        """
        Marca una celda como pared.
        """

        self.map[cell] = WALL

        # Si por algún motivo estaba en frontier,
        # la eliminaremos posteriormente.
        if cell in self.frontier_set:
            self.frontier_set.remove(cell)

    # =============================================================
    # CONVERSIÓN SENSOR -> MAPA
    # =============================================================

    def sensor_to_map(self):
        """
        Utiliza los sensores del robot para descubrir
        los cuatro vecinos de la celda actual.

        El sensor proporciona:

            front
            left
            right

        La cuarta dirección (back) se considera libre porque
        acabamos de llegar desde allí, o porque ya conocemos
        esa casilla.
        """

        current = self.current_cell()

        # La casilla donde estamos es necesariamente libre
        self.map[current] = FREE

        neighbours = self.neighbours(current)

        direction = self.direction_from_orientation()

        # ---------------------------------------------------------
        # Convertimos front / left / right según orientación
        # ---------------------------------------------------------

        directions = ['up', 'right', 'down', 'left']

        index = directions.index(direction)

        front_direction = direction

        right_direction = directions[(index + 1) % 4]
        left_direction = directions[(index - 1) % 4]
        back_direction = directions[(index + 2) % 4]

        # ---------------------------------------------------------
        # FRONT
        # ---------------------------------------------------------

        front_cell = neighbours[front_direction]

        if self.sensor['proximity']['front']:
            self.mark_cell_wall(front_cell)
        else:
            self.mark_cell_free(front_cell)

        # ---------------------------------------------------------
        # RIGHT
        # ---------------------------------------------------------

        right_cell = neighbours[right_direction]

        if self.sensor['proximity']['right']:
            self.mark_cell_wall(right_cell)
        else:
            self.mark_cell_free(right_cell)

        # ---------------------------------------------------------
        # LEFT
        # ---------------------------------------------------------

        left_cell = neighbours[left_direction]

        if self.sensor['proximity']['left']:
            self.mark_cell_wall(left_cell)
        else:
            self.mark_cell_free(left_cell)

        # ---------------------------------------------------------
        # BACK
        #
        # Sabemos que esta celda es libre si hemos llegado desde ella.
        # Si ya estaba en el mapa, conservamos la información.
        # ---------------------------------------------------------

        back_cell = neighbours[back_direction]

        if back_cell in self.map:
            return

        # No marcamos automáticamente como libre una celda desconocida
        # que esté detrás. Solo lo hacemos si estábamos desplazándonos.
        if self.last_cell == back_cell:
            self.mark_cell_free(back_cell)

    # =============================================================
    # BFS
    # =============================================================

    def find_path(self, start, goal):
        """
        Busca el camino más corto entre start y goal
        utilizando únicamente celdas conocidas como libres.

        Devuelve una lista de celdas:

            [(x1,y1), (x2,y2), ...]
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

            neighbours = self.neighbours(current)

            for next_cell in neighbours.values():

                # Solo podemos pasar por celdas conocidas como libres
                if self.map.get(next_cell) != FREE:
                    continue

                if next_cell in previous:
                    continue

                previous[next_cell] = current

                if next_cell == goal:

                    # Reconstruimos el camino
                    path = []

                    node = goal

                    while node != start:
                        path.append(node)
                        node = previous[node]

                    path.reverse()

                    return path

                queue.append(next_cell)

        # No existe camino
        return None

    # =============================================================
    # ELEGIR SIGUIENTE OBJETIVO
    # =============================================================

    def choose_frontier(self):
        """
        Elige una casilla pendiente de explorar.

        Primero eliminamos de frontier las casillas que
        ya no sean necesarias.
        """

        while self.frontier:

            candidate = self.frontier.pop(0)

            self.frontier_set.discard(candidate)

            # Ya la hemos explorado
            if candidate in self.explored:
                continue

            # Ya no es libre
            if self.map.get(candidate) != FREE:
                continue

            return candidate

        return None

    # =============================================================
    # ROTACIÓN
    # =============================================================

    def rotate_to_direction(self, direction):
        """
        Gira el robot hasta que mire en la dirección indicada.
        """

        desired = self.orientation_for_direction(direction)

        current = self.orientation % 360

        difference = desired - current

        # Normalizamos a [-180,180]
        while difference > 180:
            difference -= 360

        while difference < -180:
            difference += 360

        if abs(difference) < 1:
            self.orientation = desired
            self.sensor['orientation'] = desired
            return True

        # Para girar usamos un paso máximo de 45 grados.
        step = max(-45, min(45, difference))

        self.stop()

        self.rotate(step)

        return False

    # =============================================================
    # EXPLORAR CELDA
    # =============================================================

    def explore_current_cell(self):
        """
        Explora los vecinos de la posición actual.

        Para poder conocer los cuatro lados, vamos rotando
        el robot y consultando los sensores.
        """

        current = self.current_cell()

        self.map[current] = FREE

        self.explored.add(current)

        # Ya no necesitamos esta celda en frontier
        self.frontier_set.discard(current)

        # ---------------------------------------------------------
        # Importante:
        #
        # Vamos a comprobar las cuatro orientaciones.
        # ---------------------------------------------------------

        orientations = [
            0,    # derecha
            90,   # arriba
            180,  # izquierda
            270   # abajo
        ]

        for orientation in orientations:

            # Giramos hasta esa orientación
            difference = orientation - self.orientation

            while difference > 180:
                difference -= 360

            while difference < -180:
                difference += 360

            if abs(difference) > 1:
                self.stop()
                self.rotate(difference)

            # Actualizamos sensores
            self.check_proximity()

            # Según esta orientación, identificamos el vecino frontal
            direction = self.direction_from_orientation()

            neighbours = self.neighbours(current)

            neighbour = neighbours[direction]

            if self.sensor['proximity']['front']:
                self.mark_cell_wall(neighbour)
            else:
                self.mark_cell_free(neighbour)

        # Después de explorar, no queremos quedarnos parados
        # en una orientación arbitraria.
        self.stop()

    # =============================================================
    # MOVERSE HACIA UNA CELDA
    # =============================================================

    def move_to_next_cell(self):
        """
        Hace avanzar al robot hacia la siguiente celda del path.
        """

        if not self.path:
            return True

        current = self.current_cell()

        target = self.path[0]

        direction = self.direction_from_delta(current, target)

        if direction is None:
            self.path = []
            return False

        # ---------------------------------------------------------
        # Primero orientamos el robot.
        # ---------------------------------------------------------

        if self.direction_from_orientation() != direction:

            self.rotate_to_direction(direction)

            return False

        # ---------------------------------------------------------
        # Ya estamos mirando hacia la celda.
        # ---------------------------------------------------------

        self.start()

        return False

    # =============================================================
    # UPDATE PRINCIPAL
    # =============================================================

    def update(self):

        # ---------------------------------------------------------
        # Si hemos terminado
        # ---------------------------------------------------------

        if self.behaviour == "finished":

            self.stop()

            # Dibujamos el robot utilizando el update original
            super().update()

            return

        # ---------------------------------------------------------
        # Posición anterior
        # ---------------------------------------------------------

        previous_cell = self.current_cell()

        # ---------------------------------------------------------
        # Si estamos explorando
        # ---------------------------------------------------------

        if self.behaviour == "explore":

            self.stop()

            # Aseguramos que los sensores están actualizados
            self.check_proximity()

            # Exploramos la celda
            self.explore_current_cell()

            # -----------------------------------------------------
            # ¿Hay alguna celda pendiente?
            # -----------------------------------------------------

            target = self.choose_frontier()

            if target is None:

                # No quedan casillas por explorar
                self.behaviour = "finished"

                print("================================")
                print("MAPEO TERMINADO")
                print("================================")

                self.print_map()

                self.final_matrix = self.build_matrix()

                return

            # -----------------------------------------------------
            # Tenemos una nueva celda objetivo
            # -----------------------------------------------------

            self.target = target

            self.path = self.find_path(
                self.current_cell(),
                self.target
            )

            if self.path is None:

                # No podemos llegar a ella con el conocimiento
                # actual. La dejamos para más adelante.
                self.target = None

                return

            self.behaviour = "go_frontier"

        # ---------------------------------------------------------
        # IR HACIA UNA CASILLA DE FRONTIER
        # ---------------------------------------------------------

        elif self.behaviour == "go_frontier":

            current_cell = self.current_cell()

            # Si hemos llegado al objetivo
            if current_cell == self.target:

                self.stop()

                self.behaviour = "explore"

                self.path = []

                return

            # Si el robot se ha movido a otra celda,
            # eliminamos la primera posición del camino.
            if self.path and current_cell == self.path[0]:

                self.path.pop(0)

            # Si no quedan pasos, hemos llegado
            if not self.path:

                self.stop()

                self.behaviour = "explore"

                return

            # Intentamos avanzar hacia la siguiente celda
            self.move_to_next_cell()

        # ---------------------------------------------------------
        # Movimiento físico
        #
        # El update original se encarga de mover el robot,
        # comprobar colisiones y dibujarlo.
        # ---------------------------------------------------------

        if self.behaviour != "explore" or self.is_running:

            super().update()

        # ---------------------------------------------------------
        # Comprobamos si hemos cambiado de celda
        # ---------------------------------------------------------

        current_cell = self.current_cell()

        if current_cell != previous_cell:

            self.last_cell = previous_cell

    # =============================================================
    # MATRIZ FINAL
    # =============================================================

    def build_matrix(self):

        if not self.map:
            return []

        xs = [p[0] for p in self.map.keys()]
        ys = [p[1] for p in self.map.keys()]

        min_x = min(xs)
        max_x = max(xs)

        min_y = min(ys)
        max_y = max(ys)

        width = max_x - min_x + 1
        height = max_y - min_y + 1

        matrix = [
            [0 for x in range(width)]
            for y in range(height)
        ]

        for (x, y), value in self.map.items():

            matrix_x = x - min_x
            matrix_y = y - min_y

            matrix[matrix_y][matrix_x] = value

        print("================================")
        print("MATRIZ FINAL")
        print("================================")

        for row in matrix:
            print("".join(str(value) for value in row))

        print("================================")

        return matrix

    # =============================================================
    # MOSTRAR MAPA DURANTE LA EJECUCIÓN
    # =============================================================

    def print_map(self):

        if not self.map:
            return

        xs = [p[0] for p in self.map.keys()]
        ys = [p[1] for p in self.map.keys()]

        min_x = min(xs)
        max_x = max(xs)

        min_y = min(ys)
        max_y = max(ys)

        print("")

        for y in range(min_y, max_y + 1):

            row = ""

            for x in range(min_x, max_x + 1):

                if (x, y) == self.current_cell():
                    row += "R"

                elif self.map.get((x, y)) == WALL:
                    row += "#"

                elif self.map.get((x, y)) == FREE:
                    if (x, y) in self.explored:
                        row += "."
                    else:
                        row += "?"

                else:
                    row += " "

            print(row)

        print("")

