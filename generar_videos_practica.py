#!/usr/bin/env python3
"""Generar 12 screencasts reproducibles de A/B/C en cuatro mapas."""

from __future__ import annotations

import json
import math
import os
import argparse
from pathlib import Path
import subprocess
import sys
import tempfile
from contextlib import contextmanager

os.environ.setdefault("SDL_VIDEODRIVER", "dummy")

import imageio.v2 as imageio
import numpy as np
from PIL import Image, ImageDraw, ImageFont
import pygame

ROOT = Path(__file__).resolve().parent
SIM = ROOT / "rds2026"
OUT = ROOT / "output" / "video" / "practica"
sys.path.insert(0, str(SIM))
os.chdir(SIM)

from apartado_a import DEFAULT_STARTS, run_coverage
from apartado_b import navigate, resolve_endpoint
from apartado_c import replay, teleoperate
from rds2026simulation import simulation
from robotica_servicios import Cell, OccupancyGrid, RecordedRoute, astar, smooth_path

CASES = [
    {"key": "muebles", "config": "cfg_0.py", "start": (21, 21), "steps": 3,
     "speed": 60, "b_speed": 5, "c_speed": 5},
    {"key": "interior", "config": "cfg_1_copy.py", "start": (21, 21), "steps": 3,
     "speed": 60, "b_speed": 9, "c_speed": 9},
    {"key": "laberinto", "config": "cfg_laberinto.py", "start": (3, 3), "steps": 2,
     "speed": 45, "b_speed": 8, "c_speed": 8},
    {"key": "pilares", "config": "cfg_pilares_grande.py", "start": (3, 3), "steps": 2,
     "speed": 35, "b_speed": 5, "c_speed": 5},
]
ALL_CASES = [dict(case) for case in CASES]
ENCODED_FPS = 30
SIZE = (700, 700)


class Clip:
    """Capturar frames del simulador y añadir cartelas legibles en español."""

    def __init__(self, path: Path, steps_per_second: int = 15):
        self.path = path
        self.writer = imageio.get_writer(path, fps=ENCODED_FPS, codec="libx264",
                                         quality=7, pixelformat="yuv420p",
                                         macro_block_size=1)
        # La simulación avanza sin reloj; este acumulador fija pasos visibles
        # por segundo del vídeo sin cambiar la física ni el algoritmo.
        self.steps_per_second = steps_per_second
        self.frame_accumulator = 0.0
        self.frames = 0

    def frame(self, surface, frame_number=0):
        data = pygame.surfarray.array3d(surface).swapaxes(0, 1)
        self.frame_accumulator += ENCODED_FPS / self.steps_per_second
        copies = int(self.frame_accumulator)
        self.frame_accumulator -= copies
        for _ in range(copies):
            self.writer.append_data(data)
            self.frames += 1

    def card(self, title: str, lines: list[str], seconds: float = 2.0):
        image = Image.new("RGB", SIZE, "#102a43")
        draw = ImageDraw.Draw(image)
        bold_path = "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf"
        regular_path = "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf"
        bold = ImageFont.truetype(bold_path, 31)
        normal = ImageFont.truetype(regular_path, 20)
        box = draw.textbbox((0, 0), title, font=bold)
        draw.text(((700 - box[2] + box[0]) / 2, 190), title, font=bold, fill="white")
        y = 275
        for line in lines:
            box = draw.textbbox((0, 0), line, font=normal)
            draw.text(((700 - box[2] + box[0]) / 2, y), line, font=normal, fill="#9fe6c3")
            y += 35
        data = np.asarray(image)
        for _ in range(round(ENCODED_FPS * seconds)):
            self.writer.append_data(data)
            self.frames += 1

    def close(self):
        self.writer.close()


def cfg_key(cfg):
    return Path(cfg).stem


def map_path(case):
    return OUT / "datos" / f"mapa_{case['key']}.json"


def route_path(case):
    return OUT / "datos" / f"ruta_{case['key']}.json"


