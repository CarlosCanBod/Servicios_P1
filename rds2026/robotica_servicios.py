#!/usr/bin/python
# encoding: utf-8
"""Reusable algorithms for all three parts of practice P1.

The map stored here is a *configuration-space* grid: a FREE cell means that
the centre of the 2x2 vacuum can occupy that coordinate.  This is safer for
planning than a decorative floor bitmap because the robot footprint is already
accounted for.  UNKNOWN is never silently converted into OBSTACLE.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import IntEnum
from heapq import heappop, heappush
import json
import math
from pathlib import Path
from time import time
from typing import Iterable, Iterator

import pygame


class Cell(IntEnum):
    UNKNOWN = 0
    FREE = 1
    OBSTACLE = 2


Point = tuple[int, int]
FloatPoint = tuple[float, float]
FineKey = tuple[int, int]
CARDINALS: tuple[Point, ...] = ((1, 0), (0, 1), (-1, 0), (0, -1))
FINE_RESOLUTION = 0.5


@dataclass
class OccupancyGrid:
    width: int
    height: int
    cells: list[list[int]] = field(default_factory=list)
    config_name: str = "unknown"
    start: FloatPoint | None = None
    metadata: dict = field(default_factory=dict)
    coverage: list[list[int]] = field(default_factory=list)
    fine_free: set[FineKey] = field(default_factory=set)
    fine_obstacles: set[FineKey] = field(default_factory=set)
    planning_resolution: float = FINE_RESOLUTION
    origin: Point = (0, 0)

    def __post_init__(self) -> None:
        if not self.cells:
            self.cells = [
                [int(Cell.UNKNOWN) for _ in range(self.width)]
                for _ in range(self.height)
            ]
        if len(self.cells) != self.height or any(
            len(row) != self.width for row in self.cells
        ):
            raise ValueError("Grid dimensions do not match its cell matrix")
        if not self.coverage:
            self.coverage = [[0 for _ in range(self.width)] for _ in range(self.height)]
        if len(self.coverage) != self.height or any(
            len(row) != self.width for row in self.coverage
        ):
            raise ValueError("Coverage dimensions do not match the map")
        if self.planning_resolution <= 0:
            raise ValueError("Planning resolution must be positive")

    def in_bounds(self, point: Point, margin: int = 0) -> bool:
        x, y = point
        return (
            self.origin[0] + margin <= x < self.origin[0] + self.width - margin
            and self.origin[1] + margin <= y < self.origin[1] + self.height - margin
        )

    def get(self, point: Point) -> Cell:
        x, y = point
        if not self.in_bounds(point):
            return Cell.OBSTACLE
        return Cell(self.cells[y - self.origin[1]][x - self.origin[0]])

    def set(self, point: Point, value: Cell) -> None:
        if self.in_bounds(point):
            x, y = point
            self.cells[y - self.origin[1]][x - self.origin[0]] = int(value)

    def counts(self) -> dict[str, int]:
        return {
            "unknown": sum(row.count(int(Cell.UNKNOWN)) for row in self.cells),
            "free": sum(row.count(int(Cell.FREE)) for row in self.cells),
            "obstacle": sum(row.count(int(Cell.OBSTACLE)) for row in self.cells),
        }

    def nearest_free(self, point: FloatPoint) -> FloatPoint:
        points = list(self.free_points())
        if not points:
            raise ValueError("The map contains no traversable cells")
        return min(points, key=lambda p: math.dist(p, point))

    def configuration_in_bounds(self, point: FloatPoint) -> bool:
        """Whether the 2x2 robot footprint remains inside the floor extent."""
        x, y = point
        return (self.origin[0] + 1.0 <= x <= self.origin[0] + self.width - 1.0
                and self.origin[1] + 1.0 <= y <= self.origin[1] + self.height - 1.0)

    def world_to_key(self, point: FloatPoint, resolution: float | None = None) -> FineKey:
        resolution = resolution or self.active_resolution
        key = (round(point[0] / resolution), round(point[1] / resolution))
        decoded = self.key_to_world(key, resolution)
        if math.dist(decoded, point) > 1e-7:
            raise ValueError(f"Point {point} is not aligned to resolution {resolution}")
        return key

    @staticmethod
    def key_to_world(key: FineKey, resolution: float = FINE_RESOLUTION) -> FloatPoint:
        return (round(key[0] * resolution, 6), round(key[1] * resolution, 6))

    @property
    def active_resolution(self) -> float:
        return self.planning_resolution if self.fine_free else 1.0

    def planning_keys(self) -> set[FineKey]:
        if self.fine_free:
            return set(self.fine_free)
        return {
            (x + self.origin[0], y + self.origin[1])
            for y, row in enumerate(self.cells)
            for x, value in enumerate(row)
            if value == int(Cell.FREE)
        }

    def free_points(self) -> Iterator[FloatPoint]:
        resolution = self.active_resolution
        for key in sorted(self.planning_keys()):
            yield self.key_to_world(key, resolution)

    def is_free(self, point: FloatPoint) -> bool:
        try:
            key = self.world_to_key(point)
        except ValueError:
            return False
        return key in self.planning_keys()

    def connected_free(self, start: FloatPoint) -> set[FloatPoint]:
        resolution = self.active_resolution
        free = self.planning_keys()
        start_key = self.world_to_key(start, resolution)
        if start_key not in free:
            raise ValueError(f"Start {start} is not a known free configuration")
        reached = {start_key}
        pending = [start_key]
        while pending:
            current = pending.pop()
            for dx, dy in CARDINALS:
                neighbour = (current[0] + dx, current[1] + dy)
                if neighbour in free and neighbour not in reached:
                    reached.add(neighbour)
                    pending.append(neighbour)
        return {self.key_to_world(key, resolution) for key in reached}

    def add_free_pose(self, point: FloatPoint) -> None:
        key = self.world_to_key(point, self.planning_resolution)
        self.fine_free.add(key)
        self.fine_obstacles.discard(key)
        x, y = point
        if abs(x - round(x)) < 1e-7 and abs(y - round(y)) < 1e-7:
            self.set((round(x), round(y)), Cell.FREE)
        self.mark_covered(point)

    def add_obstacle_pose(self, point: FloatPoint) -> None:
        key = self.world_to_key(point, self.planning_resolution)
        if key in self.fine_free:
            return
        self.fine_obstacles.add(key)
        x, y = point
        if abs(x - round(x)) < 1e-7 and abs(y - round(y)) < 1e-7:
            self.set((round(x), round(y)), Cell.OBSTACLE)

    def mark_covered(self, point: FloatPoint) -> None:
        """Mark floor cells under the four footprint sampling points."""
        x, y = point
        for sample_y in (y - 0.5, y + 0.5):
            for sample_x in (x - 0.5, x + 0.5):
                cell = (math.floor(sample_x), math.floor(sample_y))
                if self.in_bounds(cell):
                    self.coverage[cell[1] - self.origin[1]][cell[0] - self.origin[0]] = 1

    def covered_points(self) -> set[Point]:
        return {
            (x + self.origin[0], y + self.origin[1])
            for y, row in enumerate(self.coverage)
            for x, value in enumerate(row)
            if value
        }

    def save(self, path: str | Path) -> Path:
        path = Path(path)
        path.parent.mkdir(parents=True, exist_ok=True)
        payload = {
            "format": "rds-p1-configuration-grid",
            "version": 3,
            "origin": list(self.origin),
            "width": self.width,
            "height": self.height,
            "states": {"unknown": 0, "free": 1, "obstacle": 2},
            "robot_footprint": [2, 2],
            "config": self.config_name,
            "start": list(self.start) if self.start else None,
            "metadata": self.metadata,
            "cells": self.cells,
            "coverage": self.coverage,
            "planning_resolution": self.planning_resolution,
            "configuration_free": [list(key) for key in sorted(self.fine_free)],
            "configuration_obstacles": [list(key) for key in sorted(self.fine_obstacles)],
        }
        temporary = path.with_suffix(path.suffix + ".tmp")
        temporary.write_text(
            json.dumps(payload, indent=2, sort_keys=True), encoding="utf-8"
        )
        temporary.replace(path)
        return path

    def save_legacy(self, path: str | Path) -> Path:
        path = Path(path)
        path.parent.mkdir(parents=True, exist_ok=True)
        temporary = path.with_suffix(path.suffix + ".tmp")
        temporary.write_text(
            "".join(
                "".join(
                    "1" if self.coverage[y][x] else "0"
                    for x in range(self.width)
                ) + "\n"
                for y in range(self.height)
            ),
            encoding="utf-8",
        )
        temporary.replace(path)
        return path

    @classmethod
    def load(cls, path: str | Path) -> "OccupancyGrid":
        path = Path(path)
        data = json.loads(path.read_text(encoding="utf-8"))
        if data.get("format") != "rds-p1-configuration-grid":
            raise ValueError(f"Unsupported map format in {path}")
        resolution = float(data.get("planning_resolution", 1.0))
        fine_free = {tuple(map(int, item)) for item in data.get("configuration_free", [])}
        fine_obstacles = {tuple(map(int, item)) for item in data.get("configuration_obstacles", [])}
        result = cls(
            width=int(data["width"]),
            height=int(data["height"]),
            cells=data["cells"],
            config_name=data.get("config", "unknown"),
            start=tuple(data["start"]) if data.get("start") else None,
            metadata=data.get("metadata", {}),
            coverage=data.get("coverage", []),
            fine_free=fine_free,
            fine_obstacles=fine_obstacles,
            planning_resolution=resolution,
            origin=tuple(map(int, data.get("origin", (0, 0)))),
        )
        # Contact observations may sit just outside the visited bounding box;
        # they are not claimed to be safe configurations.
        if any(not result.in_bounds((math.floor(x * resolution), math.floor(y * resolution)))
               for x, y in fine_free):
            raise ValueError("Free configuration point outside the observed map")
        return result

    def draw(self, surface: pygame.Surface, density: int) -> None:
        overlay = pygame.Surface(surface.get_size(), pygame.SRCALPHA)
        for y, row in enumerate(self.coverage):
            for x, covered in enumerate(row):
                if covered:
                    pygame.draw.rect(
                        overlay,
                        (45, 200, 90, 80),
                        ((x + self.origin[0]) * density,
                         (y + self.origin[1]) * density, density, density),
                    )
        # Contacts are configuration-space observations, not necessarily whole
        # occupied floor cells, so draw compact red markers instead of a false
        # full-cell obstacle fill.
        for key in self.fine_obstacles:
            x, y = self.key_to_world(key, self.planning_resolution)
            pygame.draw.circle(
                overlay, (230, 55, 55, 150),
                (round(x * density), round(y * density)), max(2, density // 7)
            )
        surface.blit(overlay, (0, 0))


class SparseExplorationMap:
    """Online observations without a predefined origin or map dimensions.

    Coordinates remain in the simulator's odometric world frame. Only after
    exploration ends do the observed minima/maxima define a dense matrix.
    """

    planning_resolution = FINE_RESOLUTION
    key_to_world = staticmethod(OccupancyGrid.key_to_world)

    def __init__(self, config_name: str, start: FloatPoint):
        self.config_name = config_name
        self.start = start
        self.fine_free: set[FineKey] = set()
        self.fine_obstacles: set[FineKey] = set()
        self.covered: set[Point] = set()

    def world_to_key(self, point: FloatPoint, resolution: float | None = None) -> FineKey:
        resolution = resolution or self.planning_resolution
        key = (round(point[0] / resolution), round(point[1] / resolution))
        if math.dist(self.key_to_world(key, resolution), point) > 1e-7:
            raise ValueError(f"Point {point} is not aligned to resolution {resolution}")
        return key

    @staticmethod
    def configuration_in_bounds(point: FloatPoint) -> bool:
        # The robot has no global boundaries; the proximity sensor decides.
        return all(math.isfinite(value) for value in point)

    def add_free_pose(self, point: FloatPoint) -> None:
        key = self.world_to_key(point, self.planning_resolution)
        self.fine_free.add(key)
        self.fine_obstacles.discard(key)
        x, y = point
        for sample_y in (y - 0.5, y + 0.5):
            for sample_x in (x - 0.5, x + 0.5):
                self.covered.add((math.floor(sample_x), math.floor(sample_y)))

    def add_obstacle_pose(self, point: FloatPoint) -> None:
        key = self.world_to_key(point, self.planning_resolution)
        if key not in self.fine_free:
            self.fine_obstacles.add(key)

    def covered_points(self) -> set[Point]:
        return set(self.covered)

    def finalize(self) -> OccupancyGrid:
        if not self.covered:
            raise ValueError("Cannot finalize an empty exploration")
        observed = set(self.covered)
        observed.update((math.floor(x * self.planning_resolution),
                         math.floor(y * self.planning_resolution))
                        for x, y in self.fine_free | self.fine_obstacles)
        min_x = min(x for x, _ in observed)
        max_x = max(x for x, _ in observed)
        min_y = min(y for _, y in observed)
        max_y = max(y for _, y in observed)
        grid = OccupancyGrid(
            max_x - min_x + 1, max_y - min_y + 1,
            config_name=self.config_name, start=self.start,
            fine_free=set(self.fine_free), fine_obstacles=set(self.fine_obstacles),
            origin=(min_x, min_y),
        )
        for point in self.covered:
            grid.coverage[point[1] - min_y][point[0] - min_x] = 1
        for key in self.fine_obstacles:
            world = self.key_to_world(key, self.planning_resolution)
            if all(abs(v - round(v)) < 1e-7 for v in world):
                grid.set((round(world[0]), round(world[1])), Cell.OBSTACLE)
        for key in self.fine_free:
            world = self.key_to_world(key, self.planning_resolution)
            if all(abs(v - round(v)) < 1e-7 for v in world):
                grid.set((round(world[0]), round(world[1])), Cell.FREE)
        grid.metadata["observed_bounds"] = {
            "min_x": min_x, "max_x": max_x, "min_y": min_y, "max_y": max_y,
        }
        return grid

    def draw(self, surface: pygame.Surface, density: int) -> None:
        overlay = pygame.Surface(surface.get_size(), pygame.SRCALPHA)
        for x, y in self.covered:
            pygame.draw.rect(overlay, (45, 200, 90, 80),
                             (x * density, y * density, density, density))
        for key in self.fine_obstacles:
            x, y = self.key_to_world(key, self.planning_resolution)
            pygame.draw.circle(overlay, (230, 55, 55, 150),
                               (round(x * density), round(y * density)),
                               max(2, density // 7))
        surface.blit(overlay, (0, 0))


def _angle_delta(current: float, target: float) -> float:
    return (target - current + 180.0) % 360.0 - 180.0


class MotionController:
    """Closed-loop point controller for the simulator's fixed-speed vacuum."""

    def __init__(self, simulation, robot, render: bool = True, frame_callback=None):
        self.simulation = simulation
        self.robot = robot
        self.render = render
        self.frame_callback = frame_callback
        self.frames = 0

    def _update(self) -> None:
        self.simulation.update()
        self.frames += 1
        if self.frame_callback is not None:
            self.frame_callback(self.simulation.screen["display"], self.frames)

    def rotate_towards(self, target: FloatPoint) -> None:
        dx = target[0] - self.robot.position[0]
        dy = target[1] - self.robot.position[1]
        if abs(dx) < 1e-12 and abs(dy) < 1e-12:
            return
        desired = math.degrees(math.atan2(-dy, dx)) % 360.0
        delta = _angle_delta(self.robot.orientation, desired)
        self.robot.stop()
        if abs(delta) > 1e-9:
            self.robot.rotate(delta)

    def go_to(self, target: FloatPoint, tolerance: float = 1e-6,
              max_frames: int = 10_000) -> bool:
        """Drive straight to a target; return False on contact/early stop."""
        self.rotate_towards(target)
        previous = math.dist(self.robot.position, target)
        if previous <= tolerance:
            return True
        self.robot.start()
        for _ in range(max_frames):
            # Query the contact footprint before commanding the next physical
            # step.  The original flow learned the same fact by colliding and
            # incrementing the simulator's collision counter.
            self.robot.check_proximity()
            if self.robot.sensor["proximity"]["front"]:
                self.robot.stop()
                self.robot.forward_path_is_blocked = False
                return False
            before = self.robot.position
            self._update()
            if not self.simulation.is_running:
                self.robot.stop()
                raise InterruptedError("Simulation closed during motion")
            distance = math.dist(self.robot.position, target)
            if distance <= tolerance:
                self.robot.stop()
                return True
            if self.robot.position == before or not self.robot.is_running:
                self.robot.stop()
                return False
            if distance > previous + 1e-7:
                self.robot.stop()
                return distance <= tolerance
            previous = distance
        self.robot.stop()
        raise RuntimeError(f"Motion timeout while driving to {target}")

    def try_step(self, source: FloatPoint, target: FloatPoint,
                 step: float = FINE_RESOLUTION) -> bool:
        distance = abs(source[0] - target[0]) + abs(source[1] - target[1])
        if abs(distance - step) > 1e-7:
            raise ValueError(f"Coverage moves must be cardinal steps of {step}")
        ok = self.go_to(target)
        if ok:
            return True
        # A collision may happen after the first 0.5-cell step.  Return to the
        # exact lattice point so exploration remains drift-free.
        if math.dist(self.robot.position, source) > 1e-7:
            if not self.go_to(source):
                raise RuntimeError("Could not retreat after probing an obstacle")
        return False

    def try_adjacent(self, source: Point, target: Point) -> bool:
        """Backward-compatible one-cell probe used by older callers."""
        return self.try_step(source, target, 1.0)


