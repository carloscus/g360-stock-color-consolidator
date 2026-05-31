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

    def show(self):
        if not self.sin_stock:
            return

        self._content_col = ft.Column(
            [self._build_header()] + [self._row(p) for p in self._sorted()],
            tight=True, spacing=2, width=520,
            scroll=ft.ScrollMode.AUTO,
            height=min(500, 40 + len(self.sin_stock) * 40),
        )

        dlg = ft.AlertDialog(
            title=ft.Row([
                ft.Icon(ft.Icons.DO_DISTURB_OUTLINED, size=20, color=self.p.danger),
                ft.Text(f"  Sin Stock Disponible ({len(self.sin_stock)})"),
            ], spacing=0),
            content=self._content_col,
            actions=[ft.TextButton("Cerrar", on_click=self._close, tooltip="Cerrar ventana")],
        )
        self.page.show_dialog(dlg)
        self.page.update()

    def _close(self, e):
        self.page.pop_dialog()
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
                text + arrow, size=13, weight=ft.FontWeight.BOLD,
            color=self.p.accent if is_sort else self.p.text_secondary,
        )
        c = ft.Container(txt, on_click=lambda _, x=col: self._on_sort(x), tooltip=f"Ordenar por {text}")
        if w is not None: c.width = w
        else: c.expand = True
        return c

    def _row(self, p):
        return ft.Container(
            content=ft.Row(
                [
                    ft.Text(p.sku, size=12, weight=ft.FontWeight.BOLD, color=self.p.text, width=80),
                    ft.Text(p.descripcion, size=12, color=self.p.text_secondary, expand=True, max_lines=2),
                    ft.Text(str(p.stock_referencial), size=12, color=self.p.text_secondary, width=50, text_align=ft.TextAlign.RIGHT),
                    ft.Text(str(p.predespacho_total), size=12, color=self.p.warning if p.predespacho_total > 0 else self.p.text_secondary, width=50, text_align=ft.TextAlign.RIGHT),
                    ft.Text("0", size=12, weight=ft.FontWeight.BOLD, color=self.p.danger, width=50, text_align=ft.TextAlign.RIGHT),
                ],
                spacing=6,
                vertical_alignment=ft.CrossAxisAlignment.CENTER,
            ),
            padding=ft.Padding(left=12, right=12, top=6, bottom=6),
            border_radius=6,
            bgcolor=self.p.surface_hover,
        )

    def _build_header(self):
        return ft.Container(
            content=ft.Row(
                [
                    self._hdr_cell("SKU", 0, 80),
                    self._hdr_cell("Artículo", 1),
                    self._hdr_cell("Stock", 2, 50),
                    self._hdr_cell("Predesp", 3, 50),
                    self._hdr_cell("Disp", 4, 50),
                ],
                spacing=6,
            ),
            padding=ft.Padding(left=12, right=12, top=4, bottom=4),
        )

    def _on_sort(self, col):
        if self.sort_col[0] == col:
            self.sort_asc[0] = not self.sort_asc[0]
        else:
            self.sort_col[0] = col
            self.sort_asc[0] = True
        if self._content_col:
            self._content_col.controls = [self._build_header()] + [self._row(p) for p in self._sorted()]
            self.page.update()
