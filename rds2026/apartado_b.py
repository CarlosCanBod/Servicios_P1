#!/usr/bin/python
# encoding: utf-8
"""Apartado B: A* point-to-point navigation with safe path smoothing."""

from __future__ import annotations

import argparse
import math
import os
from pathlib import Path

import pygame
import rds2026environment
import rds2026machines
import rds2026simulation
from robotica_servicios import MotionController, OccupancyGrid, astar, execute_path, smooth_path


def parse_point(raw: str) -> tuple[float, float]:
    try:
        x, y = raw.split(",", maxsplit=1)
        return float(x), float(y)
    except ValueError as exc:
        raise argparse.ArgumentTypeError("Use X,Y") from exc


def navigate(map_path: str, config: str | None, start: tuple[float, float],
             goal: tuple[float, float], fps: int = 60, headless: bool = False,
             smoothing: bool = True, frame_callback=None) -> dict:
    if headless:
        os.environ.setdefault("SDL_VIDEODRIVER", "dummy")
    grid = OccupancyGrid.load(map_path)
    config = config or grid.config_name
    if Path(config).name != grid.config_name:
        raise ValueError("Selected environment and occupancy map do not match")
    for label, point in (("start", start), ("goal", goal)):
        if not all(math.isfinite(value) for value in point):
            raise ValueError(f"{label} must contain finite coordinates")
        if not (grid.origin[0] <= point[0] < grid.origin[0] + grid.width
                and grid.origin[1] <= point[1] < grid.origin[1] + grid.height):
            raise ValueError(f"{label} {point} lies outside the map")
    start_cell = grid.nearest_free(start)
    reachable = grid.connected_free(start_cell)
    goal_cell = min(reachable, key=lambda point: math.dist(point, goal))
    discrete = astar(grid, start_cell, goal_cell)
    waypoints = smooth_path(grid, discrete) if smoothing else discrete
    floor = rds2026environment.floorplan(config)
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
    metrics = navigate(args.map, args.config, args.start, args.goal,
                       args.fps, args.headless, not args.no_smoothing)
    for key, value in metrics.items():
        print(f"{key}: {value}")


if __name__ == "__main__":
    main()
