#!/usr/bin/python
# encoding: utf-8
"""Apartado C: guardar waypoints durante teleoperación y reproducir la ruta."""

from __future__ import annotations

import argparse
import math
import os
from pathlib import Path

import pygame
import rds2026environment
import rds2026machines
import rds2026simulation
from robotica_servicios import MotionController, OccupancyGrid, RecordedRoute, astar, execute_path, smooth_path


def parse_point(raw: str) -> tuple[int, int]:
    """Leer el inicio de grabación X,Y; esta interfaz pide coordenadas enteras."""
    try:
        x, y = raw.split(",", maxsplit=1)
        return int(x), int(y)
    except ValueError as exc:
        raise argparse.ArgumentTypeError("Use X,Y") from exc


class WaypointOverlay:
    """Dibujar la ruta sin modificar sus puntos ni el movimiento del robot.

    Azul: waypoint guardado. Rojo: objetivo actual del replay. La numeración
    empieza en 1 e incluye el inicio, que se guarda automáticamente.
    """

    def __init__(self, simulation, route: RecordedRoute, replay_mode: bool = False):
        """Añadir una capa de dibujo que consulta la misma ruta que se está grabando."""
        self.simulation = simulation
        self.route = route
        self.replay_mode = replay_mode
        self.active_index: int | None = None
        # Los índices de Python empiezan en 0; la etiqueta visible suma 1.
        # None significa que todavía no hay objetivo activo o que hemos terminado.
        self.target: tuple[float, float] | None = None
        self.completed = False
        density = simulation.screen["window"]["density"]
        # Crear la fuente después de simulation.start(), que inicializa pygame.
        self.font = pygame.font.Font(None, max(18, min(26, density // 2)))
        original_extra = simulation.environment.update_extra

        def draw_overlay() -> None:
            # Dibujar después del robot y del mobiliario mantiene visibles las X.
            # Se repintan cada frame porque environment.update() limpia la pantalla.
            original_extra()
            self.draw()

        simulation.environment.update_extra = draw_overlay

    def draw(self) -> None:
        """Pintar X, números y estado; no mover al robot ni añadir waypoints."""
        surface = self.simulation.screen["display"]
        density = self.simulation.screen["window"]["density"]
        radius = max(6, min(11, density // 3))
        blue, red = (25, 80, 230), (220, 40, 45)

        # Agrupar puntos coincidentes evita ocultar la numeración cuando una
        # ruta vuelve al inicio: una sola X puede llevar la etiqueta "1, 5".
        groups: dict[tuple[int, int], list[int]] = {}
        for index, (x, y) in enumerate(self.route.waypoints):
            pixel = (round(x * density), round(y * density))
            groups.setdefault(pixel, []).append(index)
        for (x, y), indices in groups.items():
            color = red if self.active_index in indices else blue
            for start, end in (((x - radius, y - radius), (x + radius, y + radius)),
                               ((x - radius, y + radius), (x + radius, y - radius))):
                # Borde blanco para que la X se distinga sobre cualquier objeto.
                pygame.draw.line(surface, (255, 255, 255), start, end, 6)
                pygame.draw.line(surface, color, start, end, 3)
            label = self.font.render(", ".join(str(index + 1) for index in indices), True, color)
            box = label.get_rect(topleft=(x + radius + 3, y - radius - label.get_height()))
            box.inflate_ip(6, 4)
            box.clamp_ip(surface.get_rect())
            pygame.draw.rect(surface, (255, 255, 255), box, border_radius=3)
            pygame.draw.rect(surface, color, box, width=1, border_radius=3)
            surface.blit(label, label.get_rect(center=box.center))

        status = f"Waypoints: {len(self.route.waypoints)} | W: marcar"
        adjustment = None
        if self.replay_mode:
            status = "Ruta completada" if self.completed else "Preparando ruta"
            if self.active_index is not None:
                status = f"Destino: waypoint {self.active_index + 1}/{len(self.route.waypoints)} (rojo)"
                requested = self.route.waypoints[self.active_index]
                if self.target is not None and math.dist(requested, self.target) > 1e-6:
                    # C puede ajustar una coordenada a una pose de su mapa.
                    # Mostrar también el objetivo ejecutado evita señalar otro sitio.
                    source_pixel = (round(requested[0] * density), round(requested[1] * density))
                    target_pixel = (round(self.target[0] * density), round(self.target[1] * density))
                    pygame.draw.line(surface, red, source_pixel, target_pixel, 2)
                    pygame.draw.circle(surface, red, target_pixel, radius + 3, 2)
                    adjustment = f"Objetivo ajustado: ({self.target[0]:g}, {self.target[1]:g})"
        labels = [self.font.render(text, True, (30, 35, 45))
                  for text in (status, adjustment) if text is not None]
        box = pygame.Rect(6, 6, max(label.get_width() for label in labels) + 12,
                          sum(label.get_height() for label in labels) + 8)
        pygame.draw.rect(surface, (255, 255, 255), box, border_radius=4)
        y = box.top + 4
        for label in labels:
            surface.blit(label, (box.left + 6, y))
            y += label.get_height()


def replay(route_path: str, map_path: str, fps: int = 60,
           headless: bool = False, frame_callback=None) -> dict:
    """Reproducir puntos guardados usando el mapa de A y el A* compartido.

    A diferencia de B, este modo aproxima cada punto a una pose de la zona
    conectada al robot. max_snap_distance cuantifica el mayor cambio de destino;
    final_error compara la llegada con el objetivo ejecutado, no con el original.
    """
    if headless:
        os.environ.setdefault("SDL_VIDEODRIVER", "dummy")
    route, grid = RecordedRoute.load(route_path), OccupancyGrid.load(map_path)
    # Una ruta contiene puntos y su escenario; la geometría navegable procede
    # del mapa de A. Comprobamos que ambos archivos pertenecen al mismo mundo.
    if route.config != grid.config_name:
        raise ValueError("Route and map belong to different configurations")
    if Path(grid.config_name).name != grid.config_name or not Path(grid.config_name).is_file():
        raise ValueError("Map references an unavailable local configuration")
    for point in route.waypoints:
        if not (grid.origin[0] <= point[0] < grid.origin[0] + grid.width
                and grid.origin[1] <= point[1] < grid.origin[1] + grid.height):
            raise ValueError(f"Waypoint {point} lies outside the map")
    # La reproducción inicia el robot en la pose conocida más cercana al
    # primer waypoint. Las coordenadas originales permanecen en el archivo.
    first = grid.nearest_free(route.waypoints[0])
    floor = rds2026environment.floorplan(grid.config_name)
    robot = rds2026machines.vacuum(position=first, orientation=0)
    simulation = rds2026simulation.simulation(
        size=(700, 700), fps=fps, environment=floor, machine=robot
    )
    simulation.start()
    robot.stop()
    overlay = WaypointOverlay(simulation, route, replay_mode=True)
    controller = MotionController(simulation, robot, render=not headless,
                                  frame_callback=frame_callback)
    planned_segments = 0
    executed_targets = [first]
    snap_distances = [math.dist(route.waypoints[0], first)]
    try:
        # Primer dibujo sin avanzar: también muestra rutas con un solo waypoint.
        simulation.update()
        for index, requested_target in enumerate(route.waypoints[1:], start=1):
            # Se planifica cada pareja consecutiva usando la posición actual.
            # Los waypoints guardados pueden no coincidir con la rejilla de A:
            # se proyectan a poses libres conectadas y se mide ese ajuste.
            source = grid.nearest_free(robot.position)
            component = grid.connected_free(source)
            target = min(component, key=lambda point: math.dist(point, requested_target))
            snap_distances.append(math.dist(requested_target, target))
            # Reutilizamos el A* común (no resolve_endpoint de B): si hay un
            # mueble entre dos waypoints, A* lo rodea
            # antes de ejecutar los tramos rectos que unen los cambios de rumbo.
            path = smooth_path(grid, astar(grid, source, target))
            planned_segments += len(path) - 1
            # El índice se conserva respecto al archivo, no a los puntos de A*.
            # Así el objetivo rojo siempre tiene el mismo número que al grabar.
            overlay.active_index, overlay.target = index, target
            execute_path(controller, path)
            executed_targets.append(target)
        overlay.active_index, overlay.target = None, None
        overlay.completed = True
        simulation.update()
        return {
            "route": route.name, "waypoints": len(route.waypoints),
            "segments_replayed": max(0, len(route.waypoints) - 1),
            "planned_segments": planned_segments,
            "max_snap_distance": round(max(snap_distances), 6),
            "final_error": round(math.dist(robot.position, executed_targets[-1]), 6),
            "collisions": robot.stats_collisions, "frames": controller.frames,
        }
    finally:
        simulation.stop()


def teleoperate(config: str, start: tuple[int, int], route_path: str,
                fps: int = 30) -> None:
    """Conducir con teclado y guardar solo inicio, puntos marcados y punto final."""
    floor = rds2026environment.floorplan(config)
    robot = rds2026machines.vacuum(position=start, orientation=0)
    simulation = rds2026simulation.simulation(
        size=(700, 700), fps=fps, environment=floor, machine=robot
    )
    route = RecordedRoute(Path(route_path).stem, Path(config).name)
    # Guardamos el inicio automáticamente. Durante la conducción, W añade un
    # waypoint: esta modalidad no registra todas las poses de cada fotograma.
    route.add(robot.position)
    simulation.start()
    robot.stop()
    WaypointOverlay(simulation, route)
    print("[C] UP move | LEFT/RIGHT rotate 90 degrees | W waypoint | S save | Q save+quit")
    while simulation.is_running:
        # KEYDOWN inicia el avance/giro; KEYUP detiene al soltar arriba.
        # El simulador impide atravesar objetos, pero sí cuenta como colisión
        # un intento de avanzar contra ellos. Teleoperar no garantiza cero choques.
        for event in simulation.read_keyboard():
            if event.type == pygame.QUIT:
                simulation.is_running = False
            elif event.type == pygame.KEYDOWN:
                # Cada pulsación gira un cuarto de vuelta; partiendo de 0°,
                # conservamos los rumbos cardinales 0°, 90°, 180° y 270°.
                if event.key == pygame.K_LEFT: robot.rotate(90)
                elif event.key == pygame.K_RIGHT: robot.rotate(-90)
                elif event.key == pygame.K_UP: robot.start()
                elif event.key == pygame.K_w:
                    # El overlay consulta la misma lista; la nueva X aparecerá
                    # en el dibujo de este ciclo, sin cambiar el formato del JSON.
                    route.add(robot.position)
                    print(f"Waypoint {len(route.waypoints)}: {route.waypoints[-1]}")
                elif event.key == pygame.K_s:
                    route.save(route_path)
                    print(f"Saved {route_path}")
                elif event.key == pygame.K_d:
                    simulation.screen["debugging"] = not simulation.screen["debugging"]
                elif event.key == pygame.K_q: simulation.is_running = False
            elif event.type == pygame.KEYUP and event.key == pygame.K_UP:
                robot.stop()
        if not simulation.is_running:
            break
        simulation.update()
    robot.stop()
    # Al salir guardamos también el punto final y persistimos la ruta en JSON.
    route.add(robot.position)
    route.save(route_path)
    simulation.stop()


def build_parser() -> argparse.ArgumentParser:
    """Separar las opciones del modo record (grabar) y replay (reproducir)."""
    parser = argparse.ArgumentParser(description=__doc__)
    sub = parser.add_subparsers(dest="mode", required=True)
    record = sub.add_parser("record")
    record.add_argument("--config", default="cfg_0.py")
    record.add_argument("--start", type=parse_point, default=(21, 21))
    record.add_argument("--route", default="ruta_waypoints.json")
    record.add_argument("--fps", type=int, default=30)
    play = sub.add_parser("replay")
    play.add_argument("--route", default="ruta_waypoints.json")
    play.add_argument("--map", default="mapa_grid.json")
    play.add_argument("--fps", type=int, default=60)
    play.add_argument("--headless", action="store_true")
    return parser


def main() -> None:
    """Elegir el modo solicitado; record guarda una ruta y replay muestra medidas."""
    os.chdir(Path(__file__).resolve().parent)
    args = build_parser().parse_args()
    if args.mode == "record":
        teleoperate(args.config, args.start, args.route, args.fps)
    else:
        metrics = replay(args.route, args.map, args.fps, args.headless)
        for key, value in metrics.items(): print(f"{key}: {value}")


if __name__ == "__main__":
    main()
