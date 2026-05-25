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
    bg="#f8fafc",
    surface="#ffffff",
    surface_hover="#f1f5f9",
    accent="#4f46e5",
    text="#0f172a",
    text_secondary="#64748b",
    border="#e2e8f0",
    success="#10b981",
    warning="#f59e0b",
    danger="#ef4444",
    info="#0ea5e9",
    color_alerta="#8b5cf6",
    glass_bg="#f8fafc",
    glass_border="#e2e8f0",
    input_bg="#f1f5f9",
)

DARK: Paleta = Paleta(
    bg="#090d16",
    surface="#111827",
    surface_hover="#1f2937",
    accent="#818cf8",
    text="#f9fafb",
    text_secondary="#9ca3af",
    border="#1e293b",
    success="#34d399",
    warning="#fbbf24",
    danger="#f87171",
    info="#38bdf8",
    color_alerta="#a78bfa",
    glass_bg="#111827",
    glass_border="#1e293b",
    input_bg="#1e293b",
)
