from __future__ import annotations

import flet as ft
from src.core.models import ProductoConsolidado, ColorStock
from src.config.theme import Paleta


class SkuDetailModal:
    def __init__(self, page: ft.Page, producto: ProductoConsolidado, paleta: Paleta):
        self.page = page
        self.producto = producto
        self.p = paleta
        self.dialog: ft.AlertDialog | None = None
        self._overlay: ft.Container | None = None

    def show(self):
        content = ft.Container(
            content=ft.Column(
                [
                    self._header_info(),
                    self._stock_row(),
                    ft.Divider(height=1, color=self.p.border),
                    ft.Text("Desglose por Color", size=15, weight=ft.FontWeight.W_600, color=self.p.text),
                    *self._color_tree(),
                ],
                spacing=12,
                scroll=ft.ScrollMode.AUTO,
            ),
            width=560,
            height=460,
            padding=ft.Padding(left=20, right=20, top=20, bottom=20),
        )

        self.dialog = ft.AlertDialog(
            modal=False,
            content=content,
            actions=[
                ft.TextButton(
                    "Cerrar",
                    on_click=self._close,
                    style=ft.ButtonStyle(color=self.p.text_secondary),
                    tooltip="Cerrar detalle del producto",
                ),
            ],
            actions_alignment=ft.MainAxisAlignment.END,
            bgcolor=self.p.surface,
            shape=ft.RoundedRectangleBorder(radius=16),
        )

        self._overlay = ft.Container(
            content=self.dialog,
            bgcolor="rgba(0,0,0,0.4)",
            expand=True,
            on_click=self._close,
            on_hover=lambda e: None,
        )

        self.page._active_dialog = self.dialog
        self.page.overlay.append(self._overlay)
        self.dialog.open = True
        self.page.update()

    def _close(self, e=None):
        if self.dialog:
            self.dialog.open = False
        if hasattr(self, '_overlay') and self._overlay and self._overlay in self.page.overlay:
            self.page.overlay.remove(self._overlay)
        self.page.update()

    def _header_info(self):
        return ft.Row(
            [
                ft.Container(
                    content=ft.Text(self.producto.sku, size=20, weight=ft.FontWeight.BOLD, color=self.p.accent),
                ),
                ft.Column(
                    [
                        ft.Text(
                            self.producto.descripcion or "Sin descripcion",
                            size=14,
                            color=self.p.text,
                        ),
                    ],
                    spacing=2,
                    expand=True,
                ),
            ],
            spacing=12,
            vertical_alignment=ft.CrossAxisAlignment.CENTER,
        )

    def _stock_row(self):
        def _chip(label: str, value: int, color: str, is_special=False, special_border_color=None):
            bg = color + "12" if is_special else self.p.glass_bg
            border_col = special_border_color if is_special else self.p.glass_border
            return ft.Container(
                content=ft.Column(
                    [
                        ft.Text(str(value), size=18, weight=ft.FontWeight.BOLD, color=color),
                        ft.Text(label, size=11, color=self.p.text_secondary),
                    ],
                    horizontal_alignment=ft.CrossAxisAlignment.CENTER,
                    spacing=0,
                ),
                bgcolor=bg,
                border_radius=10,
                border=ft.Border(top=ft.BorderSide(1, border_col), left=ft.BorderSide(1, border_col), right=ft.BorderSide(1, border_col), bottom=ft.BorderSide(1, border_col)),
                padding=ft.Padding(left=20, right=20, top=12, bottom=12),
            )

        disp_color = self.p.success if self.producto.disponible > 0 else self.p.danger
        return ft.Row(
            [
                _chip("Stock Ref", self.producto.stock_referencial, self.p.info),
                _chip("Predespacho", self.producto.predespacho_total, self.p.warning),
                _chip("Disponible", self.producto.disponible, disp_color, is_special=True, special_border_color=disp_color),
            ],
            spacing=8,
        )

    def _color_tree(self) -> list[ft.Control]:
        if not self.producto.colores:
            return [ft.Text("Sin datos de colores", color=self.p.text_secondary, italic=True)]

        sections: list[ft.Control] = []
        max_total = max(c.total for c in self.producto.colores) if self.producto.colores else 1

        for color in self.producto.colores:
            sections.append(self._color_section(color, max_total))

        return sections

    def _color_section(self, color: ColorStock, max_total: int) -> ft.Container:
        bar_width = max(4, int((color.total / max_total) * 100)) if max_total > 0 else 4
        bar_color = self._get_color_hex(color.nombre)

        disenos_rows: list[ft.Control] = []
        for d in color.disenos:
            d_bar = max(4, int((d.cantidad / max_total) * 100))
            disenos_rows.append(
                ft.Container(
                    content=ft.Row(
                        [
                            ft.Text(d.nombre, size=12, color=self.p.text_secondary, width=100),
                            ft.Container(
                                content=ft.Container(
                                    bgcolor=bar_color + "80",
                                    border_radius=4,
                                    height=14,
                                    width=max(20, d_bar * 1.5),
                                ),
                                bgcolor=self.p.surface_hover,
                                border_radius=4,
                                expand=True,
                            ),
                            ft.Text(str(d.cantidad), size=12, weight=ft.FontWeight.W_600, color=self.p.text, width=40, text_align=ft.TextAlign.END),
                        ],
                        spacing=8,
                        vertical_alignment=ft.CrossAxisAlignment.CENTER,
                    ),
                    padding=ft.Padding(left=24, right=0, top=2, bottom=2),
                )
            )

        return ft.Container(
            content=ft.Column(
                [
                    ft.Container(
                        content=ft.Row(
                            [
                                ft.Icon(ft.Icons.CIRCLE, size=14, color=bar_color),
                                ft.Text(color.nombre, size=14, weight=ft.FontWeight.W_600, color=self.p.text),
                                ft.Container(expand=True),
                                ft.Text(str(color.total), size=14, weight=ft.FontWeight.BOLD, color=self.p.text),
                            ],
                            spacing=6,
                            vertical_alignment=ft.CrossAxisAlignment.CENTER,
                        ),
                        padding=ft.Padding(left=0, right=0, top=6, bottom=6),
                    ),
                    ft.Container(
                        content=ft.Container(
                            bgcolor=bar_color,
                            border_radius=6,
                            height=8,
                            animate=ft.Animation(300, ft.AnimationCurve.EASE_OUT),
                        ),
                        bgcolor=self.p.surface_hover,
                        border_radius=6,
                    ),
                    *disenos_rows,
                ],
                spacing=2,
            ),
            bgcolor=self.p.glass_bg,
            border_radius=10,
            border=ft.Border(top=ft.BorderSide(1, self.p.glass_border), left=ft.BorderSide(1, self.p.glass_border), right=ft.BorderSide(1, self.p.glass_border), bottom=ft.BorderSide(1, self.p.glass_border)),
            padding=ft.Padding(left=12, right=12, top=12, bottom=12),
        )

    def _get_color_hex(self, nombre: str) -> str:
        base = {
            "rojo": "#ef4444", "roj": "#ef4444",
            "verde": "#22c55e", "ver": "#22c55e",
            "azul": "#3b82f6", "azu": "#3b82f6",
            "amarillo": "#eab308", "ama": "#eab308",
            "naranja": "#f97316",
            "violeta": "#8b5cf6",
            "rosa": "#ec4899", "ros": "#ec4899",
            "negro": "#1e293b", "neg": "#1e293b",
            "blanco": "#f8fafc", "bla": "#94a3b8",
            "marron": "#92400e",
            "gris": "#94a3b8",
            "celeste": "#38bdf8", "cel": "#38bdf8",
            "lila": "#a78bfa", "lil": "#a78bfa",
            "turquesa": "#14b8a6",
            "fucsia": "#d946ef", "fuc": "#d946ef",
            "magenta": "#ec4899", "mag": "#ec4899",
            "dorado": "#f59e0b", "dor": "#f59e0b",
            "plateado": "#94a3b8", "plata": "#94a3b8",
            "morado": "#8b5cf6",
            "coral": "#fb7185",
            "salmon": "#fb923c",
        }

        lower = nombre.lower().replace(" ", "").replace("/", "-").replace("_", "-")
        # Try exact match first
        if lower in base:
            return base[lower]
        # Try extracting known color codes from compound names (BLA-CEL-AZU, etc)
        parts = lower.replace("-", " ").split()
        for part in parts:
            if part in base:
                return base[part]
        return self.p.accent