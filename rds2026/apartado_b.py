#!/usr/bin/python
# encoding: utf-8
"""Apartado B: planificar con A* en el mapa de A y ejecutar tramos rectos."""

from __future__ import annotations

import argparse
import math
import os
from pathlib import Path

import pygame
import rds2026environment
import rds2026machines
import rds2026simulation
from robotica_servicios import Cell, MotionController, OccupancyGrid, astar, execute_path, smooth_path


def parse_point(raw: str) -> tuple[float, float]:
    try:
        x, y = raw.split(",", maxsplit=1)
        return float(x), float(y)
    except ValueError as exc:
        raise argparse.ArgumentTypeError("Use X,Y") from exc


def resolve_endpoint(grid: OccupancyGrid, point: tuple[float, float],
                     label: str) -> tuple[float, float]:
    """Validar un extremo sin trasladarlo a otra zona para conseguir una ruta.

    Una pose de la rejilla debe ser libre conocida. Para un punto entre muestras
    solo permitimos discretizar al vértice más cercano de su intervalo local
    si todos los vértices son libres. Este ajuste limitado no prueba llegada
    continua exacta al punto arbitrario; su distancia se informa en las métricas.
    """
    if not all(math.isfinite(value) for value in point):
        raise ValueError(f"{label}: las coordenadas deben ser finitas.")
    if not (grid.origin[0] <= point[0] < grid.origin[0] + grid.width
            and grid.origin[1] <= point[1] < grid.origin[1] + grid.height):
        raise ValueError(f"{label} {point}: fuera del mapa observado.")

    resolution = grid.active_resolution
    free = grid.planning_keys()
    axes = []
    for value in point:
        scaled = value / resolution
        nearest = round(scaled)
        # La tolerancia absorbe únicamente residuos numéricos. No convierte
        # una pose ocupada en otra vecina libre por cercanía a un obstáculo.
        if abs(scaled - nearest) * resolution <= 1e-7:
            axes.append((nearest,))
        else:
            axes.append((math.floor(scaled), math.ceil(scaled)))
    candidates = {(x, y) for x in axes[0] for y in axes[1]}

    if not candidates <= free:
        if len(candidates) == 1:
            key = next(iter(candidates))
            world = grid.key_to_world(key, resolution)
            blocked = key in grid.fine_obstacles or (
                all(abs(value - round(value)) <= 1e-7 for value in world)
                and grid.get((round(world[0]), round(world[1]))) == Cell.OBSTACLE
            )
            reason = "pose bloqueada por un obstáculo" if blocked else "zona no explorada"
        else:
            reason = "rodeado de poses bloqueadas o no exploradas; no se permite ajustar el punto"
        raise ValueError(f"{label} {point}: no accesible según el mapa ({reason}).")

    # El ajuste depende solo de la resolución local, nunca de si A* encuentra
    # ruta desde el origen. El desempate por clave hace el resultado reproducible.
    key = min(candidates, key=lambda item: (
        math.dist(grid.key_to_world(item, resolution), point), item,
    ))
    return grid.key_to_world(key, resolution)


def navigate(map_path: str, config: str | None, start: tuple[float, float],
             goal: tuple[float, float], fps: int = 60, headless: bool = False,
             smoothing: bool = True, frame_callback=None) -> dict:
    if headless:
        os.environ.setdefault("SDL_VIDEODRIVER", "dummy")
    grid = OccupancyGrid.load(map_path)
    # El mapa es la información previamente descubierta por A. Su origen y
    # dimensiones describen el rectángulo observado, no el plano del simulador.
    config = config or grid.config_name
    if Path(config).name != grid.config_name:
        raise ValueError("Selected environment and occupancy map do not match")
    # Validar ambos extremos antes de crear el robot. Un obstáculo/desconocido
    # no se sustituye por una pose libre, y un destino desconectado no se mueve
    # a la componente del origen. A* debe decidir si existe una ruta entre ambos.
    start_cell = resolve_endpoint(grid, start, "Origen")
    goal_cell = resolve_endpoint(grid, goal, "Destino")
    try:
        discrete = astar(grid, start_cell, goal_cell)
    except ValueError as exc:
        raise ValueError(
            f"Destino {goal}: no accesible desde {start}. "
            "A* no encuentra una ruta entre las poses libres: zonas desconectadas."
        ) from exc
    # La compresión elimina puntos intermedios de una misma recta; mantiene
    # los giros y no introduce atajos diagonales por zonas sin observar.
    waypoints = smooth_path(grid, discrete) if smoothing else discrete
    floor = rds2026environment.floorplan(config)
    # El simulador comienza en la pose inicial validada; no ejecutamos un
    # trayecto desde el punto arbitrario hasta su muestra local de la rejilla.
    robot = rds2026machines.vacuum(position=start_cell, orientation=0)
    simulation = rds2026simulation.simulation(
        size=(700, 700), fps=fps, environment=floor, machine=robot
    )
    original_extra = floor.update_extra

    def draw_overlay() -> None:
        original_extra()
        density = simulation.screen["window"]["density"]
        grid.draw(simulation.screen["display"], density)
        if len(waypoints) > 1:
            points = [(round(x * density), round(y * density)) for x, y in waypoints]
            pygame.draw.lines(simulation.screen["display"], (30, 80, 240), False,
                              points, max(2, density // 8))

    floor.update_extra = draw_overlay
    simulation.start()
    controller = MotionController(simulation, robot, render=not headless,
                                  frame_callback=frame_callback)
    try:
        # El planificador decide el camino; el controlador ejecuta cada tramo
        # consultando posición y contacto antes de cada avance físico.
        execute_path(controller, waypoints)
        return {
            "requested_start": start, "requested_goal": goal,
            "start": start_cell, "goal": goal_cell,
            "start_snap_distance": round(math.dist(start, start_cell), 6),
            "goal_snap_distance": round(math.dist(goal, goal_cell), 6),
            "astar_cells": len(discrete), "waypoints": len(waypoints),
            "path_length": round(sum(math.dist(a, b) for a, b in zip(waypoints, waypoints[1:])), 3),
            "final_error": round(math.dist(robot.position, goal_cell), 6),
            "collisions": robot.stats_collisions, "frames": controller.frames,
        }
    finally:
        simulation.stop()


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--map", default="mapa_grid.json")
    parser.add_argument("--config")
    parser.add_argument("--start", required=True, type=parse_point)
    parser.add_argument("--goal", required=True, type=parse_point)
    parser.add_argument("--fps", type=int, default=60)
    parser.add_argument("--headless", action="store_true")
    parser.add_argument("--no-smoothing", action="store_true")
    return parser


def main() -> None:
    os.chdir(Path(__file__).resolve().parent)
    args = build_parser().parse_args()
    try:
        metrics = navigate(args.map, args.config, args.start, args.goal,
                           args.fps, args.headless, not args.no_smoothing)
    except ValueError as exc:
        # Error legible y código de salida no nulo, sin iniciar un movimiento
        # hacia un destino alternativo ni imprimir una traza para este caso.
        raise SystemExit(f"[B] {exc}") from None
    for key, value in metrics.items():
        print(f"{key}: {value}")


if __name__ == "__main__":
    main()
