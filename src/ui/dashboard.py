from __future__ import annotations

import flet as ft
from src.config.theme import LIGHT, DARK, Paleta, Modo
from src.core.models import ProductoConsolidado, AlertaSeveridad
from src.core.constants import COLOR_SIN_COLOR, WAREHOUSE_KPI
from src.ui.logo import logo_base64


class Dashboard:
    def __init__(self, page: ft.Page):
        self.page = page
        self.p: Paleta = LIGHT
        self.modo: Modo = Modo.LIGHT
        self.productos: list[ProductoConsolidado] = []
        self.productos_filtrados: list[ProductoConsolidado] = []
        self.search_query = ""
        self.current_page = 0
        self.page_size = 50
        self.filtro_alerta = False

        self.search_field: ft.TextField | None = None
        self.list_container: ft.Column | None = None
        self.kpi_row: ft.Row | None = None
        self.pag_row: ft.Row | None = None
        self.status_text: ft.Text | None = None
        self.expanded: set[str] = set()
        self.all_expanded = False
        self._on_expand_all_cb = None
        self._header_controls: list[ft.Control] = []
        self._header_container: ft.Container | None = None
        self._filtro_kpi = None
        self.overlay_loading: ft.Container | None = None

        self._on_sku_click = None
        self._on_theme_toggle = None
        self._on_download = None
        self._on_credentials = None
        self._on_load_s1 = None
        self._on_load_s2 = None
        self._on_load_s2_manual = None
        self.filtro_color = "con"
        self.sort_col = 0
        self.sort_asc = True
        self.source1_raw: dict[str, dict[str, dict]] = {}
        self.selected_warehouses: set[str] = set()
        self.warehouse_btns: list[ft.Container] = []
        self.warehouse_row: ft.Row | None = None
        self._loading_text = ft.Text("Procesando...", size=13, color="#ffffff")
        self._loading_progress = ft.ProgressBar(
            color="#ffffff",
            bgcolor="#ffffff33",
            width=300,
            value=0.0,
        )
        self._loading_bar = ft.Container(
            visible=False,
            content=ft.Column(
                [
                    ft.Row(
                        [
                            ft.Text("⏳", size=16),
                            self._loading_text,
                        ],
                        spacing=8,
                    ),
                    self._loading_progress,
                ],
                spacing=4,
            ),
            bgcolor="#1B3A5C",
            padding=ft.padding.symmetric(horizontal=16, vertical=10),
            border_radius=8,
            animate_opacity=200,
        )

    def set_on_sku_click(self, callback):
        self._on_sku_click = callback

    def set_on_theme_toggle(self, callback):
        self._on_theme_toggle = callback

    def set_on_download_report(self, callback):
        self._on_download = callback

    def set_on_credentials(self, callback):
        self._on_credentials = callback

    def set_on_load_source(self, s1_cb, s2_cb, s2_manual_cb=None):
        self._on_load_s1 = s1_cb
        self._on_load_s2 = s2_cb
        self._on_load_s2_manual = s2_manual_cb

    def set_on_expand_all(self, callback):
        self._on_expand_all_cb = callback

    def expand_all(self, expand: bool):
        self.all_expanded = expand
        if expand:
            for p in self.productos_filtrados:
                self.expanded.add(p.sku)
        else:
            self.expanded.clear()
        self._refresh_list()

    def set_source1_raw(self, data: dict[str, dict[str, dict]]):
        self.source1_raw = data
        self.selected_warehouses = set()
        self._build_warehouse_buttons()

    def set_theme(self, modo: Modo):
        self.modo = modo
        self.p = DARK if modo == Modo.DARK else LIGHT
        if self._loading_bar:
            self._loading_bar.bgcolor = self.p.accent

    def set_loading(self, active: bool, message: str = "", progress: float | None = None):
        self._loading_bar.visible = active
        if message:
            self._loading_text.value = message
        if progress is not None:
            self._loading_progress.value = max(0.0, min(1.0, progress))
        if self.overlay_loading is not None:
            self.overlay_loading.visible = active
            if active and self.overlay_loading not in self.page.overlay:
                self.page.overlay.append(self.overlay_loading)
            elif not active and self.overlay_loading in self.page.overlay:
                self.page.overlay.remove(self.overlay_loading)
        self.page.update()

    def _init_overlay_loading(self):
        """Crea overlay de carga centrado - no ocupa espacio en layout principal."""
        self.overlay_loading = ft.Container(
            content=ft.Column(
                [ft.Container(expand=True), self._loading_bar, ft.Container(expand=True)],
                horizontal_alignment=ft.CrossAxisAlignment.CENTER,
            ),
            bgcolor="rgba(0,0,0,0.6)",
            visible=False,
            expand=True,
            padding=20,
            alignment=ft.alignment.center,
        )

    # Column definitions shared by header & cards
    # ...

    def _col_labels(self) -> list[str]:
        labels = ["#", "SKU", "Artículo", "Stock", "Predesp", "Disponible"]
        if self.selected_warehouses:
            labels.append("Otros")
        labels.append("")
        return labels

    def _col_widths(self) -> list[int | None]:
        widths: list[int | None] = [36, 80, None, 60, 60, 70]
        if self.selected_warehouses:
            widths.append(80)
        widths.append(28)
        return widths

    def _col_sort_keys(self) -> list[int | None]:
        keys: list[int | None] = [None, 0, 1, 2, 3, 4]
        if self.selected_warehouses:
            keys.append(None)
        keys.append(5)
        return keys

    # ── Card cell helpers ────────────────────────────────────────────────

    def _card_text_cell(self, text: str, w: int | None, color: str, weight=ft.FontWeight.NORMAL):
        return ft.Container(
            content=ft.Text(text, size=12, color=color, weight=weight),
            padding=ft.padding.symmetric(horizontal=4),
            width=w if w is not None else None,
            expand=w is None,
        )

    def _card_warehouse_tags(self, p: ProductoConsolidado) -> ft.Container:
        if not self.selected_warehouses:
            return ft.Container(width=0, height=0)
        chips = []
        for code in sorted(self.selected_warehouses):
            val = self._warehouse_disp(code, p.sku)
            chips.append(
                ft.Container(
                    content=ft.Text(f"{code}:{val}", size=9, color=self.p.text_secondary),
                    bgcolor=self.p.surface_hover,
                    border_radius=3,
                    padding=ft.padding.only(left=4, right=4, top=1, bottom=1),
                )
            )
        return ft.Container(
            content=ft.Row(chips, spacing=3, wrap=True),
            padding=ft.padding.symmetric(horizontal=4),
            width=80,
        )

    def build(self) -> ft.Container:
        # Initialize overlay loading (centrado, no ocupa espacio en layout)
        self._init_overlay_loading()
        self.search_field = ft.TextField(
            hint_text="Buscar SKU o descripcion...",
            prefix_icon=ft.icons.SEARCH,
            border_radius=12,
            filled=True,
            bgcolor=self.p.input_bg,
            border=ft.border.all(1, self.p.border),
            text_size=14,
            on_change=self._on_search_change,
            expand=True,
        )

        self.status_text = ft.Text(
            "Descargue Source 1 y cargue Source 2 para comenzar",
            size=13,
            color=self.p.text_secondary,
        )

        return ft.Container(
            content=ft.Column(
                [
                    self._build_header(),
                    self._build_kpi_cards(),
                    self._build_filters(),
                    self._build_header_row(),
                    self._build_product_list(),
                    self._build_pagination(),
                ],
                spacing=12,
                scroll=ft.ScrollMode.AUTO,
            ),
            expand=True,
            padding=ft.padding.only(left=20, right=20, top=0, bottom=20),
        )

    def _build_header(self):
        return ft.Container(
            content=ft.Row(
                [
                    ft.Image(
                        src_base64=logo_base64("dark" if self.modo == Modo.DARK else "light"),
                        width=105, height=35, fit=ft.ImageFit.CONTAIN,
                    ),
                    ft.Text("Stock Consolidator", size=20, weight=ft.FontWeight.BOLD, color=self.p.text),
                    ft.Container(expand=True),
                    ft.ElevatedButton(
                        "S1 - Stock",
                        icon=ft.icons.CLOUD_DOWNLOAD_OUTLINED,
                        style=ft.ButtonStyle(
                            color={"": "#ffffff"},
                            bgcolor={"": "#1B3A5C", "hovered": "#244b75"},
                            shape=ft.RoundedRectangleBorder(radius=10),
                            padding=ft.padding.symmetric(horizontal=16, vertical=12),
                        ),
                        on_click=self._on_load_source1,
                    ),
                    ft.Container(width=6),
                    ft.ElevatedButton(
                        "S2 - Color",
                        icon=ft.icons.CLOUD_DOWNLOAD_OUTLINED,
                        style=ft.ButtonStyle(
                            color={"": "#ffffff"},
                            bgcolor={"": "#2C3E50", "hovered": "#34495e"},
                            shape=ft.RoundedRectangleBorder(radius=10),
                            padding=ft.padding.symmetric(horizontal=16, vertical=12),
                        ),
                        on_click=self._on_load_source2,
                    ),
                    ft.IconButton(
                        icon=ft.icons.FILE_OPEN,
                        icon_size=20,
                        icon_color=self.p.text_secondary,
                        on_click=self._on_load_source2_manual,
                        tooltip="Cargar Source 2 manual desde archivo .xls/.xlsx",
                    ),
                    ft.IconButton(
                        icon=ft.icons.LOCK_OUTLINE,
                        icon_size=20,
                        icon_color=self.p.text_secondary,
                        on_click=lambda _: self._on_credentials() if self._on_credentials else None,
                        tooltip="Configurar credenciales ERP",
                    ),
                    ft.IconButton(
                        icon=ft.icons.DOWNLOAD,
                        icon_size=20,
                        icon_color=self.p.text_secondary,
                        on_click=self._on_download_report,
                        tooltip="Descargar reporte XLSX",
                    ),
                    ft.IconButton(
                        icon=ft.icons.LIGHT_MODE if self.modo == Modo.DARK else ft.icons.DARK_MODE,
                        icon_size=20,
                        icon_color=self.p.text_secondary,
                        on_click=self._on_toggle_theme,
                    ),
                ],
                spacing=0,
                alignment=ft.MainAxisAlignment.START,
                vertical_alignment=ft.CrossAxisAlignment.CENTER,
            ),
            padding=ft.padding.symmetric(vertical=10),
        )

    def _build_kpi_cards(self):
        kpi_data = self._calcular_kpis()
        cards = ft.Row(
            spacing=12,
            controls=[
                self._kpi_card(kpi_data["con_stock"], "Con Stock", ft.icons.CHECK_CIRCLE_OUTLINE, self.p.success, "con_stock"),
                self._kpi_card(kpi_data["bajo_stock"], "Alertas", ft.icons.WARNING_AMBER_OUTLINED, self.p.warning, "bajo_stock"),
                self._kpi_card(kpi_data["sin_disponible"], "Disp 0", ft.icons.SCHEDULE, self.p.danger, "sin_disponible"),
                self._kpi_card(kpi_data["w121_total"], "Alm 121", ft.icons.WAREHOUSE, "#9C27B0", "w121"),
                self._kpi_card(kpi_data["total_skus"], "Total", ft.icons.CATEGORY, self.p.accent, "total"),
            ],
        )
        self.kpi_row = cards
        return cards

    def _kpi_card(self, valor: int, label: str, icon: str, color: str, kpi_key: str) -> ft.Container:
        is_active = self._filtro_kpi == kpi_key
        
        bg_color = self.p.accent + "22" if is_active else self.p.glass_bg
        
        return ft.Container(
            content=ft.Row(
                [
                    ft.Container(
                        content=ft.Icon(icon, size=22, color=color),
                        bgcolor=color + "22",
                        border_radius=12,
                        padding=12,
                    ),
                    ft.Column(
                        [
                            ft.Text(str(valor), size=24, weight=ft.FontWeight.BOLD, color=self.p.text),
                            ft.Text(label, size=13, color=self.p.text_secondary, weight=ft.FontWeight.W_500),
                        ],
                        spacing=2,
                        expand=True,
                    ),
                ],
                spacing=14,
                vertical_alignment=ft.CrossAxisAlignment.CENTER,
            ),
            bgcolor=bg_color,
            border_radius=14,
            border=ft.border.all(1.5, self.p.accent if is_active else self.p.glass_border),
            padding=ft.padding.all(16),
            expand=True,
            on_click=lambda _, k=kpi_key: self._on_kpi_click(k),
        )

    def _build_filters(self):
        self._color_filter_btns = None
        self.warehouse_row = ft.Row(spacing=4, vertical_alignment=ft.CrossAxisAlignment.CENTER)
        self._build_warehouse_buttons()

        self._toggle_expand_btn = ft.IconButton(
            icon=ft.icons.UNFOLD_MORE if not self.all_expanded else ft.icons.UNFOLD_LESS,
            icon_size=18,
            icon_color=self.p.accent,
            style=ft.ButtonStyle(
                bgcolor=self.p.surface_hover,
                shape=ft.RoundedRectangleBorder(radius=8),
            ),
            on_click=self._on_toggle_expand_all,
            tooltip="Expandir/Contraer todo",
        )

        return ft.Column(
            spacing=6,
            controls=[
                ft.Container(
                    content=ft.Row(
                        [
                            self.search_field,
                            ft.Container(width=10),
                            ft.Container(
                                content=self._toggle_expand_btn,
                                bgcolor=self.p.surface,
                                border_radius=8,
                                border=ft.border.all(1, self.p.glass_border),
                                padding=2,
                            ),
                            ft.Container(width=10),
                            ft.Container(
                                content=ft.Row(
                                    [
                                        ft.Checkbox(
                                            label="Solo alertas",
                                            label_style=ft.TextStyle(size=12, color=self.p.text_secondary),
                                            fill_color={ft.MaterialState.SELECTED: self.p.accent},
                                            on_change=self._on_filtro_alerta_change,
                                        ),
                                        ft.Container(width=6),
                                        self._build_color_buttons(),
                                    ],
                                    spacing=4,
                                    vertical_alignment=ft.CrossAxisAlignment.CENTER,
                                ),
                                bgcolor=self.p.glass_bg,
                                border_radius=8,
                                border=ft.border.all(1, self.p.glass_border),
                                padding=ft.padding.only(left=10, right=10),
                            ),
                        ],
                    ),
                ),
                ft.Container(
                    content=ft.Row(
                        [
                            ft.Icon(ft.icons.WAREHOUSE, size=14, color=self.p.text_secondary),
                            ft.Text("VES", size=11, weight=ft.FontWeight.BOLD, color=self.p.accent),
                            ft.Container(width=6),
                            self.warehouse_row,
                        ],
                        vertical_alignment=ft.CrossAxisAlignment.CENTER,
                    ),
                    padding=ft.padding.only(top=0),
                ),
            ],
        )

    def _build_warehouse_buttons(self):
        if not self.warehouse_row:
            return
        btns = []
        for code in sorted(self.source1_raw.keys()):
            if code == "VES":
                continue
            selected = code in self.selected_warehouses
            is_dark = self.modo == Modo.DARK
            btns.append(
                ft.Container(
                    content=ft.Text(code, size=11, weight=ft.FontWeight.BOLD,
                                   color="#ffffff" if (selected and is_dark) else (self.p.accent if selected else self.p.text)),
                    bgcolor=self.p.accent + "33" if (selected and is_dark) else (self.p.accent + "1e" if selected else "transparent"),
                    border=ft.border.all(1.5, self.p.accent if selected else self.p.border),
                    border_radius=14,
                    padding=ft.padding.only(left=10, right=10, top=4, bottom=4),
                    on_click=lambda _, c=code: self._toggle_warehouse(c),
                )
            )
        self.warehouse_row.controls = btns

    def _toggle_warehouse(self, code: str):
        if code in self.selected_warehouses:
            self.selected_warehouses.discard(code)
        else:
            self.selected_warehouses.add(code)
        self._build_warehouse_buttons()
        self._rebuild_header_row()

    def _build_color_buttons(self):
        opts = [("todos", "Todos"), ("con", "Con color"), ("sin", "S/C")]
        btns = []
        for val, label in opts:
            sel = val == self.filtro_color
            is_dark = self.modo == Modo.DARK
            btns.append(
                ft.Container(
                    content=ft.Text(label, size=11, weight=ft.FontWeight.BOLD,
                                   color="#ffffff" if (sel and is_dark) else (self.p.accent if sel else self.p.text)),
                    bgcolor=self.p.accent + "33" if (sel and is_dark) else (self.p.accent + "1e" if sel else "transparent"),
                    border=ft.border.all(1.5, self.p.accent if sel else self.p.border),
                    border_radius=14,
                    padding=ft.padding.only(left=10, right=10, top=4, bottom=4),
                    on_click=lambda _, v=val: self._on_color_filter_change(v),
                )
            )
        if self._color_filter_btns is None:
            self._color_filter_btns = ft.Row(btns, spacing=3)
        else:
            self._color_filter_btns.controls = btns
        return self._color_filter_btns

    def _on_color_filter_change(self, val: str):
        if val == self.filtro_color:
            return
        self.filtro_color = val
        self.current_page = 0
        self._build_color_buttons()
        self._refresh_list()

    def _warehouse_disp(self, code: str, sku: str) -> int:
        info = self.source1_raw.get(code, {}).get(sku)
        if not info:
            return 0
        return max(0, info.get("stock", 0) - info.get("predespacho", 0))

    # ── Sort ─────────────────────────────────────────────────────────────

    def _on_sort(self, e, idx: int):
        self.sort_asc = not self.sort_asc if self.sort_col == idx else True
        self.sort_col = idx
        self._refresh_list()

    def _sort_key(self, p: ProductoConsolidado):
        k = self.sort_col
        if k == 0:
            return p.sku
        if k == 1:
            return p.descripcion
        if k == 2:
            return p.stock_referencial
        if k == 3:
            return p.predespacho_total
        if k == 4:
            return p.disponible
        if k == 5:
            return max((a.severidad.value for a in p.alertas), default="") if p.alertas else ""
        return p.sku

    # ── Header row (aligned with card columns) ───────────────────────────

    def _build_header_row(self):
        container = ft.Container(
            content=self._make_header_row(),
            padding=ft.padding.symmetric(horizontal=12, vertical=8),
            bgcolor=self.p.surface_hover,
            border_radius=8,
            border=ft.border.all(1, self.p.border),
        )
        self._header_container = container
        return container

    def _make_header_row(self):
        labels = self._col_labels()
        widths = self._col_widths()
        keys = self._col_sort_keys()
        cells = []
        sort_arrow = " ▲" if self.sort_asc else " ▼"
        for i, (label, w, sk) in enumerate(zip(labels, widths, keys)):
            is_sort = sk is not None
            display_label = label
            if is_sort and self.sort_col == sk:
                display_label = (label or "") + sort_arrow
            txt = ft.Text(
                display_label,
                size=11, weight=ft.FontWeight.BOLD,
                color=self.p.accent if is_sort and self.sort_col == sk else self.p.text_secondary,
            )
            cell = ft.Container(content=txt, padding=ft.padding.symmetric(horizontal=4))
            if w is not None:
                cell.width = w
            else:
                cell.expand = True
            if is_sort:
                cell.on_click = lambda _, idx=sk: self._on_sort(_, idx)
            cells.append(cell)
        self._header_controls = cells
        return ft.Row(cells, spacing=4, vertical_alignment=ft.CrossAxisAlignment.CENTER)

    def _rebuild_header_row(self):
        if self._header_container:
            self._header_container.content = self._make_header_row()
        if self.list_container is not None:
            self._refresh_list()

    # ── Product list (accordion cards) ───────────────────────────────────

    def _build_product_list(self):
        self.list_container = ft.Column(spacing=4, scroll=ft.ScrollMode.AUTO)
        return ft.Container(
            content=self.list_container,
            border_radius=12,
            border=ft.border.all(1, self.p.glass_border),
            bgcolor=self.p.surface,
            padding=ft.padding.all(6),
        )

    def _build_pagination(self):
        self.pag_row = ft.Row(alignment=ft.MainAxisAlignment.END, spacing=4)
        return ft.Container(
            content=ft.Row(
                [
                    self.status_text,
                    ft.Container(expand=True),
                    self.pag_row,
                ],
                vertical_alignment=ft.CrossAxisAlignment.CENTER,
            ),
            padding=ft.padding.symmetric(vertical=6),
        )

    def _build_product_card(self, p: ProductoConsolidado, idx: int = 0) -> ft.Column:
        is_expanded = p.sku in self.expanded
        alerta = self._alerta_info(p)
        labels = self._col_labels()
        widths = self._col_widths()

        cells = []
        for i, label in enumerate(labels):
            w = widths[i]
            if i == 0:
                cell = self._card_text_cell(str(idx), w, self.p.text_secondary)
            elif i == 1:
                cell = self._card_text_cell(p.sku, w, self.p.text, ft.FontWeight.BOLD)
            elif i == 2:
                cell = self._card_text_cell(p.descripcion, w, self.p.text)
            elif i == 3:
                cell = self._card_text_cell(str(p.stock_referencial), w, self.p.text_secondary)
            elif i == 4:
                cell = self._card_text_cell(str(p.predespacho_total), w, self.p.text_secondary)
            elif i == 5:
                color = self.p.success if p.disponible > 0 else self.p.danger
                cell = self._card_text_cell(str(p.disponible), w, color, ft.FontWeight.BOLD)
            elif label == "Otros":
                cell = self._card_warehouse_tags(p)
            else:
                cell = ft.Container(width=28, height=0)
            cells.append(cell)
        cells[-1] = ft.Container(
            content=ft.Icon(alerta["icon"], size=16, color=alerta["color"]),
            tooltip=alerta["msg"],
            width=28,
        )

        chevron = ft.Icon(
            ft.icons.EXPAND_MORE if is_expanded else ft.icons.CHEVRON_RIGHT,
            size=14,
            color=self.p.text_secondary,
        )

        row_content = ft.Row(
            [chevron] + cells,
            spacing=3,
            vertical_alignment=ft.CrossAxisAlignment.CENTER,
        )

        card = ft.Container(
            content=row_content,
            padding=ft.padding.symmetric(horizontal=12, vertical=10),
            border_radius=8,
            border=ft.border.all(1, self.p.border),
            bgcolor=self.p.surface_hover if is_expanded else self.p.surface,
            shadow=ft.BoxShadow(
                spread_radius=0,
                blur_radius=6,
                color="rgba(15,23,42,0.03)" if self.modo == Modo.LIGHT else "rgba(0,0,0,0.25)",
                offset=ft.Offset(0, 2),
            ),
            on_click=lambda _, sku=p.sku: self._toggle_expand(sku),
            on_hover=lambda e: self._on_card_hover(e, p.sku),
        )

        items = [card]
        if is_expanded and p.colores:
            sub_rows = []
            for c in sorted(p.colores, key=lambda x: x.total, reverse=True):
                for d in c.disenos:
                    sub_rows.append((d.nombre, c.nombre, d.cantidad))
            if sub_rows:
                sub_controls = [
                    ft.Container(
                        content=ft.Row([
                            ft.Text("Modelo", size=10, weight=ft.FontWeight.BOLD, color=self.p.text_secondary, expand=3),
                            ft.Text("Color", size=10, weight=ft.FontWeight.BOLD, color=self.p.text_secondary, expand=2),
                            ft.Text("Cant", size=10, weight=ft.FontWeight.BOLD, color=self.p.text_secondary, width=50, text_align=ft.TextAlign.RIGHT),
                        ], spacing=3),
                        padding=ft.padding.only(left=28, right=4, top=2, bottom=1),
                    )
                ]
                for modelo, color, cant in sub_rows:
                    sub_controls.append(
                        ft.Container(
                            content=ft.Row([
                                ft.Text(modelo, size=12, color=self.p.text, expand=3),
                                ft.Text(color, size=12, color=self.p.text_secondary, expand=2),
                                ft.Text(str(cant), size=12, weight=ft.FontWeight.BOLD, color=self.p.text,
                                        width=50, text_align=ft.TextAlign.RIGHT),
                            ], spacing=3),
                            padding=ft.padding.only(left=28, right=4, top=2, bottom=2),
                        )
                    )
                items.append(ft.Column(sub_controls, spacing=0))

        return ft.Column(items, spacing=0)

    def _on_card_hover(self, e, sku: str):
        is_expanded = sku in self.expanded
        if e.data == "true":
            e.control.bgcolor = self.p.surface_hover
            e.control.shadow = ft.BoxShadow(
                spread_radius=0,
                blur_radius=10,
                color="rgba(15,23,42,0.08)" if self.modo == Modo.LIGHT else "rgba(0,0,0,0.4)",
                offset=ft.Offset(0, 4),
            )
        else:
            e.control.bgcolor = self.p.surface_hover if is_expanded else self.p.surface
            e.control.shadow = ft.BoxShadow(
                spread_radius=0,
                blur_radius=6,
                color="rgba(15,23,42,0.03)" if self.modo == Modo.LIGHT else "rgba(0,0,0,0.25)",
                offset=ft.Offset(0, 2),
            )
        self.page.update()

    def _toggle_expand(self, sku: str):
        if sku in self.expanded:
            self.expanded.discard(sku)
        else:
            self.expanded.add(sku)
        self._refresh_list()

    def _alerta_info(self, p: ProductoConsolidado) -> dict:
        if not p.alertas:
            return {"color": self.p.success, "icon": ft.icons.CHECK_CIRCLE_OUTLINE, "msg": "OK"}

        # Ordenar alertas por severidad (ALTA > MEDIA > BAJA > INFO) y mostrar la más grave
        severidad_orden = {AlertaSeveridad.ALTA: 0, AlertaSeveridad.MEDIA: 1, AlertaSeveridad.BAJA: 2, AlertaSeveridad.INFO: 3}
        peor_alerta = min(p.alertas, key=lambda a: severidad_orden.get(a.severidad, 99))

        sev = peor_alerta.severidad
        if sev == AlertaSeveridad.ALTA:
            return {"color": self.p.danger, "icon": ft.icons.ERROR_OUTLINE, "msg": peor_alerta.mensaje}
        if sev == AlertaSeveridad.MEDIA:
            return {"color": self.p.warning, "icon": ft.icons.WARNING_AMBER_OUTLINED, "msg": peor_alerta.mensaje}
        if sev == AlertaSeveridad.BAJA:
            return {"color": self.p.info, "icon": ft.icons.INFO_OUTLINE, "msg": peor_alerta.mensaje}
        return {"color": self.p.info, "icon": ft.icons.INFO_OUTLINE, "msg": peor_alerta.mensaje}

    # ── Refresh ──────────────────────────────────────────────────────────

    def _refresh_list(self):
        self._apply_filters()

        sorted_products = sorted(
            self.productos_filtrados,
            key=self._sort_key,
            reverse=not self.sort_asc,
        )

        start = self.current_page * self.page_size
        end = start + self.page_size
        page_items = sorted_products[start:end]

        self.list_container.controls = [
            self._build_product_card(p, start + i + 1)
            for i, p in enumerate(page_items)
        ]

        total = len(self.productos_filtrados)
        self.status_text.value = (
            f"{total} productos | {start + 1}-{min(end, total)}"
            if total > 0 else "Sin resultados"
        )

        total_pages = max(1, (total + self.page_size - 1) // self.page_size)
        pag_btns = []
        for i in range(total_pages):
            pag_btns.append(
                ft.Container(
                    content=ft.Text(str(i + 1), size=12, weight=ft.FontWeight.BOLD,
                                   color=self.p.accent if i == self.current_page else self.p.text_secondary),
                    width=26, height=26,
                    border_radius=5,
                    bgcolor=self.p.accent + "18" if i == self.current_page else "transparent",
                    alignment=ft.alignment.center,
                    on_click=lambda _, pg=i: self._go_to_page(pg),
                )
            )
        self.pag_row.controls = pag_btns

        self._rebuild_kpis()
        self.page.update()

    def _go_to_page(self, page: int):
        self.current_page = page
        self._refresh_list()

    def set_productos(self, productos: list[ProductoConsolidado]):
        self.productos = productos
        self.expanded = set()
        self._apply_filters()
        self._refresh_list()

    def _apply_filters(self):
        filtered = self.productos
        if self.search_query:
            filtered = [
                p for p in filtered
                if self.search_query in p.sku.lower()
                or self.search_query in p.descripcion.lower()
            ]
        if self.filtro_alerta:
            filtered = [p for p in filtered if p.alertas]
        if self.filtro_color == "con":
            filtered = [p for p in filtered if any(c.nombre != COLOR_SIN_COLOR for c in p.colores)]
        elif self.filtro_color == "sin":
            filtered = [p for p in filtered if all(c.nombre == COLOR_SIN_COLOR for c in p.colores)]
        if self._filtro_kpi == "con_stock":
            filtered = [p for p in filtered if p.disponible > 0]
        elif self._filtro_kpi == "bajo_stock":
            filtered = [p for p in filtered if any(
                a.severidad in (AlertaSeveridad.ALTA, AlertaSeveridad.MEDIA) for a in p.alertas
            )]
        elif self._filtro_kpi == "sin_disponible":
            filtered = [p for p in filtered if p.disponible == 0 and p.stock_referencial > 0]
        elif self._filtro_kpi == "w121":
            filtered = [p for p in filtered if self._warehouse_disp(WAREHOUSE_KPI, p.sku) > 0]
        self.productos_filtrados = filtered

    def _on_search_change(self, e):
        self.search_query = e.control.value.strip().lower()
        self.current_page = 0
        self._refresh_list()

    def _on_filtro_alerta_change(self, e):
        self.filtro_alerta = e.control.value
        self.current_page = 0
        self._refresh_list()

    def _on_kpi_click(self, kpi_key: str):
        if self._filtro_kpi == kpi_key:
            self._filtro_kpi = None
        else:
            self._filtro_kpi = kpi_key
        self.current_page = 0
        self._refresh_list()

    def _on_toggle_expand_all(self, e):
        self.all_expanded = not self.all_expanded
        if self.all_expanded:
            for p in self.productos_filtrados:
                self.expanded.add(p.sku)
        else:
            self.expanded.clear()
        if hasattr(self, '_toggle_expand_btn') and self._toggle_expand_btn:
            self._toggle_expand_btn.icon = ft.icons.UNFOLD_LESS if self.all_expanded else ft.icons.UNFOLD_MORE
            self._toggle_expand_btn.update()
        self._refresh_list()

    def _on_toggle_theme(self, e):
        if self._on_theme_toggle:
            self._on_theme_toggle()

    def _on_load_source1(self, e):
        if self._on_load_s1:
            self._on_load_s1()

    def _on_load_source2(self, e):
        if self._on_load_s2:
            self._on_load_s2()

    def _on_load_source2_manual(self, e):
        if self._on_load_s2_manual:
            self._on_load_s2_manual()

    def _on_download_report(self, e):
        if self._on_download:
            self._on_download()

    def _calcular_kpis(self) -> dict:
        total = len(self.productos_filtrados)
        con_stock = sum(1 for p in self.productos_filtrados if p.disponible > 0)
        bajo = sum(1 for p in self.productos_filtrados if p.alertas and any(
            a.severidad in (AlertaSeveridad.ALTA, AlertaSeveridad.MEDIA) for a in p.alertas
        ))
        sin_disp = sum(1 for p in self.productos_filtrados if p.disponible == 0 and p.stock_referencial > 0)
        w121 = sum(1 for p in self.productos_filtrados 
                   if self._warehouse_disp(WAREHOUSE_KPI, p.sku) > 0)
        return {
            "total_skus": total,
            "con_stock": con_stock,
            "bajo_stock": bajo,
            "sin_disponible": sin_disp,
            "w121_total": w121,
        }

    def _rebuild_kpis(self):
        if not self.kpi_row or len(self.kpi_row.controls) != 5:
            return
        kpi = self._calcular_kpis()
        keys = ["con_stock", "bajo_stock", "sin_disponible", "w121", "total"]
        values = [kpi["con_stock"], kpi["bajo_stock"], kpi["sin_disponible"], kpi["w121_total"], kpi["total_skus"]]
        for i, (val, key) in enumerate(zip(values, keys)):
            card = self.kpi_row.controls[i]
            row = card.content
            col = row.controls[1]
            col.controls[0].value = str(val)
            is_active = self._filtro_kpi == key
            card.bgcolor = self.p.accent + "22" if is_active else self.p.glass_bg
            card.border = ft.border.all(1.5, self.p.accent if is_active else self.p.glass_border)
        self.page.update()


