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
    try:
        x, y = raw.split(",", maxsplit=1)
        return int(x), int(y)
    except ValueError as exc:
        raise argparse.ArgumentTypeError("Use X,Y") from exc


def replay(route_path: str, map_path: str, fps: int = 60,
           headless: bool = False, frame_callback=None) -> dict:
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
    controller = MotionController(simulation, robot, render=not headless,
                                  frame_callback=frame_callback)
    planned_segments = 0
    executed_targets = [first]
    snap_distances = [math.dist(route.waypoints[0], first)]
    try:
        for requested_target in route.waypoints[1:]:
            # Se planifica cada pareja consecutiva usando la posición actual.
            # Los waypoints guardados pueden no coincidir con la rejilla de A:
            # se proyectan a poses libres conectadas y se mide ese ajuste.
            source = grid.nearest_free(robot.position)
            component = grid.connected_free(source)
            target = min(component, key=lambda point: math.dist(point, requested_target))
            snap_distances.append(math.dist(requested_target, target))
            # Reutilizamos B: si hay un mueble entre dos waypoints, A* lo rodea
            # antes de ejecutar los tramos rectos que unen los cambios de rumbo.
            path = smooth_path(grid, astar(grid, source, target))
            planned_segments += len(path) - 1
            execute_path(controller, path)
            executed_targets.append(target)
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
    print("[C] UP move | LEFT/RIGHT rotate | W waypoint | S save | Q save+quit")
    while simulation.is_running:
        # KEYDOWN inicia el avance/giro; KEYUP detiene al soltar arriba.
        # El propio simulador bloquea movimientos que producirían contacto.
        for event in simulation.read_keyboard():
            if event.type == pygame.QUIT:
                simulation.is_running = False
            elif event.type == pygame.KEYDOWN:
                if event.key == pygame.K_LEFT: robot.rotate(15)
                elif event.key == pygame.K_RIGHT: robot.rotate(-15)
                elif event.key == pygame.K_UP: robot.start()
                elif event.key == pygame.K_w:
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
    os.chdir(Path(__file__).resolve().parent)
    args = build_parser().parse_args()
    if args.mode == "record":
        teleoperate(args.config, args.start, args.route, args.fps)
    else:
        metrics = replay(args.route, args.map, args.fps, args.headless)
        for key, value in metrics.items(): print(f"{key}: {value}")


if __name__ == "__main__":
    main()
