from __future__ import annotations

import flet as ft
from src.config.theme import Paleta
from src.core.helpers import producto_tiene_traslado


class TrasladosModal:
    def __init__(self, page: ft.Page, p: Paleta, productos: list,
                 source1_raw: dict, warehouse_disp_fn, warehouse_stock_fn):
        self.page = page
        self.p = p
        self._wh_disp = warehouse_disp_fn
        self._wh_stock = warehouse_stock_fn

        self.traslados = [
            p for p in productos
            if producto_tiene_traslado(p, source1_raw, warehouse_disp_fn)
        ]

        wh_totals: dict[str, int] = {}
        for p in self.traslados:
            vd = self._wh_disp("VES", p.sku)
            for code in source1_raw:
                if code in ("VES", "121"):
                    continue
                d = self._wh_disp(code, p.sku)
                if d > vd:
                    wh_totals[code] = wh_totals.get(code, 0) + d
        self.wh_order = [c for c, _ in sorted(wh_totals.items(), key=lambda x: -x[1])]
        self.wh_w = min(50, max(38, 60 // max(len(self.wh_order), 1)))

        self.sort_col = [0]
        self.sort_asc = [True]
        self._content_col: ft.Column | None = None

    def show(self):
        if not self.traslados:
            return

        contenido = [self._build_header()] + [self._build_row(p) for p in self._sorted()]
        ancho = max(640, 70 + 3 * self.wh_w + len(self.wh_order) * (self.wh_w + 4) + 60)

        self._content_col = ft.Column(
            contenido, tight=True, spacing=2, width=min(ancho, 920),
            scroll=ft.ScrollMode.AUTO,
            height=min(500, 40 + len(self.traslados) * 40),
        )

        dlg = ft.AlertDialog(
            title=ft.Row([
                ft.Icon(ft.Icons.LOCAL_SHIPPING, size=20, color="#E65100"),
                ft.Text(f"  Pendientes de Transferencia ({len(self.traslados)})"),
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
        vd = self._wh_disp("VES", p.sku)
        if c == 0: return p.sku
        if c == 1: return p.descripcion
        if c == 2: return self._wh_stock("VES", p.sku)
        if c == 3: return vd
        if c == 4: return self._wh_disp("121", p.sku)
        idx = c - 5
        if idx < len(self.wh_order):
            d = self._wh_disp(self.wh_order[idx], p.sku)
            return d if d > vd else -1
        return p.sku

    def _sorted(self):
        return sorted(self.traslados, key=self._sort_key, reverse=not self.sort_asc[0])

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

    def _data_cell(self, text, w, color=None, bold=False):
        return ft.Text(
            str(text), size=12,
            weight=ft.FontWeight.BOLD if bold else ft.FontWeight.NORMAL,
            color=color or self.p.text_secondary,
            width=w, text_align=ft.TextAlign.RIGHT,
        )

    def _build_header(self):
        cells = [
            self._hdr_cell("SKU", 0, 70),
            self._hdr_cell("Artículo", 1),
            self._hdr_cell("St VES", 2, self.wh_w),
            self._hdr_cell("Dsp VES", 3, self.wh_w),
            self._hdr_cell("121", 4, self.wh_w),
        ]
        for i, code in enumerate(self.wh_order):
            cells.append(self._hdr_cell(code, 5 + i, self.wh_w))
        return ft.Container(
            content=ft.Row(cells, spacing=4),
            padding=ft.Padding(left=10, right=10, top=4, bottom=4),
        )

    def _build_row(self, p):
        vd = self._wh_disp("VES", p.sku)
        vs = self._wh_stock("VES", p.sku)
        d121 = self._wh_disp("121", p.sku)
        cells = [
                ft.Text(p.sku, size=12, weight=ft.FontWeight.BOLD, color=self.p.text, width=70),
                ft.Text(p.descripcion, size=12, color=self.p.text_secondary, expand=True, max_lines=2),
            self._data_cell(vs, self.wh_w),
            self._data_cell(vd, self.wh_w, self.p.danger, True),
            self._data_cell(d121, self.wh_w, self.p.accent if d121 > 0 else self.p.text_secondary, d121 > 0),
        ]
        for code in self.wh_order:
            d = self._wh_disp(code, p.sku)
            show = d if d > vd else 0
            cells.append(self._data_cell(show, self.wh_w, self.p.text if show > 0 else self.p.text_secondary))
        return ft.Container(
            content=ft.Row(cells, spacing=4, vertical_alignment=ft.CrossAxisAlignment.CENTER),
            padding=ft.Padding(left=10, right=10, top=6, bottom=6),
            border_radius=6,
            bgcolor=self.p.surface_hover,
        )

    def _on_sort(self, col):
        if self.sort_col[0] == col:
            self.sort_asc[0] = not self.sort_asc[0]
        else:
            self.sort_col[0] = col
            self.sort_asc[0] = True
        if self._content_col:
            self._content_col.controls = [self._build_header()] + [self._build_row(p) for p in self._sorted()]
            self.page.update()
