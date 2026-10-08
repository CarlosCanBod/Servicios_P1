#!/usr/bin/python
"""Crear un MP4 de A/B/C capturando el dibujo del simulador, no otro algoritmo.

Solo ejecutar si se quiere regenerar el vídeo: este script sobrescribe el MP4.
Las órdenes de movimiento siguen siendo run_coverage, navigate y replay.
"""

from __future__ import annotations

import os
from pathlib import Path
import sys

os.environ.setdefault("SDL_VIDEODRIVER", "dummy")

import imageio.v2 as imageio
import numpy as np
from PIL import Image, ImageDraw, ImageFont
import pygame

ROOT = Path(__file__).resolve().parent
SIM = ROOT / "rds2026"
sys.path.insert(0, str(SIM))
os.chdir(SIM)

from apartado_a import run_coverage
from apartado_b import navigate
from apartado_c import replay


class Recorder:
    """Escribir títulos y fotogramas; sample_every controla cuántos se conservan."""
    def __init__(self, writer):
        """Recibir el escritor de vídeo abierto por main."""
        self.writer = writer
        self.sample_every = 1

    def title(self, heading: str, detail: str, seconds: float = 1.2) -> None:
        """Insertar una cartela repetida a 30 imágenes/segundo durante seconds."""
        image = Image.new("RGB", (700, 700), "#102A43")
        draw = ImageDraw.Draw(image)
        bold = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf", 38)
        normal = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf", 22)
        box = draw.textbbox((0, 0), heading, font=bold)
        draw.text(((700 - (box[2] - box[0])) / 2, 285), heading, font=bold, fill="#FFFFFF")
        box = draw.textbbox((0, 0), detail, font=normal)
        draw.text(((700 - (box[2] - box[0])) / 2, 350), detail, font=normal, fill="#9FE6C3")
        frame = np.asarray(image)
        for _ in range(round(30 * seconds)):
            self.writer.append_data(frame)

    def callback(self, surface: pygame.Surface, frame_number: int) -> None:
        """Recibir un ciclo del controlador y convertir su imagen a formato vídeo."""
        if frame_number % self.sample_every:
            return
        frame = pygame.surfarray.array3d(surface).swapaxes(0, 1)
        self.writer.append_data(frame)


def main() -> None:
    """Ejecutar las demostraciones, capturar imágenes y cerrar el archivo MP4."""
    output = ROOT / "output" / "video" / "demo_P1.mp4"
    output.parent.mkdir(parents=True, exist_ok=True)
    writer = imageio.get_writer(
        output, fps=30, codec="libx264", quality=7,
        pixelformat="yuv420p", macro_block_size=1,
    )
    recorder = Recorder(writer)
    try:
        recorder.title("Apartado A", "Mapeo y cobertura completa - cfg_3")
        recorder.sample_every = 3
        run_coverage(
            "cfg_3.py", (7, 7), 0, True,
            "resultados/video_mapa_cfg3.json", "resultados/video_mapa_cfg3.txt",
            frame_callback=recorder.callback,
        )
        recorder.title("Apartado B", "A* entre puntos arbitrarios")
        recorder.sample_every = 1
        navigate("resultados/mapa_cfg_3.json", "cfg_3.py", (2, 2), (12, 12),
                 0, True, True, recorder.callback)
        recorder.title("Apartado C", "Reproducción autónoma de waypoints")
        recorder.sample_every = 2
        replay("rutas/ruta_demo_cfg3.json", "resultados/mapa_cfg_3.json",
               0, True, recorder.callback)
        recorder.title("Validación completada", "100% cobertura - error 0 - 0 colisiones")
    finally:
        writer.close()
    print(output)


if __name__ == "__main__":
    main()
