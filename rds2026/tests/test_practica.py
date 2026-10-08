"""Comprobaciones automáticas: un assert incumplido hace fallar la prueba.

Ejecutar desde rds2026: python -m unittest discover -s tests -v.
Los tests unitarios verifican funciones pequeñas; los de integración conectan
mapa, planificador y simulador. No sustituyen la demostración con teclado.
"""

import json
import os
from pathlib import Path
import subprocess
import tempfile
import unittest
from unittest.mock import patch

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


# Pruebas pequeñas de representaciones y planificación, sin recorrer un piso.
class UnitTests(unittest.TestCase):
    def test_robot_state_is_not_shared(self):
        """Modificar un robot no debe alterar los sensores de otro."""
        first = rds2026machines.vacuum((2, 3), 90)
        second = rds2026machines.vacuum((8, 9), 180)
        first.sensor["position"] = (99, 99)
        self.assertEqual(second.sensor["position"], (8, 9))
        self.assertEqual(second.sensor["orientation"], 180)

    def test_astar_avoids_obstacle_and_compresses_turns(self):
        """Una pared obliga a rodear; comprimir quita puntos, no origen ni destino."""
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
        """Guardar y cargar debe conservar poses finas y orden de waypoints."""
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
        """Una posición entre centros enteros puede cubrir cuatro celdas distintas."""
        grid = OccupancyGrid(5, 5)
        self.assertTrue(grid.configuration_in_bounds((4.0, 4.0)))
        grid.add_free_pose((1.5, 1.5))
        self.assertEqual(grid.covered_points(), {(1, 1), (1, 2), (2, 1), (2, 2)})

    def test_map_dimensions_are_derived_after_exploration(self):
        """La matriz nace después de explorar y admite un origen distinto de cero."""
        # Incluir coordenadas negativas comprueba que no asumimos origen (0,0).
        # Antes de finalize no hay ancho; después se conserva el origen al guardar.
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
        """Una ruta no debe elegir un fichero de escenario fuera del directorio."""
        with tempfile.TemporaryDirectory() as directory:
            route_path = Path(directory) / "bad.json"
            route_path.write_text(json.dumps({
                "format": "rds-p1-waypoints", "config": "../cfg_0.py",
                "waypoints": [[1, 1]]
            }), encoding="utf-8")
            with self.assertRaises(ValueError):
                RecordedRoute.load(route_path)


class NavigationRejectionTests(unittest.TestCase):
    """B debe conservar el destino y rechazarlo antes de iniciar el simulador."""

    def setUp(self):
        """Crear dos zonas libres separadas para aislar los rechazos del apartado B."""
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.map_path = str(Path(self.temp.name) / "disconnected.json")
        grid = OccupancyGrid(8, 5, config_name="cfg_3.py")
        for point in ((2, 2), (2.5, 2), (5, 2), (5.5, 2), (5, 2.5), (5.5, 2.5)):
            grid.add_free_pose(point)
        grid.add_obstacle_pose((3, 2))
        grid.save(self.map_path)

    def test_blocked_unknown_and_invalid_endpoints_do_not_start_simulation(self):
        """Validar el extremo antes de cargar el entorno o intentar mover el robot."""
        cases = (
            ((2, 2), (3, 2), "Destino.*obstáculo"),
            ((2, 2), (4, 2), "Destino.*no explorada"),
            ((3, 2), (2, 2), "Origen.*obstáculo"),
            ((2, 2), (2.75, 2), "Destino.*no se permite ajustar"),
            ((2, 2), (2.25, 2.25), "Destino.*no se permite ajustar"),
            ((2, 2), (8, 2), "Destino.*fuera del mapa"),
            ((2, 2), (float("nan"), 2), "Destino.*finitas"),
        )
        with patch("apartado_b.rds2026environment.floorplan") as environment:
            for start, goal, reason in cases:
                with self.subTest(start=start, goal=goal):
                    with self.assertRaisesRegex(ValueError, reason):
                        navigate(self.map_path, None, start, goal, 0, True)
            environment.assert_not_called()

    def test_astar_rejects_free_destination_in_another_component(self):
        """Ser libre no basta: tiene que existir camino desde el origen."""
        # Los dos extremos son libres, pero no existe camino entre ellos.
        # La versión antigua cambiaba el destino a la componente de (2, 2).
        with patch("apartado_b.rds2026environment.floorplan") as environment:
            with self.assertRaisesRegex(ValueError, "A\\* no encuentra una ruta"):
                navigate(self.map_path, None, (2, 2), (5, 2), 0, True)
            environment.assert_not_called()

    def test_local_discretization_does_not_hide_disconnected_destination(self):
        """Ajustar decimales localmente no debe cambiar de habitación el destino."""
        # Sus cuatro vértices son libres, pero pertenecen a otra componente.
        with patch("apartado_b.rds2026environment.floorplan") as environment:
            with self.assertRaisesRegex(ValueError, "zonas desconectadas"):
                navigate(self.map_path, None, (2, 2), (5.2, 2.2), 0, True)
            environment.assert_not_called()

    def test_command_line_explains_rejection_without_traceback(self):
        """El terminal debe explicar el rechazo y acabar con código de error 1."""
        result = subprocess.run(
            [sys.executable, str(ROOT / "apartado_b.py"), "--map", self.map_path,
             "--start", "2,2", "--goal", "5,2", "--headless", "--fps", "0"],
            capture_output=True, text=True, check=False,
        )
        self.assertEqual(result.returncode, 1)
        self.assertIn("[B] Destino", result.stderr)
        self.assertIn("A* no encuentra una ruta", result.stderr)
        self.assertNotIn("Traceback", result.stderr)
        self.assertNotIn("path_length", result.stdout)


