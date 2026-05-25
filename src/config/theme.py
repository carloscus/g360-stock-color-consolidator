from __future__ import annotations
from dataclasses import dataclass
from enum import Enum


class Modo(str, Enum):
    LIGHT = "light"
    DARK = "dark"


@dataclass
class Paleta:
    bg: str
    surface: str
    surface_hover: str
    accent: str
    text: str
    text_secondary: str
    border: str
    success: str
    warning: str
    danger: str
    info: str
    color_alerta: str
    glass_bg: str
    glass_border: str
    input_bg: str


LIGHT: Paleta = Paleta(
    bg="#f4f6f9",
    surface="#ffffff",
    surface_hover="#eef2f6",
    accent="#00d084",
    text="#0c1929",
    text_secondary="#475569",
    border="rgba(0,0,0,0.08)",
    success="#10b981",
    warning="#f59e0b",
    danger="#ef4444",
    info="#3b82f6",
    color_alerta="#8b5cf6",
    glass_bg="rgba(255,255,255,0.88)",
    glass_border="rgba(0,0,0,0.06)",
    input_bg="#ffffff",
)

DARK: Paleta = Paleta(
    bg="#0f172a",
    surface="#1e293b",
    surface_hover="#334155",
    accent="#00d084",
    text="#f1f5f9",
    text_secondary="#94a3b8",
    border="rgba(255,255,255,0.06)",
    success="#34d399",
    warning="#fbbf24",
    danger="#fb7185",
    info="#60a5fa",
    color_alerta="#a78bfa",
    glass_bg="rgba(30,41,59,0.85)",
    glass_border="rgba(255,255,255,0.12)",
    input_bg="#1e293b",
)
