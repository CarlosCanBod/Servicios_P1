#!/usr/bin/env python3
"""Recortar y concatenar cuatro tramos del resumen P1 ya existente.

No inicia la simulación ni vuelve a grabar demostraciones. Los rangos de
frames son intervalos semiabiertos del resumen a 30 fps: se incluye el
fotograma inicial y se excluye el final.
"""

from __future__ import annotations

import hashlib
import json
import argparse
from pathlib import Path
import re
import subprocess

import imageio.v2 as imageio
import imageio_ffmpeg
from PIL import Image, ImageDraw, ImageFont

ROOT = Path(__file__).resolve().parent
VIDEO_DIR = ROOT / "output" / "video" / "practica"
INPUT = VIDEO_DIR / "resumen_completo.mp4"
OUTPUT = VIDEO_DIR / "entrega_2min.mp4"
METRICS = VIDEO_DIR / "metricas.json"
MANIFEST = VIDEO_DIR / "entrega_2min.json"
REVIEW_DIR = VIDEO_DIR / "revision" / "entrega_2min"
FPS = 30
SIZE = (700, 700)
SELECTED = [
    {"name": "A · cfg_0.py (muebles)", "video": "A_muebles.mp4", "start": 0, "end": 1427},
    {"name": "B · cfg_0.py (muebles)", "video": "B_muebles.mp4", "start": 3690, "end": 4110},
    {"name": "C · cfg_0.py (muebles)", "video": "C_muebles.mp4", "start": 5425, "end": 6268},
    {"name": "C · cfg_laberinto.py", "video": "C_laberinto.mp4", "start": 7138, "end": 8046},
]


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def get_ffmpeg() -> str:
    return imageio_ffmpeg.get_ffmpeg_exe()


def decoded_frame_count(path: Path) -> int:
    """Decodificar el vídeo entero y leer el contador final de ffmpeg."""
    result = subprocess.run(
        [get_ffmpeg(), "-v", "info", "-i", str(path), "-map", "0:v:0", "-f", "null", "-"],
        check=True, capture_output=True, text=True,
    )
    counts = re.findall(r"frame=\s*(\d+)", result.stderr)
    if not counts:
        raise RuntimeError(f"ffmpeg no informó el número de frames para {path}")
    return int(counts[-1])


def validate_selection(metrics: dict, actual_frames: int, input_meta: dict) -> list[dict]:
    rows = metrics.get("cases", [])
    expected_total = sum(row["video_info"]["frames"] for row in rows)
    if len(rows) != 12 or expected_total != actual_frames:
        raise ValueError(f"El resumen no coincide con el inventario: 12 clips/{expected_total} frames "
                         f"esperados, {actual_frames} frames decodificados")
    if input_meta.get("fps") != FPS or tuple(input_meta.get("size", ())) != SIZE:
        raise ValueError(f"Formato inesperado en el resumen: {input_meta}")

    offsets = {}
    offset = 0
    for row in rows:
        name = Path(row["video"]).name
        offsets[name] = {"start": offset, "end": offset + row["video_info"]["frames"]}
        offset += row["video_info"]["frames"]
    for chunk in SELECTED:
        expected = offsets.get(chunk["video"])
        if expected != {"start": chunk["start"], "end": chunk["end"]}:
            raise ValueError(f"Rango cambiado para {chunk['video']}: {chunk} frente a {expected}")
        if not (0 <= chunk["start"] < chunk["end"] <= actual_frames):
            raise ValueError(f"Rango fuera del resumen: {chunk}")
    chosen_frames = sum(chunk["end"] - chunk["start"] for chunk in SELECTED)
    if chosen_frames != 3598:
        raise ValueError(f"La selección esperada es 3598 frames; se obtuvo {chosen_frames}")
    return rows