@dataclass
class CoverageResult:
    visited: set[FineKey]
    obstacles: set[FineKey]
    trajectory: list[FineKey]
    probes: int
    frames: int


class CompleteCoverageExplorer:
    """Online DFS coverage over the robot's configuration-space lattice.

    Every reachable half-cell centre pose is visited.  Unlike a wall follower,
    DFS backtracks from dead ends and has a finite termination condition.
    """

    def __init__(self, grid: OccupancyGrid, controller: MotionController):
        self.grid = grid
        self.controller = controller

    def run(self, max_probes: int | None = None) -> CoverageResult:
        start_world = tuple(float(v) for v in self.controller.robot.position)
        start = self.grid.world_to_key(start_world, self.grid.planning_resolution)
        if not self.grid.configuration_in_bounds(start_world):
            raise ValueError(f"Start {start_world} is unsafe for the 2x2 robot")

        visited: set[Point] = {start}
        obstacles: set[Point] = set()
        trajectory = [start]
        self.grid.add_free_pose(start_world)
        # Each stack entry stores the cell and its next neighbour index.
        stack: list[list] = [[start, 0]]
        probes = 0

        while stack and self.controller.simulation.is_running:
            current, direction_index = stack[-1]
            if direction_index >= len(CARDINALS):
                stack.pop()
                if stack:
                    parent = stack[-1][0]
                    current_world = self.grid.key_to_world(current, self.grid.planning_resolution)
                    parent_world = self.grid.key_to_world(parent, self.grid.planning_resolution)
                    if not self.controller.try_step(
                        current_world, parent_world, self.grid.planning_resolution
                    ):
                        raise RuntimeError("A previously traversed edge became blocked")
                    trajectory.append(parent)
                continue

            dx, dy = CARDINALS[direction_index]
            stack[-1][1] += 1
            neighbour = (current[0] + dx, current[1] + dy)
            if neighbour in visited or neighbour in obstacles:
                continue
            neighbour_world = self.grid.key_to_world(
                neighbour, self.grid.planning_resolution
            )
            if not self.grid.configuration_in_bounds(neighbour_world):
                obstacles.add(neighbour)
                continue

            probes += 1
            if max_probes is not None and probes > max_probes:
                raise RuntimeError("Coverage probe limit reached")
            current_world = self.grid.key_to_world(
                current, self.grid.planning_resolution
            )
            if self.controller.try_step(
                current_world, neighbour_world, self.grid.planning_resolution
            ):
                visited.add(neighbour)
                obstacles.discard(neighbour)
                self.grid.add_free_pose(neighbour_world)
                trajectory.append(neighbour)
                stack.append([neighbour, 0])
            else:
                obstacles.add(neighbour)
                # At half-cell resolution a probe is exactly one simulator
                # movement.  Contact depends on the target footprint, so this
                # pose is globally non-traversable in the static world.
                self.grid.add_obstacle_pose(neighbour_world)

        if not self.controller.simulation.is_running:
            raise RuntimeError("Simulation closed before coverage completed")
        return CoverageResult(
            visited=visited,
            obstacles=obstacles,
            trajectory=trajectory,
            probes=probes,
            frames=self.controller.frames,
        )


