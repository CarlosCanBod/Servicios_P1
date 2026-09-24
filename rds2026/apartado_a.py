#!/usr/bin/python
# encoding: utf-8
"""Apartado A: mapping plus terminating complete grid coverage."""

from __future__ import annotations

import argparse
import os
from pathlib import Path

import rds2026environment
import rds2026machines
import rds2026simulation
from robotica_servicios import (
    CompleteCoverageExplorer, MotionController, SparseExplorationMap,
    reachable_truth, surface_cells_for_keys,
)


DEFAULT_STARTS = {
    "cfg_0.py": (21, 21), "cfg_1.py": (21, 21),
    "cfg_2.py": (21, 21), "cfg_3.py": (7, 7),
}


def parse_point(raw: str) -> tuple[float, float]:
    try:
        x, y = raw.split(",", maxsplit=1)
        return float(x), float(y)
    except ValueError as exc:
        raise argparse.ArgumentTypeError("Use X,Y, for example 21,21") from exc


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--config", default="cfg_0.py")
    parser.add_argument("--start", type=parse_point)
    parser.add_argument("--fps", type=int, default=60, help="0 disables real-time throttling")
    parser.add_argument("--headless", action="store_true")
    parser.add_argument("--output", default="mapa_grid.json")
    parser.add_argument("--legacy-output", default="mapa_grid.txt")
    parser.add_argument("--max-probes", type=int)
    return parser


def run_coverage(config: str, start: tuple[float, float], fps: int,
                 headless: bool, output: str, legacy_output: str,
                 max_probes: int | None = None, frame_callback=None) -> dict:
    if headless:
        os.environ.setdefault("SDL_VIDEODRIVER", "dummy")
    floor = rds2026environment.floorplan(config)
    robot = rds2026machines.vacuum(position=start, orientation=0)
    simulation = rds2026simulation.simulation(
        size=(700, 700), fps=fps, environment=floor, machine=robot
    )
    observations = SparseExplorationMap(Path(config).name, start)
    original_extra = floor.update_extra

    def draw_overlay() -> None:
        original_extra()
        observations.draw(simulation.screen["display"], simulation.screen["window"]["density"])

    floor.update_extra = draw_overlay
    simulation.start()
    controller = MotionController(simulation, robot, render=not headless,
                                  frame_callback=frame_callback)
    try:
        result = CompleteCoverageExplorer(observations, controller).run(max_probes=max_probes)
        grid = observations.finalize()
        # Ground truth is read only now, for post-hoc validation. Neither the
        # explorer nor the matrix constructor sees the simulator's dimensions.
        truth = reachable_truth(floor, simulation.screen["window"]["density"], start)
        truth_surface = surface_cells_for_keys(truth, floor.size[0], floor.size[1])
        covered_surface = grid.covered_points()
        metrics = {
            "reachable_poses": len(truth),
            "visited_poses": len(result.visited),
            "pose_coverage_percent": round(100 * len(result.visited & truth) / len(truth), 3),
            "missed_poses": len(truth - result.visited),
            "unexpected_poses": len(result.visited - truth),
            "reachable_cells": len(truth_surface),
            "visited_cells": len(covered_surface & truth_surface),
            "coverage_percent": round(100 * len(covered_surface & truth_surface) / len(truth_surface), 3),
            "missed_cells": len(truth_surface - covered_surface),
            "unexpected_cells": len(covered_surface - truth_surface),
            "contact_obstacles": len(result.obstacles),
            "probes": result.probes,
            "trajectory_steps": len(result.trajectory) - 1,
            "simulation_frames": result.frames,
            "collisions": robot.stats_collisions,
        }
        grid.metadata.update(metrics)
        grid.save(output)
        grid.save_legacy(legacy_output)
        return metrics
    finally:
        simulation.stop()


def main() -> None:
    os.chdir(Path(__file__).resolve().parent)
    args = build_parser().parse_args()
    start = args.start or DEFAULT_STARTS.get(Path(args.config).name)
    if start is None:
        raise SystemExit("Unknown configuration: provide --start X,Y")
    print(f"[A] Exploring {Path(args.config).name} from {start}...")
    metrics = run_coverage(args.config, start, args.fps, args.headless,
                           args.output, args.legacy_output, args.max_probes)
    for key, value in metrics.items():
        print(f"{key}: {value}")


if __name__ == "__main__":
    main()