def capture_review(path: Path, chapter: dict, time_seconds: float, label: str) -> Path:
    REVIEW_DIR.mkdir(parents=True, exist_ok=True)
    destination = REVIEW_DIR / f"{chapter['file_key']}_{label}.png"
    subprocess.run(
        [get_ffmpeg(), "-y", "-v", "error", "-ss", f"{time_seconds:.6f}", "-i", str(path),
         "-frames:v", "1", str(destination)],
        check=True, stdout=subprocess.DEVNULL, stderr=subprocess.PIPE,
    )
    return destination


def make_contact_sheet(paths: list[Path]) -> Path:
    tile_w, tile_h, label_h = 350, 350, 30
    sheet = Image.new("RGB", (tile_w * 2, (tile_h + label_h) * 2), "white")
    draw = ImageDraw.Draw(sheet)
    font = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf", 16)
    for index, path in enumerate(paths):
        col, row = index % 2, index // 2
        x, y = col * tile_w, row * (tile_h + label_h)
        image = Image.open(path).convert("RGB").resize((tile_w, tile_h))
        sheet.paste(image, (x, y + label_h))
        draw.text((x + 6, y + 6), path.stem.replace("_", " · "), font=font, fill="#102a43")
    destination = REVIEW_DIR / "contacto_entrega_2min.jpg"
    sheet.save(destination, quality=90)
    return destination


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--review-only", action="store_true",
                        help="extraer la captura de movimiento B sin volver a recortar el vídeo")
    args = parser.parse_args()
    if args.review_only:
        manifest = json.loads(MANIFEST.read_text(encoding="utf-8"))
        for item in manifest["chapters"]:
            previous = item.pop("review_frame", None)
            item.setdefault("review_frames", [])
            if previous and previous not in item["review_frames"]:
                item["review_frames"].append(previous)
        chapter = next(item for item in manifest["chapters"]
                       if item["source_video"] == "B_muebles.mp4")
        chapter["file_key"] = "B_muebles"
        review = capture_review(OUTPUT, chapter, chapter["start_seconds"] + 9.0, "movimiento")
        chapter.setdefault("review_frames", [])
        movement_frame = str(review.relative_to(ROOT))
        if movement_frame not in chapter["review_frames"]:
            chapter["review_frames"].append(movement_frame)
        chapter.pop("file_key", None)
        MANIFEST.write_text(json.dumps(manifest, indent=2, ensure_ascii=False), encoding="utf-8")
        print(f"Captura de movimiento B guardada: {review.relative_to(ROOT)} (sin reencodear)")
        return
    if not INPUT.is_file() or not METRICS.is_file():
        raise SystemExit("Falta el resumen original o su inventario metricas.json")
    metrics = json.loads(METRICS.read_text(encoding="utf-8"))
    input_hash = sha256(INPUT)
    clip_hashes = {
        row["video"]: sha256(ROOT / row["video"])
        for row in metrics["cases"]
    }
    reader = imageio.get_reader(INPUT)
    input_meta = reader.get_meta_data()
    reader.close()
    frame_count = decoded_frame_count(INPUT)
    validate_selection(metrics, frame_count, input_meta)

    chapters = []
    out_offset = 0
    for chunk in SELECTED:
        count = chunk["end"] - chunk["start"]
        chapters.append({
            "title": chunk["name"],
            "source_video": chunk["video"],
            "source_frames": [chunk["start"], chunk["end"]],
            "output_frames": [out_offset, out_offset + count],
            "start_seconds": round(out_offset / FPS, 6),
            "end_seconds": round((out_offset + count) / FPS, 6),
            "frame_count": count,
        })
        out_offset += count

    intervals = "+".join(
        f"between(n\\,{chunk['start']}\\,{chunk['end'] - 1})" for chunk in SELECTED
    )
    filter_expr = f"select={intervals},setpts=N/({FPS}*TB)"
    subprocess.run([
        get_ffmpeg(), "-y", "-v", "error", "-i", str(INPUT), "-map", "0:v:0", "-an",
        "-vf", filter_expr, "-fps_mode", "cfr", "-r", str(FPS), "-c:v", "libx264",
        "-crf", "18", "-pix_fmt", "yuv420p", "-movflags", "+faststart", str(OUTPUT),
    ], check=True, stdout=subprocess.DEVNULL, stderr=subprocess.PIPE)

    output_reader = imageio.get_reader(OUTPUT)
    output_meta = output_reader.get_meta_data()
    output_reader.close()
    output_count = decoded_frame_count(OUTPUT)
    expected_duration = 3598 / FPS
    if output_count != 3598 or output_meta.get("fps") != FPS:
        raise RuntimeError(f"Salida incorrecta: {output_count} frames a {output_meta.get('fps')} fps")
    if tuple(output_meta.get("size", ())) != SIZE:
        raise RuntimeError(f"Resolución inesperada: {output_meta.get('size')}")
    if abs(output_count / FPS - expected_duration) > 1e-9:
        raise RuntimeError("La duración no coincide con el número de frames seleccionado")

    review_paths = []
    for chapter, chunk in zip(chapters, SELECTED):
        chapter["file_key"] = Path(chunk["video"]).stem
        if chunk["video"] == "A_muebles.mp4":
            review_points = [(23.0, "avance")]
        elif chunk["video"] == "B_muebles.mp4":
            review_points = [(3.8, "rechazo"), (9.0, "movimiento")]
        else:
            # En los dos clips C, duración menos cinco segundos cae en replay.
            local_time = metrics["cases"][[row["video"] for row in metrics["cases"]].index(
                f"output/video/practica/{chunk['video']}")]["video_info"]["duration_seconds"] - 5.0
            review_points = [(local_time, "replay_rojo")]
        chapter["review_frames"] = []
        for local_time, label in review_points:
            chapter_time = chapter["start_seconds"] + local_time
            path = capture_review(OUTPUT, chapter, chapter_time, label)
            chapter["review_frames"].append(str(path.relative_to(ROOT)))
            if label in ("avance", "rechazo", "replay_rojo"):
                # Una muestra representativa por cada uno de los cuatro fragmentos.
                review_paths.append(path)
        del chapter["file_key"]
    contact_sheet = make_contact_sheet(review_paths)

    # Confirmar que ni la fuente ni ninguno de sus doce MP4 de origen cambiaron.
    if sha256(INPUT) != input_hash:
        raise RuntimeError("El resumen de origen cambió durante el recorte")
    changed_clips = [name for name, before in clip_hashes.items()
                     if sha256(ROOT / name) != before]
    if changed_clips:
        raise RuntimeError(f"Cambió algún MP4 fuente: {changed_clips}")

    manifest = {
        "format": "video-entrega-p1-selection",
        "source_video": str(INPUT.relative_to(ROOT)),
        "source_sha256": input_hash,
        "source_total_frames": frame_count,
        "source_fps": input_meta["fps"],
        "source_resolution": list(input_meta["size"]),
        "source_clips_sha256": clip_hashes,
        "selection": [{key: value for key, value in chunk.items() if key != "file_key"}
                      for chunk in SELECTED],
        "frame_range_convention": "[inicio, fin): inicio incluido y frame final excluido",
        "output_video": str(OUTPUT.relative_to(ROOT)),
        "output_sha256": sha256(OUTPUT),
        "output_frames": output_count,
        "output_fps": output_meta["fps"],
        "output_resolution": list(output_meta["size"]),
        "duration_seconds": round(output_count / FPS, 6),
        "decode_verified": True,
        "chapters": [{key: value for key, value in chapter.items() if key != "file_key"}
                     for chapter in chapters],
        "review_contact_sheet": str(contact_sheet.relative_to(ROOT)),
    }
    MANIFEST.write_text(json.dumps(manifest, indent=2, ensure_ascii=False), encoding="utf-8")
    print(json.dumps({key: manifest[key] for key in (
        "output_video", "output_frames", "output_fps", "output_resolution",
        "duration_seconds", "output_sha256", "decode_verified", "review_contact_sheet",
    )}, indent=2, ensure_ascii=False))


if __name__ == "__main__":
    main()
