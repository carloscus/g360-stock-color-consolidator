from __future__ import annotations

import flet as ft
from src.config.theme import Paleta
from src.core.models import ProductoConsolidado


class SearchOverlay:
    def __init__(self, page: ft.Page, p: Paleta, productos: list[ProductoConsolidado],
                 source1_raw: dict, on_select: callable):
        self.page = page
        self.p = p
        self.productos = productos
        self.source1_raw = source1_raw
        self._on_select = on_select
        self._container: ft.Container | None = None
        self._results_col: ft.Column | None = None
        self._selected_idx = 0
        self._query = ""
        self._results: list[ProductoConsolidado] = []

    def build(self) -> ft.Container:
        self._results_col = ft.Column(spacing=0, tight=True)
        self._container = ft.Container(
            content=self._results_col,
            visible=False,
            bgcolor=self.p.surface,
            border=ft.Border(
                top=ft.BorderSide(1, self.p.border),
                left=ft.BorderSide(1, self.p.border),
                right=ft.BorderSide(1, self.p.border),
                bottom=ft.BorderSide(1, self.p.border),
            ),
            border_radius=ft.BorderRadius(top_left=0, top_right=0, bottom_left=12, bottom_right=12),
            shadow=[ft.BoxShadow(blur_radius=12, spread_radius=-2, color="rgba(0,0,0,0.1)", offset=ft.Offset(0, 4))],
            padding=ft.Padding(left=0, right=0, top=4, bottom=4),
            width=420,
            animate_opacity=200,
        )
        return self._container

    def search(self, query: str):
        self._query = query.strip().lower()
        if not self._query or len(self._query) < 2:
            self.hide()
            return

        self._results = [
            p for p in self.productos
            if self._query in p.sku.lower()
            or self._query in p.descripcion.lower()
        ][:8]

        self._selected_idx = 0
        self._render()
        if self._container:
            self._container.visible = len(self._results) > 0
            self.page.update()

    def hide(self):
        if self._container:
            self._container.visible = False
            self.page.update()

    def on_key(self, e: ft.KeyboardEvent):
        if not self._container or not self._container.visible:
            return
        if e.key == "ArrowDown":
            e.control.update()
            if self._selected_idx < len(self._results) - 1:
                self._selected_idx += 1
                self._render()
                self.page.update()
        elif e.key == "ArrowUp":
            e.control.update()
            if self._selected_idx > 0:
                self._selected_idx -= 1
                self._render()
                self.page.update()
        elif e.key == "Enter":
            if 0 <= self._selected_idx < len(self._results):
                self._select(self._results[self._selected_idx])
        elif e.key == "Escape":
            self.hide()

    def _select(self, p: ProductoConsolidado):
        self.hide()
        if self._on_select:
            self._on_select(p.sku)

    def _wh_stock(self, code: str, sku: str) -> int:
        info = self.source1_raw.get(code, {}).get(sku)
        return (info.get("stock", 0) or 0) if info else 0

    def _wh_disp(self, code: str, sku: str) -> int:
        info = self.source1_raw.get(code, {}).get(sku)
        if not info:
            return 0
        return max(0, (info.get("stock", 0) or 0) - (info.get("predespacho", 0) or 0))

    def _render(self):
        if not self._results_col:
            return
        controls = []
        for i, p in enumerate(self._results):
            is_sel = i == self._selected_idx
            wh_count = sum(1 for code in self.source1_raw if self._wh_stock(code, p.sku) > 0)
            disp = p.disponible
            disp_color = self.p.success if disp > 0 else self.p.danger

            def on_hover(e, idx=i):
                card = e.control
                card.bgcolor = self.p.accent + "12" if e.data == "true" else (
                    self.p.surface_hover if idx == self._selected_idx else self.p.surface
                )
                self.page.update()

            def on_click(e, pp=p):
                self._select(pp)

            card = ft.Container(
                content=ft.Row([
                    ft.Container(
                        content=ft.Text(p.sku, size=13, weight=ft.FontWeight.BOLD, color=self.p.accent),
                        width=80,
                    ),
                    ft.Container(width=1),
                    ft.Column([
                        ft.Text(p.descripcion[:40] + ("..." if len(p.descripcion) > 40 else ""),
                                size=12, color=self.p.text, weight=ft.FontWeight.W_500),
                        ft.Row([
                            ft.Icon(ft.Icons.WAREHOUSE, size=10, color=self.p.text_secondary),
                            ft.Text(f"{wh_count} almacenes", size=10, color=self.p.text_secondary),
                            ft.Container(width=8),
                            ft.Icon(ft.Icons.INVENTORY_2_OUTLINED, size=10, color=disp_color),
                            ft.Text(f"{disp} disp.", size=10, color=disp_color, weight=ft.FontWeight.W_600),
                        ], spacing=0),
                    ], spacing=2, expand=True),
                    ft.Container(
                        content=ft.Text(str(disp), size=14, weight=ft.FontWeight.BOLD, color=disp_color),
                        width=40,
                        alignment=ft.alignment.center,
                    ),
                ], spacing=0, vertical_alignment=ft.CrossAxisAlignment.CENTER),
                padding=ft.Padding(left=12, right=12, top=8, bottom=8),
                border_radius=8,
                bgcolor=self.p.surface_hover if is_sel else self.p.surface,
                on_hover=on_hover,
                on_click=on_click,
                animate=ft.Animation(100, "ease"),
            )
            controls.append(card)

        if not controls:
            controls.append(
                ft.Container(
                    content=ft.Text("Sin resultados", size=12, color=self.p.text_secondary, italic=True),
                    padding=ft.Padding(left=16, right=16, top=12, bottom=12),
                    alignment=ft.alignment.center,
                )
            )
        else:
            controls.append(
                ft.Container(
                    content=ft.Text(f"{len(self._results)} resultados  ·  Enter para ver detalle  ·  Esc para cerrar",
                                    size=10, color=self.p.text_secondary),
                    padding=ft.Padding(left=16, right=16, top=6, bottom=6),
                    alignment=ft.alignment.center,
                )
            )

        self._results_col.controls = controls
