#!/usr/bin/env python3
"""Construir un ZIP autocontenido con los programas y recursos de P1.

La lista explícita evita incluir entornos, archivos temporales y rutas locales.
Los nombres dentro del archivo son relativos a una única carpeta raíz.
"""

from __future__ import annotations

from datetime import datetime, timezone
import hashlib
from pathlib import Path, PurePosixPath
import shutil
from zipfile import ZIP_DEFLATED, ZipFile

ROOT = Path(__file__).resolve().parent
PACKAGE = "P1_Robotica_Servicios"
DESTINATION = ROOT / "output" / "entrega" / f"{PACKAGE}.zip"
BACKUPS = ROOT.parent / "Preparacion_P1" / "copias"


def package_files() -> dict[str, Path]:
    """Relacionar cada nombre del paquete con su archivo fuente actual."""
    files = {
        "README.md": ROOT / "readme.MD",
        "requirements.txt": ROOT / "requirements.txt",
        "memoria_P1.pdf": ROOT / "output/pdf/memoria_P1.pdf",
        "video_P1.mp4": ROOT / "output/video/practica/entrega_2min.mp4",
        "rds2026/README_SOLUCION.md": ROOT / "rds2026/README_SOLUCION.md",
        "rds2026/tests/test_practica.py": ROOT / "rds2026/tests/test_practica.py",
        "rds2026/rutas/ruta_demo_cfg3.json": ROOT / "rds2026/rutas/ruta_demo_cfg3.json",
        "rds2026/resultados/diagnostico.json": ROOT / "rds2026/resultados/diagnostico.json",
    }
    programs = (
        "apartado_a.py", "apartado_b.py", "apartado_c.py", "robotica_servicios.py",
        "rds2026environment.py", "rds2026machines.py", "rds2026simulation.py",
        "validar_practica.py", "cfg_0.py", "cfg_1.py", "cfg_2.py", "cfg_3.py",
        "cfg_1_copy.py", "cfg_laberinto.py", "cfg_pilares_grande.py",
        "cfg_pilares.py", "cfg_prueba.py",
    )
    for name in programs:
        files[f"rds2026/{name}"] = ROOT / "rds2026" / name
    for path in sorted((ROOT / "rds2026/img").glob("*.png")):
        files[f"rds2026/img/{path.name}"] = path
    for index in range(4):
        for suffix in ("json", "txt"):
            name = f"mapa_cfg_{index}.{suffix}"
            files[f"rds2026/resultados/{name}"] = ROOT / "rds2026/resultados" / name
    extra_maps = {"interior": "cfg_1_copy", "laberinto": "cfg_laberinto",
                  "pilares": "cfg_pilares_grande"}
    data = ROOT / "output/video/practica/datos"
    for example, config in extra_maps.items():
        for suffix in ("json", "txt"):
            files[f"rds2026/resultados/mapa_{config}.{suffix}"] = data / f"mapa_{example}.{suffix}"
    for example in ("muebles", "interior", "laberinto", "pilares"):
        files[f"rds2026/rutas/ruta_{example}.json"] = data / f"ruta_{example}.json"
    return files


def main() -> None:
    files = package_files()
    for name, source in files.items():
        relative = PurePosixPath(name)
        if relative.is_absolute() or ".." in relative.parts:
            raise ValueError(f"Nombre no permitido: {name}")
        if not source.is_file() or source.is_symlink():
            raise ValueError(f"Falta un archivo regular: {source}")
        if not source.resolve().is_relative_to(ROOT):
            raise ValueError(f"Fuente fuera del proyecto: {source}")

    DESTINATION.parent.mkdir(parents=True, exist_ok=True)
    temporary = DESTINATION.with_suffix(".zip.tmp")
    hashes = {}
    with ZipFile(temporary, "w", compression=ZIP_DEFLATED, compresslevel=6) as archive:
        for name, source in sorted(files.items()):
            payload = source.read_bytes()
            hashes[name] = hashlib.sha256(payload).hexdigest()
            archive.writestr(f"{PACKAGE}/{name}", payload)
        checksum_text = "".join(f"{digest}  {name}\n" for name, digest in hashes.items())
        archive.writestr(f"{PACKAGE}/SHA256SUMS", checksum_text.encode("utf-8"))

    # Verificar el CRC y el contenido antes de sustituir el archivo anterior.
    with ZipFile(temporary) as archive:
        damaged = archive.testzip()
        if damaged:
            raise RuntimeError(f"Error CRC en {damaged}")
        for name, expected in hashes.items():
            actual = hashlib.sha256(archive.read(f"{PACKAGE}/{name}")).hexdigest()
            if actual != expected:
                raise RuntimeError(f"Contenido distinto de la fuente: {name}")

    if DESTINATION.exists():
        BACKUPS.mkdir(parents=True, exist_ok=True)
        stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
        backup = BACKUPS / f"{PACKAGE}_anterior_{stamp}.zip"
        if backup.exists():
            raise FileExistsError(f"Ya existe la copia de seguridad: {backup}")
        shutil.copy2(DESTINATION, backup)
        print(f"Copia anterior conservada en: {backup}")
    temporary.replace(DESTINATION)
    print(f"ZIP: {DESTINATION}")
    print(f"Archivos: {len(files) + 1}; tamaño: {DESTINATION.stat().st_size} bytes")


if __name__ == "__main__":
    main()
