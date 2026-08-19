from __future__ import annotations
from dataclasses import dataclass
from enum import Enum

import flet as ft


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
    success_bg: str
    warning: str
    warning_bg: str
    danger: str
    danger_bg: str
    info: str
    info_bg: str
    violet: str
    violet_bg: str
    color_alerta: str
    glass_bg: str
    glass_border: str
    input_bg: str


LIGHT: Paleta = Paleta(
    bg="#f8fafc",
    surface="#ffffff",
    surface_hover="#f1f5f9",
    accent="#059669",
    text="#0f172a",
    text_secondary="#64748b",
    border="#e2e8f0",
    success="#059669",
    success_bg="#ecfdf5",
    warning="#d97706",
    warning_bg="#fffbeb",
    danger="#dc2626",
    danger_bg="#fef2f2",
    info="#0284c7",
    info_bg="#f0f9ff",
    violet="#7c3aed",
    violet_bg="#f5f3ff",
    color_alerta="#059669",
    glass_bg="#f8fafc",
    glass_border="#e2e8f0",
    input_bg="#f1f5f9",
)

DARK: Paleta = Paleta(
    bg="#090d16",
    surface="#111827",
    surface_hover="#1f2937",
    accent="#34d399",
    text="#f9fafb",
    text_secondary="#9ca3af",
    border="#1e293b",
    success="#34d399",
    success_bg="#064e3b",
    warning="#fbbf24",
    warning_bg="#78350f",
    danger="#f87171",
    danger_bg="#7f1d1d",
    info="#38bdf8",
    info_bg="#0c4a6e",
    violet="#a78bfa",
    violet_bg="#1e1b4b",
    color_alerta="#34d399",
    glass_bg="#111827",
    glass_border="#1e293b",
    input_bg="#1e293b",
)


# ── KPI configuration ───────────────────────────────────────────────

@dataclass
class KpiConf:
    key: str
    label: str
    icon: str
    color: str
    idle_bg: str
    hover_bg: str


KPI_LIGHT: list[KpiConf] = [
    KpiConf("total", "Total", ft.Icons.CATEGORY, "#64748B", "#F1F5F9", "#E2E8F0"),
    KpiConf("con_stock", "Con Stock", ft.Icons.CHECK_CIRCLE_OUTLINE, "#059669", "#ECFDF5", "#D1FAE5"),
    KpiConf("sin_stock", "Sin Stock", ft.Icons.DO_DISTURB_OUTLINED, "#DC2626", "#FEF2F2", "#FEE2E2"),
    KpiConf("traslados", "Traslados", ft.Icons.LOCAL_SHIPPING, "#7C3AED", "#F5F3FF", "#EDE9FE"),
]

KPI_DARK: list[KpiConf] = [
    KpiConf("total", "Total", ft.Icons.CATEGORY, "#94A3B8", "#1E293B", "#334155"),
    KpiConf("con_stock", "Con Stock", ft.Icons.CHECK_CIRCLE_OUTLINE, "#34D399", "#064E3B", "#065F46"),
    KpiConf("sin_stock", "Sin Stock", ft.Icons.DO_DISTURB_OUTLINED, "#F87171", "#450A0A", "#7F1D1D"),
    KpiConf("traslados", "Traslados", ft.Icons.LOCAL_SHIPPING, "#A78BFA", "#1E1B4B", "#312E81"),
]


def kpi_config(modo: Modo) -> list[KpiConf]:
    return KPI_DARK if modo == Modo.DARK else KPI_LIGHT
