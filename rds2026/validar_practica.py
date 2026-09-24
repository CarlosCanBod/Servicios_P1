#!/usr/bin/python
"""Run the reproducible end-to-end acceptance suite and save its metrics."""

from __future__ import annotations

import json
import os
from pathlib import Path

os.environ.setdefault("SDL_VIDEODRIVER", "dummy")

from apartado_a import DEFAULT_STARTS, run_coverage
from apartado_b import navigate
from apartado_c import replay


ENDPOINTS = {
    "cfg_0.py": ((23, 7), (2, 26)),
    "cfg_1.py": ((2, 2), (23, 23)),
    "cfg_2.py": ((2, 2), (39, 40)),
    "cfg_3.py": ((2, 2), (12, 12)),
}


def main() -> None:
    root = Path(__file__).resolve().parent
    os.chdir(root)
    output = root / "resultados"
    output.mkdir(exist_ok=True)
    report = {"coverage": {}, "navigation": {}, "replay": {}}
    for config, start in DEFAULT_STARTS.items():
        stem = Path(config).stem
        map_path = output / f"mapa_{stem}.json"
        report["coverage"][config] = run_coverage(
            config, start, 0, True, str(map_path),
            str(output / f"mapa_{stem}.txt"),
        )
        nav_start, nav_goal = ENDPOINTS[config]
        report["navigation"][config] = navigate(
            str(map_path), config, nav_start, nav_goal, 0, True, True
        )
    report["replay"]["cfg_3.py"] = replay(
        "rutas/ruta_demo_cfg3.json", "resultados/mapa_cfg_3.json", 0, True
    )
    destination = output / "diagnostico.json"
    destination.write_text(json.dumps(report, indent=2), encoding="utf-8")
    print(json.dumps(report, indent=2))
    print(f"Saved {destination}")


if __name__ == "__main__":
    main()
