from __future__ import annotations

import flet as ft
from src.config.theme import Paleta
from src.core.models import ProductoConsolidado


class SinStockModal:
    def __init__(self, page: ft.Page, p: Paleta, productos: list[ProductoConsolidado]):
        self.page = page
        self.p = p
        self.sin_stock = [p for p in productos if p.disponible == 0]
        self.sort_col = [0]
        self.sort_asc = [True]
        self._content_col: ft.Column | None = None
        self._dlg: ft.AlertDialog | None = None
        self._overlay: ft.Container | None = None
        self._rows: list[ft.Container] = []

    def show(self):
        if not self.sin_stock:
            return

        self._rows = [self._row(p) for p in self._sorted()]

        header = self._build_header()
        self._content_col = ft.Column(
            [header] + self._rows,
            tight=True, spacing=0, width=540,
            scroll=ft.ScrollMode.AUTO,
            height=min(520, 60 + len(self.sin_stock) * 42),
        )

        self._dlg = ft.AlertDialog(
            modal=False,
            title=ft.Container(
                content=ft.Row([
                    ft.Container(
                        content=ft.Icon(ft.Icons.DO_DISTURB_OUTLINED, size=20, color="#ffffff"),
                        bgcolor=self.p.danger,
                        border_radius=10,
                        padding=10,
                    ),
                    ft.Container(width=10),
                    ft.Column([
                        ft.Text("Sin Stock Disponible", size=16, weight=ft.FontWeight.W_700, color=self.p.text),
                        ft.Text(f"{len(self.sin_stock)} productos sin stock", size=11, color=self.p.text_secondary),
                    ], spacing=0),
                ], vertical_alignment=ft.CrossAxisAlignment.CENTER),
                padding=ft.Padding(left=4, right=4, top=4, bottom=4),
            ),
            content=self._content_col,
            actions=[
                ft.TextButton(
                    "Cerrar",
                    on_click=self._close,
                    style=ft.ButtonStyle(color=self.p.text_secondary),
                    tooltip="Cerrar ventana",
                ),
            ],
            actions_alignment=ft.MainAxisAlignment.END,
            bgcolor=self.p.surface,
            shape=ft.RoundedRectangleBorder(radius=16),
        )

        self._overlay = ft.Container(
            content=self._dlg,
            bgcolor="rgba(0,0,0,0.4)",
            expand=True,
            on_click=self._close,
            on_hover=lambda e: None,
        )

        self.page._active_dialog = self._dlg
        self.page.overlay.append(self._overlay)
        self._dlg.open = True
        self.page.update()

    def _close(self, e=None):
        if self._dlg:
            self._dlg.open = False
        if self._overlay and self._overlay in self.page.overlay:
            self.page.overlay.remove(self._overlay)
        self.page.update()

    def _sort_key(self, p):
        c = self.sort_col[0]
        if c == 0: return p.sku
        if c == 1: return p.descripcion
        if c == 2: return p.stock_referencial
        if c == 3: return p.predespacho_total
        if c == 4: return p.disponible
        return p.sku

    def _sorted(self):
        return sorted(self.sin_stock, key=self._sort_key, reverse=not self.sort_asc[0])

    def _hdr_cell(self, text, col, w=None):
        is_sort = self.sort_col[0] == col
        arrow = " ▲" if is_sort and self.sort_asc[0] else " ▼" if is_sort else ""
        txt = ft.Text(
            text + arrow, size=12, weight=ft.FontWeight.W_600,
            color=self.p.accent if is_sort else self.p.text_secondary,
        )
        c = ft.Container(
            txt,
            on_click=lambda _, x=col: self._on_sort(x),
            tooltip=f"Ordenar por {text}",
            padding=ft.Padding(left=4, right=4, top=4, bottom=4),
        )
        if w is not None: c.width = w
        else: c.expand = True
        return c

    def _row(self, p):
        def on_hover(e):
            row = e.control
            row.bgcolor = self.p.accent + "15" if e.data == "true" else self.p.surface_hover
            self.page.update()

        return ft.Container(
            content=ft.Row(
                [
                    ft.Text(p.sku, size=12, weight=ft.FontWeight.BOLD, color=self.p.accent, width=80),
                    ft.Text(p.descripcion, size=12, color=self.p.text, expand=True, max_lines=2),
                    ft.Text(str(p.stock_referencial), size=12, color=self.p.text_secondary, width=55, text_align=ft.TextAlign.RIGHT),
                    ft.Text(str(p.predespacho_total), size=12, color=self.p.warning if p.predespacho_total > 0 else self.p.text_secondary, width=55, text_align=ft.TextAlign.RIGHT),
                    ft.Container(
                        content=ft.Text("0", size=12, weight=ft.FontWeight.BOLD, color="#ffffff"),
                        bgcolor=self.p.danger,
                        border_radius=6,
                        padding=ft.Padding(left=8, right=8, top=2, bottom=2),
                        width=55,
                        alignment=ft.alignment.center,
                    ),
                ],
                spacing=4,
                vertical_alignment=ft.CrossAxisAlignment.CENTER,
            ),
            padding=ft.Padding(left=10, right=10, top=6, bottom=6),
            border_radius=8,
            bgcolor=self.p.surface_hover,
            border=ft.Border(bottom=ft.BorderSide(1, self.p.border)),
            on_hover=on_hover,
            animate=ft.Animation(150, "ease"),
        )

    def _build_header(self):
        return ft.Container(
            content=ft.Row(
                [
                    self._hdr_cell("SKU", 0, 80),
                    self._hdr_cell("Artículo", 1),
                    self._hdr_cell("Stock", 2, 55),
                    self._hdr_cell("Predesp", 3, 55),
                    self._hdr_cell("Disp", 4, 55),
                ],
                spacing=4,
            ),
            padding=ft.Padding(left=10, right=10, top=6, bottom=6),
            bgcolor=self.p.surface_hover,
            border_radius=ft.BorderRadius(top_left=10, top_right=10, bottom_left=0, bottom_right=0),
            border=ft.Border(bottom=ft.BorderSide(1, self.p.border)),
        )

    def _on_sort(self, col):
        if self.sort_col[0] == col:
            self.sort_asc[0] = not self.sort_asc[0]
        else:
            self.sort_col[0] = col
            self.sort_asc[0] = True
        self._rows = [self._row(p) for p in self._sorted()]
        if self._content_col:
            self._content_col.controls = [self._build_header()] + self._rows
            self.page.update()