# Pruebas con el simulador real: descubrir cfg_3 y usar ese mapa en B y C.
# Los archivos temporales evitan sobrescribir mapas o rutas del usuario.
class IntegrationTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        """Explorar cfg_3 una vez; las pruebas de B/C reutilizan este mapa temporal."""
        cls.temp = tempfile.TemporaryDirectory()
        cls.map_path = str(Path(cls.temp.name) / "cfg3.json")
        cls.txt_path = str(Path(cls.temp.name) / "cfg3.txt")
        cls.coverage = run_coverage(
            "cfg_3.py", (7, 7), 0, True, cls.map_path, cls.txt_path
        )

    @classmethod
    def tearDownClass(cls):
        """Borrar solo el directorio temporal creado por este grupo de pruebas."""
        cls.temp.cleanup()

    def test_complete_coverage(self):
        # 100 % del conjunto alcanzable y ningún choque; se comprueban por
        # separado las posiciones del centro y la superficie de su huella.
        self.assertEqual(self.coverage["coverage_percent"], 100.0)
        self.assertEqual(self.coverage["pose_coverage_percent"], 100.0)
        self.assertEqual(self.coverage["missed_cells"], 0)
        self.assertEqual(self.coverage["missed_poses"], 0)
        self.assertEqual(self.coverage["unexpected_cells"], 0)
        self.assertEqual(self.coverage["collisions"], 0)

    def test_long_navigation(self):
        """Recorrer el mapa de A y comprobar llegada y contador de colisiones."""
        metrics = navigate(self.map_path, None, (2, 2), (12, 12), 0, True, True)
        self.assertEqual(metrics["final_error"], 0.0)
        self.assertEqual(metrics["collisions"], 0)

    def test_arbitrary_points_are_safely_snapped(self):
        """Medir el ajuste local para decimales con vecinos conocidos libres."""
        # Ambas coordenadas están en intervalos con todos sus vértices libres.
        metrics = navigate(self.map_path, None, (2.2, 2.2), (11.8, 11.8), 0, True, True)
        self.assertLessEqual(metrics["start_snap_distance"], 0.36)
        self.assertLessEqual(metrics["goal_snap_distance"], 0.36)
        self.assertEqual(metrics["final_error"], 0.0)
        self.assertEqual(metrics["collisions"], 0)

    def test_real_map_wall_is_rejected_instead_of_snapped(self):
        """Distinguir pared observada, zona desconocida y ajuste local no permitido."""
        with patch("apartado_b.rds2026environment.floorplan") as environment:
            cases = (((9.5, 3), "obstáculo"), ((10, 3), "no explorada"),
                     ((9.25, 3), "no se permite ajustar"))
            for goal, reason in cases:
                with self.subTest(goal=goal):
                    with self.assertRaisesRegex(ValueError, f"Destino.*{reason}"):
                        navigate(self.map_path, None, (2, 2), goal, 0, True)
            environment.assert_not_called()

    def test_route_replay(self):
        """Reproducir una ruta válida con el simulador y comprobar sus medidas."""
        route_path = Path(self.temp.name) / "route.json"
        RecordedRoute("integration", "cfg_3.py",
                      [(2, 2), (9, 2), (12, 12), (7, 7)]).save(route_path)
        metrics = replay(str(route_path), self.map_path, 0, True)
        self.assertEqual(metrics["final_error"], 0.0)
        self.assertEqual(metrics["collisions"], 0)
        self.assertEqual(metrics["max_snap_distance"], 0.0)


if __name__ == "__main__":
    unittest.main(verbosity=2)