def _heuristic(a: FineKey, b: FineKey) -> int:
    return abs(a[0] - b[0]) + abs(a[1] - b[1])


def astar(grid: OccupancyGrid, start: FloatPoint, goal: FloatPoint) -> list[FloatPoint]:
    """Optimal four-connected A* at the map's measured planning resolution."""
    resolution = grid.active_resolution
    start_key = grid.world_to_key(start, resolution)
    goal_key = grid.world_to_key(goal, resolution)
    free = grid.planning_keys()
    if start_key not in free or goal_key not in free:
        raise ValueError("A* endpoints must be known FREE cells")
    frontier: list[tuple[int, int, FineKey]] = [(0, 0, start_key)]
    counter = 0
    came_from: dict[FineKey, FineKey | None] = {start_key: None}
    cost: dict[FineKey, int] = {start_key: 0}

    while frontier:
        _, _, current = heappop(frontier)
        if current == goal_key:
            break
        for dx, dy in CARDINALS:
            neighbour = (current[0] + dx, current[1] + dy)
            if neighbour not in free:
                continue
            new_cost = cost[current] + 1
            if neighbour not in cost or new_cost < cost[neighbour]:
                cost[neighbour] = new_cost
                came_from[neighbour] = current
                counter += 1
                heappush(
                    frontier,
                    (new_cost + _heuristic(neighbour, goal_key), counter, neighbour),
                )
    if goal_key not in came_from:
        raise ValueError(f"No route from {start} to {goal}")
    path: list[FineKey] = []
    current: FineKey | None = goal_key
    while current is not None:
        path.append(current)
        current = came_from[current]
    return [grid.key_to_world(key, resolution) for key in reversed(path)]


