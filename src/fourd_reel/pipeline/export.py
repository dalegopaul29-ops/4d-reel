"""Pillar 5 — Cross-Platform Omni-Format Adapters (fully real today).

One project, one storyline, N aspect exports. True volumetric/Gaussian-splat
output is research-stage and deliberately NOT promised here.
"""
from pathlib import Path
from typing import List, Tuple
from ..models import AspectRatio
from .assemble import conform_vertical

FORMATS = {"9:16": (1080, 1920), "16:9": (1920, 1080),
           "1:1": (1080, 1080), "4:5": (1080, 1350)}


def resolution_for(fmt: str) -> Tuple[int, int]:
    if fmt not in FORMATS:
        raise ValueError(f"unknown format {fmt}; choose from {sorted(FORMATS)}")
    return FORMATS[fmt]


def export_plan(src: Path, out_dir: Path, formats: List[str]) -> List[Tuple[int, int, Path]]:
    plan = []
    for fmt in formats:
        w, h = resolution_for(fmt)
        out = Path(out_dir) / f"{Path(src).stem}_{fmt.replace(':','x')}.mp4"
        plan.append((w, h, out))
    return plan


def run_export(src: Path, out_dir: Path, formats: List[str]) -> List[Path]:
    out_dir = Path(out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)
    outs = []
    for w, h, out in export_plan(src, out_dir, formats):
        conform_vertical(Path(src), out, target=f"{w}x{h}")
        outs.append(out)
    return outs
