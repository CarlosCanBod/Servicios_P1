import json
import os
from pathlib import Path
import tempfile
import unittest

os.environ.setdefault("SDL_VIDEODRIVER", "dummy")

import sys
ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
os.chdir(ROOT)

import rds2026machines
from apartado_a import run_coverage
from apartado_b import navigate
from apartado_c import replay
from robotica_servicios import Cell, OccupancyGrid, RecordedRoute, SparseExplorationMap, astar, smooth_path


class UnitTests(unittest.TestCase):
    def test_robot_state_is_not_shared(self):
        first = rds2026machines.vacuum((2, 3), 90)
        second = rds2026machines.vacuum((8, 9), 180)
        first.sensor["position"] = (99, 99)
        self.assertEqual(second.sensor["position"], (8, 9))
        self.assertEqual(second.sensor["orientation"], 180)

    def test_astar_avoids_obstacle_and_compresses_turns(self):
        grid = OccupancyGrid(7, 7)
        for y in range(1, 6):
            for x in range(1, 6):
                grid.set((x, y), Cell.FREE)
        for y in range(1, 5):
            grid.set((3, y), Cell.OBSTACLE)
        path = astar(grid, (1, 1), (5, 1))
        self.assertNotIn((3, 1), path)
        self.assertEqual(path[0], (1, 1))
        self.assertEqual(path[-1], (5, 1))
        self.assertLess(len(smooth_path(grid, path)), len(path))

    def test_map_and_route_round_trip(self):
        with tempfile.TemporaryDirectory() as directory:
            grid_path = Path(directory) / "map.json"
            route_path = Path(directory) / "route.json"
            grid = OccupancyGrid(4, 3, config_name="cfg_test.py", start=(1, 1))
            grid.set((1, 1), Cell.FREE)
            grid.add_free_pose((1.5, 1.5))
            grid.save(grid_path)
            self.assertEqual(OccupancyGrid.load(grid_path).get((1, 1)), Cell.FREE)
            self.assertTrue(OccupancyGrid.load(grid_path).is_free((1.5, 1.5)))
            route = RecordedRoute("test", "cfg_test.py", [(1, 1), (2, 1)])
            route.save(route_path)
            self.assertEqual(RecordedRoute.load(route_path).waypoints[-1], (2.0, 1.0))

    def test_half_step_pose_covers_corner_cells(self):
        grid = OccupancyGrid(5, 5)
        self.assertTrue(grid.configuration_in_bounds((4.0, 4.0)))
        grid.add_free_pose((1.5, 1.5))
        self.assertEqual(grid.covered_points(), {(1, 1), (1, 2), (2, 1), (2, 2)})

    def test_map_dimensions_are_derived_after_exploration(self):
        observations = SparseExplorationMap("cfg_test.py", (-2, 3))
        self.assertFalse(hasattr(observations, "width"))
        observations.add_free_pose((-2, 3))
        observations.add_free_pose((1.5, 4.5))
        observations.add_obstacle_pose((2, 4.5))
        grid = observations.finalize()
        self.assertEqual(grid.origin, (-3, 2))
        self.assertEqual((grid.width, grid.height), (6, 4))
        self.assertIn((-3, 2), grid.covered_points())
        self.assertTrue(grid.is_free((1.5, 4.5)))
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "map.json"
            grid.save(path)
            loaded = OccupancyGrid.load(path)
            self.assertEqual(loaded.origin, grid.origin)
            self.assertEqual(loaded.covered_points(), grid.covered_points())

    def test_malformed_route_is_rejected(self):
        with tempfile.TemporaryDirectory() as directory:
            route_path = Path(directory) / "bad.json"
            route_path.write_text(json.dumps({
                "format": "rds-p1-waypoints", "config": "../cfg_0.py",
                "waypoints": [[1, 1]]
            }), encoding="utf-8")
            with self.assertRaises(ValueError):
                RecordedRoute.load(route_path)


class IntegrationTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.temp = tempfile.TemporaryDirectory()
        cls.map_path = str(Path(cls.temp.name) / "cfg3.json")
        cls.txt_path = str(Path(cls.temp.name) / "cfg3.txt")
        cls.coverage = run_coverage(
            "cfg_3.py", (7, 7), 0, True, cls.map_path, cls.txt_path
        )

    @classmethod
    def tearDownClass(cls):
        cls.temp.cleanup()

    def test_complete_coverage(self):
        self.assertEqual(self.coverage["coverage_percent"], 100.0)
        self.assertEqual(self.coverage["pose_coverage_percent"], 100.0)
        self.assertEqual(self.coverage["missed_cells"], 0)
        self.assertEqual(self.coverage["missed_poses"], 0)
        self.assertEqual(self.coverage["unexpected_cells"], 0)
        self.assertEqual(self.coverage["collisions"], 0)

    def test_long_navigation(self):
        metrics = navigate(self.map_path, None, (2, 2), (12, 12), 0, True, True)
        self.assertEqual(metrics["final_error"], 0.0)
        self.assertEqual(metrics["collisions"], 0)

    def test_arbitrary_points_are_safely_snapped(self):
        metrics = navigate(self.map_path, None, (2.2, 2.2), (11.8, 11.8), 0, True, True)
        self.assertLessEqual(metrics["start_snap_distance"], 0.36)
        self.assertLessEqual(metrics["goal_snap_distance"], 0.36)
        self.assertEqual(metrics["final_error"], 0.0)
        self.assertEqual(metrics["collisions"], 0)

    def test_route_replay(self):
        route_path = Path(self.temp.name) / "route.json"
        RecordedRoute("integration", "cfg_3.py",
                      [(2, 2), (9, 2), (12, 12), (7, 7)]).save(route_path)
        metrics = replay(str(route_path), self.map_path, 0, True)
        self.assertEqual(metrics["final_error"], 0.0)
        self.assertEqual(metrics["collisions"], 0)
        self.assertEqual(metrics["max_snap_distance"], 0.0)


if __name__ == "__main__":
    unittest.main(verbosity=2)