def smooth_path(grid: OccupancyGrid, path: list[FloatPoint]) -> list[FloatPoint]:
    """Safely compress a grid path into maximal straight cardinal segments.

    Any-angle string pulling is attractive, but an occupancy value at integer
    centres does not certify the continuous swept volume of this 2x2 robot.
    Keeping the A* geometry while removing redundant collinear waypoints gives
    exact arrival and preserves the collision guarantee of the explored grid.
    """
    if len(path) <= 2:
        return path[:]
    result = [path[0]]
    previous_direction = (
        path[1][0] - path[0][0], path[1][1] - path[0][1]
    )
    for index in range(1, len(path) - 1):
        direction = (
            path[index + 1][0] - path[index][0],
            path[index + 1][1] - path[index][1],
        )
        if direction != previous_direction:
            result.append(path[index])
            previous_direction = direction
    result.append(path[-1])
    return result


def execute_path(controller: MotionController, points: Iterable[FloatPoint]) -> None:
    points = list(points)
    if not points:
        return
    for point in points[1:]:
        if not controller.go_to(point, tolerance=1e-6):
            raise RuntimeError(f"Unexpected obstacle while following path at {point}")


@dataclass
class RecordedRoute:
    name: str
    config: str
    waypoints: list[FloatPoint] = field(default_factory=list)
    created_at: float = field(default_factory=time)

    def add(self, point: FloatPoint) -> None:
        candidate = (round(point[0], 3), round(point[1], 3))
        if not self.waypoints or math.dist(self.waypoints[-1], candidate) > 1e-6:
            self.waypoints.append(candidate)

    def save(self, path: str | Path) -> Path:
        path = Path(path)
        path.parent.mkdir(parents=True, exist_ok=True)
        payload = {
            "format": "rds-p1-waypoints",
            "version": 1,
            "name": self.name,
            "config": self.config,
            "created_at": self.created_at,
            "waypoints": [list(point) for point in self.waypoints],
        }
        temporary = path.with_suffix(path.suffix + ".tmp")
        temporary.write_text(json.dumps(payload, indent=2), encoding="utf-8")
        temporary.replace(path)
        return path

    @classmethod
    def load(cls, path: str | Path) -> "RecordedRoute":
        data = json.loads(Path(path).read_text(encoding="utf-8"))
        if data.get("format") != "rds-p1-waypoints":
            raise ValueError("Unsupported route format")
        waypoints = data.get("waypoints")
        if not isinstance(waypoints, list) or not waypoints:
            raise ValueError("A recorded route needs at least one waypoint")
        parsed: list[FloatPoint] = []
        for index, point in enumerate(waypoints):
            if (not isinstance(point, (list, tuple)) or len(point) != 2
                    or isinstance(point[0], bool) or isinstance(point[1], bool)):
                raise ValueError(f"Invalid waypoint at index {index}")
            try:
                candidate = (float(point[0]), float(point[1]))
            except (TypeError, ValueError) as exc:
                raise ValueError(f"Invalid waypoint at index {index}") from exc
            if not all(math.isfinite(value) for value in candidate):
                raise ValueError(f"Non-finite waypoint at index {index}")
            parsed.append(candidate)
        config = str(data.get("config", "unknown"))
        if not config or Path(config).name != config:
            raise ValueError("Route configuration must be a local file name")
        return cls(
            name=str(data.get("name", "route")),
            config=config,
            waypoints=parsed,
            created_at=float(data.get("created_at", 0.0)),
        )


