from __future__ import annotations

import base64
from functools import lru_cache
from pathlib import Path

import cairosvg


@lru_cache(maxsize=4)
def _svg_to_b64(path: str) -> str:
    png_bytes = cairosvg.svg2png(url=path, output_width=105, output_height=35)
    return base64.b64encode(png_bytes).decode()


def logo_base64(modo: str) -> str:
    name = f"logo_g360_dark.svg" if modo == "dark" else f"logo_g360_light.svg"
    svg_path = str(Path(__file__).parent.parent.parent / "assets" / "images" / name)
    return _svg_to_b64(svg_path)