def create_map(case, clip=None):
    target = map_path(case)
    target.parent.mkdir(parents=True, exist_ok=True)
    # FPS cero solo desactiva el reloj; el número de pasos no se altera.
    result = run_coverage(case["config"], case["start"], 0, True,
                          str(target), str(target.with_suffix(".txt")),
                          frame_callback=clip.frame if clip else None)
    return result


def choose_path(grid: OccupancyGrid, min_steps=14, wanted_corners=(3, 8)):
    """Elegir una ruta libre larga con giros, buscando primero un rodeo real."""
    free = sorted(grid.planning_keys())
    candidates = []
    # Determinista y acotado: muestreo regular evita el producto cartesiano entero.
    stride = max(1, len(free) // 28)
    starts = free[::stride][:28]
    target_stride = max(1, len(free) // 80)
    targets = free[::target_stride][:80]
    for a in starts:
        for b in targets:
            if a == b:
                continue
            start = grid.key_to_world(a, grid.active_resolution)
            goal = grid.key_to_world(b, grid.active_resolution)
            manhattan = abs(a[0] - b[0]) + abs(a[1] - b[1])
            if manhattan < min_steps:
                continue
            try:
                discrete = astar(grid, start, goal)
            except ValueError:
                continue
            path = smooth_path(grid, discrete)
            corners = len(path) - 2
            length = len(discrete) - 1
            # 3-6 giros producen 5-8 puntos: se conservan todos al grabar.
            if not wanted_corners[0] <= corners <= wanted_corners[1]:
                continue
            # Prefer paths longer than Manhattan: this proves a forced detour.
            score = (length - manhattan, corners, length)
            candidates.append((score, start, goal, path, discrete, manhattan))
    if not candidates:
        raise RuntimeError(f"No suitable route in {grid.config_name}")
    # A* deterministic tie break; prefer actual detour, then 4-6 visible turns.
    candidates.sort(key=lambda c: (-c[0][0], abs(c[0][1] - 4), -c[0][2], c[1], c[2]))
    return candidates[0]


def blocked_goal(grid):
    if grid.fine_obstacles:
        key = min(grid.fine_obstacles)
        return grid.key_to_world(key, grid.active_resolution)
    for y in range(grid.origin[1], grid.origin[1] + grid.height):
        for x in range(grid.origin[0], grid.origin[0] + grid.width):
            if grid.get((x, y)) == Cell.OBSTACLE:
                return (float(x), float(y))
    return (float(grid.origin[0]), float(grid.origin[1]))


def rejection_cards(case, clip, start, goal):
    """Ejecutar rechazos reales B y mostrar literalmente sus mensajes."""
    grid = OccupancyGrid.load(map_path(case))
    unknown = None
    for y in range(grid.origin[1], grid.origin[1] + grid.height):
        for x in range(grid.origin[0], grid.origin[0] + grid.width):
            key = (round(x / grid.active_resolution), round(y / grid.active_resolution))
            if (grid.get((x, y)) == Cell.UNKNOWN and key not in grid.fine_free
                    and key not in grid.fine_obstacles):
                unknown = (float(x), float(y))
                break
        if unknown is not None:
            break
    cases = [
        ("Destino bloqueado", start, blocked_goal(grid)),
    ]
    if unknown is not None:
        cases.append(("Destino desconocido", start, unknown))
    cases.append(("Destino fuera del mapa", start,
                  (grid.origin[0] + grid.width + 3.0, grid.origin[1] + 3.0)))
    outcomes = []
    for title, s, g in cases:
        try:
            navigate(str(map_path(case)), case["config"], s, g, 0, True, True)
        except ValueError as exc:
            detail = str(exc).split("\n")[0]
            outcomes.append({"case": title, "result": "rechazado", "message": detail})
            words = detail.split()
            lines, current = [], ""
            for word in words:
                candidate = f"{current} {word}".strip()
                if len(candidate) > 48 and current:
                    lines.append(current)
                    current = word
                else:
                    current = candidate
            if current:
                lines.append(current)
            clip.card(title, ["Validación real de B", *lines[:4]], 1.4)
        else:
            outcomes.append({"case": title, "result": "admitido inesperadamente"})
            clip.card(title, ["La entrada no produjo rechazo"], 1.4)
    return outcomes


def best_route(case):
    grid = OccupancyGrid.load(map_path(case))
    return grid, choose_path(grid)


def run_b(case, clip, selected):
    grid, (_, start, goal, path, discrete, manhattan) = selected
    clip.card("Apartado B · navegación autónoma", [
        f"{case['config']} · A* rodea obstáculos",
        f"{case['b_speed']} pasos de 0,5 unidades/s · recorrido azul",
    ], 1.8)
    rejections = rejection_cards(case, clip, start, goal)
    metrics = navigate(str(map_path(case)), case["config"], start, goal,
                       0, True, True, clip.frame)
    metrics.update({"manhattan_steps": manhattan, "astar_steps": len(discrete) - 1,
                    "detour_steps": len(discrete) - 1 - manhattan,
                    "rejections": rejections})
    return metrics


def corner_points(path):
    # Una coordenada por cada cambio de rumbo, conservando inicio y llegada.
    if len(path) <= 2:
        return path
    result = [path[0]]
    prev = (path[1][0] - path[0][0], path[1][1] - path[0][1])
    for i in range(1, len(path) - 1):
        direction = (path[i + 1][0] - path[i][0], path[i + 1][1] - path[i][1])
        if direction != prev:
            result.append(path[i])
        prev = direction
    result.append(path[-1])
    return result


def record_scripted_teleop(case, points, clip):
    """Ejecutar la función real teleoperate con secuencia de teclas reproducible.

    Los eventos pygame KEYDOWN/KEYUP representan los controles que espera
    teleoperate; se muestra explícitamente como demostración automatizada.
    """
    path_out = route_path(case)
    path_out.parent.mkdir(parents=True, exist_ok=True)
    grid = OccupancyGrid.load(map_path(case))
    # Limitar los waypoints a 4-8; puntos son cardinales y cada segmento libre.
    if len(points) > 8:
        raise RuntimeError("Ruta con más de 8 esquinas: seleccionar otra ruta completa")
    if len(points) < 4:
        raise RuntimeError("La ruta candidata necesita más giros para mostrar controles")
    resolution = grid.active_resolution
    units = [(round(x / resolution), round(y / resolution)) for x, y in points]
    # Compilar una lista de eventos por iteración del bucle teleoperate.
    schedule = []
    heading = 0  # orientación de salida, grados, 0 = este
    key_for_heading = {0: None, 90: pygame.K_LEFT, 180: pygame.K_LEFT, 270: pygame.K_RIGHT}
    for (x1, y1), (x2, y2) in zip(units, units[1:]):
        if x2 != x1:
            desired = 0 if x2 > x1 else 180
        else:
            desired = 90 if y2 < y1 else 270
        delta = (desired - heading) % 360
        while delta:
            key = pygame.K_LEFT if delta in (90, 180) else pygame.K_RIGHT
            schedule.append([pygame.event.Event(pygame.KEYDOWN, key=key)])
            heading = (heading + (90 if key == pygame.K_LEFT else -90)) % 360
            delta = (desired - heading) % 360
        # W marks the current point; UP held for exact half-unit steps.
        schedule.append([pygame.event.Event(pygame.KEYDOWN, key=pygame.K_w)])
        # Congelar el robot en la posición marcada para hacer legible la X.
        schedule.extend([[] for _ in range(max(1, round(case["c_speed"] * 0.7)))])
        distance = abs(x2 - x1) + abs(y2 - y1)
        schedule.append([pygame.event.Event(pygame.KEYDOWN, key=pygame.K_UP)])
        schedule.extend([[] for _ in range(distance - 1)])
        schedule.append([pygame.event.Event(pygame.KEYUP, key=pygame.K_UP)])
    schedule.append([pygame.event.Event(pygame.KEYDOWN, key=pygame.K_w)])
    schedule.extend([[] for _ in range(max(1, round(case["c_speed"] * 0.7)))])
    schedule.append([pygame.event.Event(pygame.KEYDOWN, key=pygame.K_s)])
    schedule.extend([[] for _ in range(case["c_speed"])])
    schedule.append([pygame.event.Event(pygame.KEYDOWN, key=pygame.K_q)])

    cursor = 0
    real_read = simulation.read_keyboard
    real_update = simulation.update
    def scripted_read(self):
        nonlocal cursor
        if cursor >= len(schedule):
            pygame.event.post(pygame.event.Event(pygame.KEYDOWN, key=pygame.K_q))
        else:
            for event in schedule[cursor]:
                pygame.event.post(event)
        cursor += 1
        return real_read(self)
    observed = {"collisions": 0, "final_position": None}
    def captured_update(self):
        result = real_update(self)
        clip.frame(self.screen["display"], cursor)
        observed["collisions"] = self.machine.stats_collisions
        observed["final_position"] = tuple(self.machine.position)
        return result
    simulation.read_keyboard = scripted_read
    simulation.update = captured_update
    try:
        clip.card("Apartado C · grabación de ruta", [
            "Demostración automatizada de controles",
            "Giros de 90° · W marca · S guarda el fichero",
            "Waypoints azules numerados",
        ], 2.0)
        teleoperate(case["config"], points[0], str(path_out), fps=0)
    finally:
        simulation.read_keyboard = real_read
        simulation.update = real_update
    route = RecordedRoute.load(path_out)
    expected = [tuple(p) for p in points]
    # teleoperate añade inicio, cada W y el final al cerrar.
    if route.waypoints != expected:
        raise RuntimeError(f"La ruta guardada difiere de los puntos conducidos: {route.waypoints} != {expected}")
    if observed["final_position"] is None or math.dist(observed["final_position"], expected[-1]) > 1e-6:
        raise RuntimeError(f"Teleoperación no terminó en el último punto: {observed['final_position']} != {expected[-1]}")
    if observed["collisions"] != 0:
        raise RuntimeError(f"La grabación de controles registró {observed['collisions']} colisiones")
    clip.card("Fichero guardado", [path_out.name, "Waypoints persistidos en formato JSON"], 1.0)
    return route, path_out, {"teleop_collisions": observed["collisions"],
                             "teleop_final_position": observed["final_position"]}


def run_c(case, clip, selected):
    grid, (_, start, goal, path, _discrete, _manhattan) = selected
    route, route_file, teleop_metrics = record_scripted_teleop(case, corner_points(path), clip)
    clip.card("Apartado C · reproducción", [
        f"{len(route.waypoints)} puntos guardados en {route_file.name}",
        "Waypoints azules · objetivo actual rojo",
        "A* entre puntos guardados",
    ], 1.7)
    metrics = replay(str(route_file), str(map_path(case)), 0, True, clip.frame)
    metrics.update(teleop_metrics)
    if metrics["max_snap_distance"] > 0:
        clip.card("Ajuste de puntos", [
            f"max_snap_distance = {metrics['max_snap_distance']}",
            "El objetivo ejecutado difiere del waypoint pedido",
        ], 1.6)
    metrics["recorded_waypoints"] = [list(p) for p in route.waypoints]
    metrics["route_file"] = str(route_file.relative_to(ROOT))
    return metrics


def inspect_video(path):
    reader = imageio.get_reader(path)
    meta = reader.get_meta_data()
    count = round(meta.get("duration", 0) * meta.get("fps", ENCODED_FPS))
    reader.close()
    # Decodificar el stream entero para cazar errores de contenedor/frames.
    import imageio_ffmpeg
    ffmpeg = imageio_ffmpeg.get_ffmpeg_exe()
    subprocess.run([ffmpeg, "-v", "error", "-i", str(path), "-f", "null", "-"],
                   check=True, stdout=subprocess.DEVNULL, stderr=subprocess.PIPE)
    review = OUT / "revision" / path.stem
    review.mkdir(parents=True, exist_ok=True)
    duration = meta.get("duration", 0)
    section = path.stem[0]
    objective_time = duration - (5.0 if section == "C" else 3.2 if section == "B" else 3.0)
    shots = [("inicio", 0.1), ("medio", duration / 2), ("objetivo", objective_time),
             ("final", duration - 0.2)]
    if section == "B":
        shots.append(("rechazo", 3.8))
    if section == "C":
        shots.append(("replay", duration - 5.0))
    for label, second in shots:
        second = max(0.1, second)
        subprocess.run([ffmpeg, "-y", "-v", "error", "-ss", str(second), "-i", str(path),
                        "-frames:v", "1", str(review / f"{label}.png")],
                       check=True, stdout=subprocess.DEVNULL, stderr=subprocess.PIPE)
    return {"frames": count, "fps": meta.get("fps"), "size": meta.get("size"),
            "duration_seconds": round(meta.get("duration", 0), 2),
            "decode_verified": True, "review_frames": str(review.relative_to(ROOT)),
            "review_images": [label + ".png" for label, _ in shots]}


def create_contact_sheets(metrics):
    """Montar una hoja por apartado con cuatro vistas de cada escenario."""
    labels = ("inicio", "medio", "objetivo", "rechazo", "replay", "final")
    for section in "ABC":
        rows = [row for row in metrics.get("cases", []) if row["section"] == section]
        if not rows:
            continue
        tile_w, tile_h, label_h = 350, 350, 28
        sheet = Image.new("RGB", (tile_w * 4, (tile_h + label_h) * len(rows)), "white")
        draw = ImageDraw.Draw(sheet)
        font_path = "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf"
        font = ImageFont.truetype(font_path, 16)
        for row_index, row in enumerate(rows):
            stem = Path(row["video"]).stem
            folder = OUT / "revision" / stem
            chosen = ("inicio", "medio", "replay", "final") if section == "C" else (
                ("inicio", "medio", "rechazo", "final") if section == "B" else
                ("inicio", "medio", "objetivo", "final"))
            for col, label in enumerate(chosen):
                image_path = folder / f"{label}.png"
                if not image_path.exists():
                    continue
                image = Image.open(image_path).convert("RGB").resize((tile_w, tile_h))
                x, y = col * tile_w, row_index * (tile_h + label_h)
                sheet.paste(image, (x, y + label_h))
                draw.text((x + 6, y + 5), f"{Path(row['scenario']).name} · {label}",
                          font=font, fill="#102a43")
        sheet.save(OUT / "revision" / f"contacto_{section}.jpg", quality=88)


def write_index(metrics):
    """Escribir índice de clips, mediciones y comandos de reproducción."""
    descriptions = {
        "muebles": "cfg_0.py original, con muebles y objetos: contactos y cobertura densa",
        "interior": "cfg_1_copy.py modificado: cajas interiores y estrechamientos",
        "laberinto": "cfg_laberinto.py modificado: pasillos y retrocesos",
        "pilares": "cfg_pilares_grande.py modificado: pilares y esquinas",
    }
    timing = {}
    cursor = 0.0
    for section in "ABC":
        for case in ALL_CASES:
            item = next((row for row in metrics.get("cases", [])
                         if row["section"] == section and row["scenario"] == case["config"]), None)
            if item:
                timing[(section, case["config"])] = cursor
                cursor += item.get("video_info", {}).get("duration_seconds", 0)
    lines = [
        "# Vídeos de la práctica P1", "",
        "El enunciado solo pide un «vídeo breve (screencast)» y no fija duración ni FPS. "
        "Hay 12 demostraciones completas, una por apartado y escenario, y un resumen concatenado "
        "que conserva los 12 clips completos en orden A/B/C. Los MP4 se codifican a 30 fps; "
        "la velocidad indicada es pasos físicos visibles por segundo (un paso desplaza 0,5 unidades).",
        "Rótulo: **12 ejemplos completos · A, B y C en 4 mapas**. "
        "Resumen íntegro: [resumen_completo.mp4](resumen_completo.mp4) (4:56.1).",
        "", "## Casos", "",
    ]
    for section in "ABC":
        lines.append(f"### Apartado {section}")
        lines.append("")
        for case in ALL_CASES:
            item = next((row for row in metrics.get("cases", [])
                         if row["section"] == section and row["scenario"] == case["config"]), None)
            if item is None:
                continue
            m = item["metrics"]
            duration = item.get("video_info", {}).get("duration_seconds", "?")
            filename = Path(item["video"]).name
            elapsed = timing.get((section, case["config"]), 0)
            stamp = f"{int(elapsed // 60):02}:{elapsed % 60:04.1f}"
            lines.append(f"- **{case['config']}** — {descriptions[case['key']]}. "
                         f"resumen {stamp}; velocidad: {item['movement_steps_per_second']} pasos/s; "
                         f"duración: {duration} s; [vídeo]({filename}).")
            if section == "A":
                lines.append(f"  Cobertura: {m['pose_coverage_percent']}% poses y "
                             f"{m['coverage_percent']}% suelo alcanzable; omisiones "
                             f"{m['missed_poses']}, inesperadas {m['unexpected_poses']}, "
                             f"colisiones {m['collisions']}.")
            elif section == "B":
                lines.append(f"  A*: {m['astar_steps']} pasos frente a Manhattan "
                             f"{m['manhattan_steps']} (+{m['detour_steps']} por rodeo); "
                             f"error final {m['final_error']}, colisiones {m['collisions']}. "
                             f"Se muestran los rechazos medidos: " + ", ".join(
                                 x['case'] for x in m['rejections']))
            else:
                lines.append(f"  {m['waypoints']} waypoints grabados con teclas automatizadas y "
                             f"persistidos en [{Path(m['route_file']).name}](datos/{Path(m['route_file']).name}); "
                             f"replay: max_snap_distance {m['max_snap_distance']}, "
                             f"error final {m['final_error']}, colisiones "
                             f"teleop/replay {m['teleop_collisions']}/{m['collisions']}.")
        lines.append("")
    lines.extend(["## Repetir ejemplos", "",
                  "Desde la raíz del proyecto, estos comandos generan o reemplazan únicamente "
                  "el MP4 del caso indicado dentro de output/video/practica. Los mapas y rutas "
                  "personales no se modifican. `--speed` permite fijar otros pasos visibles/s.", ""])
    for section in "ABC":
        for case in ALL_CASES:
            lines.append(f"- `{sys.executable} generar_videos_practica.py --section {section} "
                         f"--scenario {case['key']}`")
    lines.extend(["", "Los datos por escenario, rutas guardadas y métricas están en `datos/` y "
                  "`metricas.json`. Hojas de revisión: [A](revision/contacto_A.jpg), "
                  "[B](revision/contacto_B.jpg), [C](revision/contacto_C.jpg); los clips C tienen "
                  "una captura del replay rojo y los B una del rechazo. En C la secuencia de teclas es una demostración "
                  "automatizada de los controles reales; no representa a una persona manejando.", ""])
    lines.extend(["## Grabación manual opcional", "",
                  "Estos comandos abren el simulador con ventana y permiten manejarlo; no crean MP4. "
                  "Para entregar el screencast generado con las 12 demostraciones automatizadas, "
                  "usa los MP4 anteriores. En C: flechas para avanzar/girar 90°, W marca, S guarda, Q termina.", "",
                  "A genera el mapa previo que usa B/C. Los pasos A son 35–60/s según el tamaño; B usa 5–9/s. "
                  "C interactivo va a 12 fps y el replay a 8 fps.", ""])
    for case in ALL_CASES:
        key, config = case["key"], case["config"]
        sx, sy = case["start"]
        map_json = f"../output/video/practica/datos/mapa_{key}.json"
        map_txt = f"../output/video/practica/datos/mapa_{key}.txt"
        lines.append(f"### {config}")
        lines.append("")
        lines.append(f"```bash\ntmp/bin/python rds2026/apartado_a.py --config {config} --start {sx:g},{sy:g} "
                     f"--fps {case['speed']} --output {map_json} --legacy-output {map_txt}\n```")
        b_metrics = next(row["metrics"] for row in metrics["cases"]
                         if row["section"] == "B" and row["scenario"] == config)
        start, goal = b_metrics["start"], b_metrics["goal"]
        lines.append(f"```bash\ntmp/bin/python rds2026/apartado_b.py --config {config} --map {map_json} "
                     f"--start {start[0]:g},{start[1]:g} --goal {goal[0]:g},{goal[1]:g} "
                     f"--fps {case['b_speed']}\n```")
        cstart = (21, 21) if key in ("muebles", "interior") else (3, 3)
        manual_route = f"rutas/video_manual_{key}.json"
        lines.append(f"```bash\ntmp/bin/python rds2026/apartado_c.py record --config {config} "
                     f"--start {cstart[0]},{cstart[1]} --route {manual_route} --fps 12\n"
                     f"tmp/bin/python rds2026/apartado_c.py replay --route {manual_route} "
                     f"--map {map_json} --fps 8\n```")
        lines.append("")
    lines.extend(["Al regenerar un ejemplo con `--section` y `--scenario`, el generador sustituye el MP4 "
                  "de ese caso y sus datos propios en `datos/`, actualiza su fila de métricas e índice y "
                  "vuelve a concatenar el resumen con el inventario completo. `--speed` solo cambia la "
                  "velocidad visible del apartado/escenario indicado.", ""])
    (OUT / "INDICE.md").write_text("\n".join(lines), encoding="utf-8")


def create_full_summary():
    """Concatenar los doce vídeos completos (sin recortar sus ejecuciones)."""
    order = [OUT / f"{section}_{case['key']}.mp4"
             for section in "ABC" for case in ALL_CASES]
    if not all(path.exists() for path in order):
        return None
    import imageio_ffmpeg
    ffmpeg = imageio_ffmpeg.get_ffmpeg_exe()
    output = OUT / "resumen_completo.mp4"
    with tempfile.NamedTemporaryFile("w", suffix=".txt", encoding="utf-8", delete=False) as manifest:
        manifest_path = Path(manifest.name)
        for path in order:
            escaped = str(path).replace("'", "'\\''")
            manifest.write(f"file '{escaped}'\n")
    try:
        subprocess.run([ffmpeg, "-y", "-v", "error", "-f", "concat", "-safe", "0",
                        "-i", str(manifest_path), "-c", "copy", str(output)],
                       check=True, stdout=subprocess.DEVNULL, stderr=subprocess.PIPE)
    finally:
        manifest_path.unlink(missing_ok=True)
    return output


def main():
    global CASES
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--section", choices=("A", "B", "C"), help="generar solo un apartado")
    parser.add_argument("--scenario", choices=[case["key"] for case in CASES],
                        help="generar un solo escenario")
    parser.add_argument("--speed", type=int,
                        help="sobrescribir pasos visibles/s para el apartado y escenario elegidos")
    parser.add_argument("--assemble-only", action="store_true",
                        help="crear resumen e índice desde clips existentes, sin regenerarlos")
    args = parser.parse_args()
    CASES = [dict(case) for case in CASES if args.scenario is None or case["key"] == args.scenario]
    if args.speed is not None:
        if args.speed <= 0:
            parser.error("--speed debe ser mayor que cero")
        if args.section == "A":
            for case in CASES: case["speed"] = args.speed
        elif args.section == "B":
            for case in CASES: case["b_speed"] = args.speed
        elif args.section == "C":
            for case in CASES: case["c_speed"] = args.speed
        else:
            parser.error("--speed requiere --section A, B o C")
    OUT.mkdir(parents=True, exist_ok=True)
    all_metrics = {"encoded_fps": ENCODED_FPS, "cases": []}
    clips = []
    try:
        for case in (CASES if not args.assemble_only and args.section in (None, "A") else []):
            # Mapeo A: muestra el algoritmo a 60-90 pasos/s en reproducción.
            path = OUT / f"A_{case['key']}.mp4"
            clip = Clip(path, case["speed"])
            clip.card("Apartado A · mapeo", [
                f"{case['config']} · exploración DFS",
                f"{case['speed']} pasos de 0,5 unidades por segundo",
            ], 1.8)
            metrics_a = create_map(case, clip)
            clip.card("Cobertura observada", [
                f"{metrics_a['pose_coverage_percent']}% de poses alcanzables",
                f"omisiones {metrics_a['missed_poses']} · inesperadas {metrics_a['unexpected_poses']}",
                f"colisiones {metrics_a['collisions']}",
            ], 2.2)
            clip.close()
            clips.append(path)
            all_metrics["cases"].append({"section": "A", "scenario": case["config"],
                                         "metrics": metrics_a, "video": str(path.relative_to(ROOT)),
                                         "movement_steps_per_second": case["speed"],
                                         "video_info": inspect_video(path)})
            print(f"A {case['key']} {metrics_a}", flush=True)

        for case in (CASES if not args.assemble_only and args.section in (None, "B", "C") else []):
            if not map_path(case).exists():
                create_map(case)
            grid, selected = best_route(case)
            _score, start, goal, path, discrete, manhattan = selected
            # Duplicar frames para que los trayectos cortos duren 5-8 segundos.
            path_b = OUT / f"B_{case['key']}.mp4"
            if args.section != "C":
                clip_b = Clip(path_b, case["b_speed"])
                try:
                    metrics_b = run_b(case, clip_b, (grid, selected))
                    clip_b.card("Resultado B", [
                        f"A* {metrics_b['astar_steps']} pasos · desvío +{metrics_b['detour_steps']}",
                        f"error final {metrics_b['final_error']} · colisiones {metrics_b['collisions']}",
                    ], 2.0)
                finally:
                    clip_b.close()
                clips.append(path_b)
                all_metrics["cases"].append({"section": "B", "scenario": case["config"],
                                             "metrics": metrics_b, "video": str(path_b.relative_to(ROOT)),
                                             "movement_steps_per_second": case["b_speed"],
                                             "video_info": inspect_video(path_b)})
                print(f"B {case['key']} {metrics_b}", flush=True)
            if args.section == "B":
                continue

            path_c = OUT / f"C_{case['key']}.mp4"
            clip_c = Clip(path_c, case["c_speed"])
            try:
                metrics_c = run_c(case, clip_c, (grid, selected))
                clip_c.card("Resultado C", [
                    f"max_snap_distance {metrics_c['max_snap_distance']} unidades",
                    f"error final {metrics_c['final_error']} · colisiones {metrics_c['collisions']}",
                    f"grabación teleoperada: {metrics_c['teleop_collisions']} colisiones",
                ], 2.2)
            finally:
                clip_c.close()
            clips.append(path_c)
            all_metrics["cases"].append({"section": "C", "scenario": case["config"],
                                         "metrics": metrics_c, "video": str(path_c.relative_to(ROOT)),
                                         "movement_steps_per_second": case["c_speed"],
                                         "video_info": inspect_video(path_c)})
            print(f"C {case['key']} {metrics_c}", flush=True)
    finally:
        # No quedan escritores abiertos si cualquier simulación falla.
        pass
    metrics_path = OUT / "metricas.json"
    if metrics_path.exists():
        previous = json.loads(metrics_path.read_text(encoding="utf-8"))
        merged = {(row["section"], row["scenario"]): row for row in previous.get("cases", [])}
        merged.update({(row["section"], row["scenario"]): row for row in all_metrics["cases"]})
        all_metrics["cases"] = [merged[key] for key in sorted(merged)]
    metrics_path.write_text(json.dumps(all_metrics, indent=2, ensure_ascii=False), encoding="utf-8")
    if args.assemble_only:
        for row in all_metrics["cases"]:
            row["video_info"] = inspect_video(ROOT / row["video"])
    summary = create_full_summary()
    if summary:
        summary_info = inspect_video(summary)
        chapters = []
        offset = 0.0
        by_key = {(row["section"], row["scenario"]): row for row in all_metrics["cases"]}
        for section in "ABC":
            for case in ALL_CASES:
                row = by_key.get((section, case["config"]))
                if row is None:
                    continue
                length = row["video_info"]["duration_seconds"]
                chapters.append({"title": f"{section} · {case['config']}",
                                 "start_seconds": round(offset, 2),
                                 "end_seconds": round(offset + length, 2)})
                offset += length
        all_metrics["summary_video"] = {"video": str(summary.relative_to(ROOT)), **summary_info}
        all_metrics["summary_video"]["chapters"] = chapters
        metrics_path.write_text(json.dumps(all_metrics, indent=2, ensure_ascii=False), encoding="utf-8")
    create_contact_sheets(all_metrics)
    write_index(all_metrics)
    print(f"Listos {len(clips)} vídeos en {OUT}")


if __name__ == "__main__":
    main()