def surface_cells_for_keys(keys: Iterable[FineKey], width: int, height: int,
                           resolution: float = FINE_RESOLUTION) -> set[Point]:
    """Floor cells covered by the robot footprint at a set of poses."""
    covered: set[Point] = set()
    for key in keys:
        x, y = OccupancyGrid.key_to_world(key, resolution)
        for sample_y in (y - 0.5, y + 0.5):
            for sample_x in (x - 0.5, x + 0.5):
                cell = (math.floor(sample_x), math.floor(sample_y))
                if 0 <= cell[0] < width and 0 <= cell[1] < height:
                    covered.add(cell)
    return covered


def reachable_truth(environment, density: int, start: FloatPoint,
                    resolution: float = FINE_RESOLUTION) -> set[FineKey]:
    """Independent ground-truth oracle used only by tests/metrics."""
    from rds2026machines import VACUUM_SIZE

    half = VACUUM_SIZE // 2

    def pose_is_free(x: float, y: float) -> bool:
        if not (half <= x <= environment.size[0] - half
                and half <= y <= environment.size[1] - half):
            return False
        rect = pygame.Rect(0, 0, VACUUM_SIZE * density, VACUUM_SIZE * density)
        # Match the simulator's Rect property assignment semantics.  Passing
        # floats to the Rect constructor truncates instead of rounding and
        # creates a subtly different oracle at half-cell positions.
        rect.x = (x - half) * density
        rect.y = (y - half) * density
        return not any(rect.colliderect(obj["bbox"]) for obj in environment.objects)

    max_x = round((environment.size[0] - half) / resolution)
    max_y = round((environment.size[1] - half) / resolution)
    min_key = round(half / resolution)
    free: set[FineKey] = set()
    for key_y in range(min_key, max_y + 1):
        for key_x in range(min_key, max_x + 1):
            x, y = OccupancyGrid.key_to_world((key_x, key_y), resolution)
            if pose_is_free(x, y):
                free.add((key_x, key_y))
    start_key = (round(start[0] / resolution), round(start[1] / resolution))
    if start_key not in free:
        return set()
    reached = {start_key}
    pending = [start_key]
    while pending:
        current = pending.pop()
        for dx, dy in CARDINALS:
            nxt = (current[0] + dx, current[1] + dy)
            if nxt in free and nxt not in reached:
                reached.add(nxt)
                pending.append(nxt)
    return reached
