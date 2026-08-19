from __future__ import annotations

import flet as ft
from src.config.theme import LIGHT, DARK, Paleta, Modo, kpi_config
from src.core.helpers import producto_tiene_traslado
from src.core.models import ProductoConsolidado, AlertaSeveridad, Alerta, AlertaTipo
from src.core.constants import COLOR_SIN_COLOR
from src.ui.logo import logo_base64
from src.ui.search_overlay import SearchOverlay
from src.ui.modals.sin_stock_modal import SinStockModal
from src.ui.modals.traslados_modal import TrasladosModal

try:
    from g360_flet.g360_signature import G360Signature
except ImportError:
    G360Signature = None


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
        self._search_overlay: SearchOverlay | None = None
        self._alerta_checkbox: ft.Checkbox | None = None
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
        self._active_warehouse: str | None = None
        self._warehouse_sidebar: ft.Container | None = None
        self._loading_text = ft.Text("Procesando...", size=13, color="#ffffff")
        self._loading_progress = ft.ProgressBar(
            color="#ffffff",
            bgcolor="#ffffff33",
            width=300,
            value=0.0,
        )
        self._loading_spinner = ft.Column(
            [
                ft.Row(
                    [
                        ft.ProgressRing(
                            width=48, height=48,
                            stroke_width=3,
                            color=self.p.accent,
                        ),
                        ft.Container(width=16),
                        self._loading_text,
                    ],
                    spacing=0,
                    vertical_alignment=ft.CrossAxisAlignment.CENTER,
                ),
                ft.Container(height=12),
                self._loading_progress,
            ],
            spacing=0,
            horizontal_alignment=ft.CrossAxisAlignment.CENTER,
        )
        self._loading_bar = ft.Container(
            visible=False,
            content=self._loading_spinner,
            bgcolor=self.p.accent,
            padding=ft.Padding(left=24, right=24, top=16, bottom=16),
            border_radius=12,
            animate_opacity=200,
            shadow=[
                ft.BoxShadow(blur_radius=12, spread_radius=-2, color="rgba(0,0,0,0.15)", offset=ft.Offset(0, 4)),
            ],
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
        self._active_warehouse = None
        if self._search_overlay:
            self._search_overlay.source1_raw = data
        if self._warehouse_sidebar is not None:
            self._refresh_sidebar()

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
        wh = self._active_warehouse
        if wh:
            return ["#", "SKU", "Artículo", f"Stock {wh}", f"Predesp {wh}", f"Disp {wh}", ""]
        return ["#", "SKU", "Artículo", "Stock", "Predesp", "Disp", ""]

    def _col_widths(self) -> list[int | None]:
        return [36, 80, None, 60, 60, 70, 34]

    def _col_sort_keys(self) -> list[int | None]:
        return [None, 0, 1, 2, 3, 4, 5]

    # ── Card cell helpers ────────────────────────────────────────────────

    def _card_text_cell(self, text: str, w: int | None, color: str, weight=ft.FontWeight.NORMAL):
        return ft.Container(
            content=ft.Text(text, size=12, color=color, weight=weight),
            padding=ft.Padding(left=4, right=4, top=0, bottom=0),
            width=w if w is not None else None,
            expand=w is None,
        )



    def build(self) -> ft.Container:
        # Initialize overlay loading (centrado, no ocupa espacio en layout)
        self._init_overlay_loading()
        self._search_overlay = SearchOverlay(
            self.page, self.p, self.productos, self.source1_raw,
            on_select=self._on_sku_click,
        )
        self.search_field = ft.TextField(
            hint_text="Buscar SKU o descripcion...",
            prefix_icon=ft.Icons.SEARCH,
            border_radius=12,
            filled=True,
            bgcolor=self.p.input_bg,
            border=ft.Border(top=ft.BorderSide(1, self.p.border), left=ft.BorderSide(1, self.p.border), right=ft.BorderSide(1, self.p.border), bottom=ft.BorderSide(1, self.p.border)),
            text_size=14,
            on_change=self._on_search_change,
            on_focus=self._on_search_focus,
            expand=True,
        )

        self.status_text = ft.Text(
            "Descargue Source 1 y cargue Source 2 para comenzar",
            size=13,
            color=self.p.text_secondary,
        )

        main_content = ft.Column(
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
            expand=True,
        )

        self._warehouse_sidebar = self._build_warehouse_sidebar()
        return ft.Container(
            content=ft.Row(
                [
                    self._warehouse_sidebar,
                    ft.Container(
                        content=main_content,
                        expand=True,
                        padding=ft.Padding(left=20, right=20, top=0, bottom=20),
                    ),
                ],
                spacing=0,
                vertical_alignment=ft.CrossAxisAlignment.START,
                expand=True,
            ),
            expand=True,
        )

    def _build_header(self):
        brand = ft.Row(
            [
                ft.Image(
                    src=logo_base64("dark" if self.modo == Modo.DARK else "light"),
                    width=105, height=35, fit=ft.ImageFit.CONTAIN,
                ),
                ft.Container(width=12),
                ft.Column(
                    [
                        ft.Text("Stock Consolidator", size=18, weight=ft.FontWeight.BOLD, color=self.p.text),
                        ft.Container(height=2),
                        ft.Text("CIPSA · ERP Stock Colors", size=11, color=self.p.text_secondary),
                    ],
                    spacing=0,
                ),
                ft.Container(width=16),
            ],
            spacing=0,
            vertical_alignment=ft.CrossAxisAlignment.CENTER,
        )

        actions = ft.Row(
            [
                ft.Button(
                    "S1 - Stock",
                    icon=ft.Icons.CLOUD_DOWNLOAD_OUTLINED,
                    style=ft.ButtonStyle(
                        color={"": "#ffffff"},
                        bgcolor={"": "#059669", "hovered": "#047857"},
                        shape=ft.RoundedRectangleBorder(radius=10),
                        padding=ft.Padding(left=16, right=16, top=12, bottom=12),
                    ),
                    on_click=self._on_load_source1,
                    tooltip="Descargar Source 1 (stock) desde el ERP",
                ),
                ft.Container(width=6),
                ft.Button(
                    "S2 - Color",
                    icon=ft.Icons.CLOUD_DOWNLOAD_OUTLINED,
                    style=ft.ButtonStyle(
                        color={"": "#ffffff"},
                        bgcolor={"": "#059669", "hovered": "#047857"},
                        shape=ft.RoundedRectangleBorder(radius=10),
                        padding=ft.Padding(left=16, right=16, top=12, bottom=12),
                    ),
                    on_click=self._on_load_source2,
                    tooltip="Descargar Source 2 (colores) desde el ERP",
                ),
                ft.Container(width=6),
                ft.IconButton(
                    icon=ft.Icons.FILE_OPEN,
                    icon_size=20,
                    icon_color=self.p.text_secondary,
                    on_click=self._on_load_source2_manual,
                    tooltip="Cargar Source 2 manual desde archivo .xls/.xlsx",
                ),
                ft.Container(width=2),
                ft.IconButton(
                    icon=ft.Icons.LOCK_OUTLINE,
                    icon_size=20,
                    icon_color=self.p.text_secondary,
                    on_click=lambda _: self._on_credentials() if self._on_credentials else None,
                    tooltip="Configurar credenciales ERP",
                ),
                ft.Container(width=2),
                ft.IconButton(
                    icon=ft.Icons.DOWNLOAD,
                    icon_size=20,
                    icon_color=self.p.text_secondary,
                    on_click=self._on_download_report,
                    tooltip="Descargar reporte XLSX",
                ),
                ft.Container(width=2),
                ft.IconButton(
                    icon=ft.Icons.LIGHT_MODE if self.modo == Modo.DARK else ft.Icons.DARK_MODE,
                    icon_size=20,
                    icon_color=self.p.text_secondary,
                    on_click=self._on_toggle_theme,
                    tooltip="Cambiar tema claro/oscuro",
                ),
            ],
            spacing=0,
            vertical_alignment=ft.CrossAxisAlignment.CENTER,
        )

        return ft.Container(
            content=ft.Column(
                [brand, actions],
                spacing=8,
            ),
            padding=ft.Padding(left=4, right=4, top=12, bottom=12),
            border=ft.Border(bottom=ft.BorderSide(1, self.p.border)),
        )

    def _build_kpi_cards(self):
        kpi_data = self._calcular_kpis()
        cfgs = kpi_config(self.modo)
        cards = ft.Row(
            spacing=12,
            controls=[
                self._kpi_card(
                    kpi_data[cfg.key] if cfg.key != "total" else kpi_data["total_skus"],
                    cfg.label, cfg.icon, cfg.color, cfg.key,
                    compact=(cfg.key in ("sin_stock", "traslados")),
                    idle_bg=cfg.idle_bg, hover_bg=cfg.hover_bg,
                )
                for cfg in cfgs
            ],
        )
        self.kpi_row = cards
        return cards

    def _kpi_card(self, valor: int, label: str, icon: str, color: str, kpi_key: str, compact: bool = False, idle_bg: str | None = None, hover_bg: str | None = None) -> ft.Container:
        c = color
        is_dark = self.modo == Modo.DARK
        base_idle = idle_bg or (c + "12" if is_dark else c + "06")
        base_hover = hover_bg or (c + "22" if is_dark else c + "14")
        active_a = (c + "50" if is_dark else c + "30")
        border_off = c + "30" if is_dark else c + "18"
        border_hov = c + "70" if is_dark else c + "50"

        def _on_hover(e):
            card = e.control
            is_active = self._filtro_kpi == kpi_key
            if e.data == "true":
                card.bgcolor = (c + "65" if is_dark else c + "45") if is_active else base_hover
                card.border = ft.Border(top=ft.BorderSide(2, c if is_active else border_hov), left=ft.BorderSide(2, c if is_active else border_hov), right=ft.BorderSide(2, c if is_active else border_hov), bottom=ft.BorderSide(2, c if is_active else border_hov))
            else:
                card.bgcolor = active_a if is_active else base_idle
                card.border = ft.Border(top=ft.BorderSide(1.5, c if is_active else border_off), left=ft.BorderSide(1.5, c if is_active else border_off), right=ft.BorderSide(1.5, c if is_active else border_off), bottom=ft.BorderSide(1.5, c if is_active else border_off))
            self.page.update()

        icon_pad = 8 if compact else 12
        icon_size = 18 if compact else 22
        val_size = 20 if compact else 24
        pad = ft.Padding(left=12, right=12, top=10, bottom=10) if compact else ft.Padding(left=16, right=16, top=16, bottom=16)

        kpi_tooltips = {
            "total": "Mostrar todos los productos",
            "con_stock": "Filtrar productos con stock disponible",
            "sin_stock": "Ver productos sin stock disponible",
            "traslados": "Ver productos pendientes de traslado",
        }

        return ft.Container(
            content=ft.Row(
                [
                    ft.Container(
                        content=ft.Icon(icon, size=icon_size, color=c),
                        bgcolor=(c + "20" if is_dark else c + "14"),
                        border_radius=12,
                        padding=icon_pad,
                    ),
                    ft.Column(
                        [
                            ft.Text(str(valor), size=val_size, weight=ft.FontWeight.BOLD, color=self.p.text),
                            ft.Text(label, size=13, color=self.p.text_secondary, weight=ft.FontWeight.W_500),
                        ],
                        spacing=2,
                        expand=True,
                    ),
                ],
                spacing=14,
                vertical_alignment=ft.CrossAxisAlignment.CENTER,
            ),
            bgcolor=base_idle,
            border_radius=14,
            border=ft.Border(top=ft.BorderSide(1.5, border_off), left=ft.BorderSide(1.5, border_off), right=ft.BorderSide(1.5, border_off), bottom=ft.BorderSide(1.5, border_off)),
            shadow=[
                ft.BoxShadow(blur_radius=8, spread_radius=-2, color=c + "0C", offset=ft.Offset(0, 2)),
                ft.BoxShadow(blur_radius=16, spread_radius=-4, color=c + "08", offset=ft.Offset(0, 6)),
            ],
            padding=pad,
            expand=True,
            animate=ft.Animation(200, "ease"),
            on_click=lambda _, k=kpi_key: self._on_kpi_click(k),
            on_hover=_on_hover,
            tooltip=kpi_tooltips.get(kpi_key, ""),
        )

    def _build_filters(self):
        self._alerta_checkbox = ft.Checkbox(
            label="Solo alertas",
            label_style=ft.TextStyle(size=12, color=self.p.text_secondary),
            fill_color={ft.ControlState.SELECTED: self.p.accent},
            on_change=self._on_filtro_alerta_change,
            tooltip="Mostrar solo productos con alertas",
        )
        self._toggle_expand_btn = ft.IconButton(
            icon=ft.Icons.UNFOLD_MORE if not self.all_expanded else ft.Icons.UNFOLD_LESS,
            icon_size=18,
            icon_color=self.p.accent,
            style=ft.ButtonStyle(
                bgcolor=self.p.surface_hover,
                shape=ft.RoundedRectangleBorder(radius=8),
            ),
            on_click=self._on_toggle_expand_all,
            tooltip="Expandir/Contraer todo",
        )

        search_overlay = self._search_overlay.build()
        search_area = ft.Stack(
            [
                self.search_field,
                ft.Container(
                    content=search_overlay,
                    top=44,
                    left=0,
                ),
            ],
            expand=True,
        )

        return ft.Column(
            [
                ft.Row(
                    [
                        search_area,
                        ft.Container(width=10),
                        ft.Container(
                            content=self._toggle_expand_btn,
                            bgcolor=self.p.surface,
                            border_radius=8,
                            border=ft.Border(top=ft.BorderSide(1, self.p.glass_border), left=ft.BorderSide(1, self.p.glass_border), right=ft.BorderSide(1, self.p.glass_border), bottom=ft.BorderSide(1, self.p.glass_border)),
                            padding=2,
                        ),
                        ft.Container(width=10),
                        self._alerta_checkbox,
                    ],
                ),
            ],
            spacing=0,
        )

    def _make_sidebar_controls(self) -> list[ft.Control]:
        wh_data: list[tuple[str, int]] = []
        for code in self.source1_raw:
            count = sum(
                1 for p in self.productos
                if self._warehouse_stock(code, p.sku) > 0
            ) if self.productos else 0
            if count == 0:
                continue
            wh_data.append((code, count))
        wh_data.sort(key=lambda x: (0 if x[0] == "VES" else 1, x[0]))
        btns = []
        for code, count in wh_data:
            is_active = self._active_warehouse == code
            is_ves = code == "VES"

            btn = ft.Container(
                content=ft.Column(
                    [
                        ft.Row(
                            [
                                ft.Icon(
                                    ft.Icons.STAR if is_ves else ft.Icons.WAREHOUSE,
                                    size=12,
                                    color=self.p.accent if is_active else self.p.text_secondary,
                                ),
                                ft.Text(
                                    code,
                                    size=13,
                                    weight=ft.FontWeight.BOLD,
                                    color=self.p.accent if is_active else self.p.text,
                                ),
                            ],
                            spacing=4,
                            vertical_alignment=ft.CrossAxisAlignment.CENTER,
                        ),
                        ft.Text(
                            f"{count} productos" if count else "sin stock",
                            size=11,
                            color=self.p.accent if count else self.p.text_secondary,
                        ),
                    ],
                    spacing=2,
                ),
                bgcolor=self.p.accent + "18" if is_active else self.p.surface_hover,
                border_radius=10,
                border=ft.Border(top=ft.BorderSide(1.5, self.p.accent if is_active else self.p.border), left=ft.BorderSide(1.5, self.p.accent if is_active else self.p.border), right=ft.BorderSide(1.5, self.p.accent if is_active else self.p.border), bottom=ft.BorderSide(1.5, self.p.accent if is_active else self.p.border)),
                padding=ft.Padding(left=12, right=12, top=10, bottom=10),
                on_click=lambda _, c=code: self._on_warehouse_sidebar_click(c),
                animate=ft.Animation(150, "ease"),
                tooltip=f"Filtrar productos del almacén {code}",
            )
            btns.append(btn)

        header = ft.Container(
            content=ft.Row(
                [
                    ft.Icon(ft.Icons.WAREHOUSE, size=16, color=self.p.accent),
                    ft.Text("Almacenes", size=14, weight=ft.FontWeight.BOLD, color=self.p.text),
                ],
                spacing=6,
                vertical_alignment=ft.CrossAxisAlignment.CENTER,
            ),
            padding=ft.Padding(left=8, right=8, top=16, bottom=8),
        )

        # ── Color filter section ──
        color_header = ft.Container(
            content=ft.Text("Color", size=11, weight=ft.FontWeight.BOLD, color=self.p.text_secondary),
            padding=ft.Padding(left=8, right=8, top=12, bottom=4),
        )
        color_btns = self._color_filter_sidebar_btns()

        # ── Clear filter ──
        clear_btn = ft.Container(
            content=ft.Row(
                [
                    ft.Icon(ft.Icons.CLEAR_ALL, size=14, color=self.p.accent),
                    ft.Text("Limpiar filtros", size=13, color=self.p.accent, weight=ft.FontWeight.W_600),
                ],
                spacing=4,
                vertical_alignment=ft.CrossAxisAlignment.CENTER,
            ),
            padding=ft.Padding(left=10, right=10, top=6, bottom=6),
            border_radius=8,
            border=ft.Border(top=ft.BorderSide(1, self.p.accent + "40"), left=ft.BorderSide(1, self.p.accent + "40"), right=ft.BorderSide(1, self.p.accent + "40"), bottom=ft.BorderSide(1, self.p.accent + "40")),
            on_click=lambda _: self._on_clear_filter(),
            tooltip="Limpiar todos los filtros activos",
        )

        g360_footer = ft.Container(
            content=G360Signature(mode="powered", version="2.0") if G360Signature
            else ft.Text("Powered by G360", size=10, color=self.p.text_secondary, weight=ft.FontWeight.W_500),
            alignment=ft.Alignment(0, 0),
            padding=ft.Padding(left=8, right=8, top=8, bottom=4),
        )

        return [header] + btns + [color_header] + color_btns + [clear_btn] + [ft.Container(expand=True), g360_footer]

    def _color_filter_sidebar_btns(self) -> list[ft.Control]:
        is_dark = self.modo == Modo.DARK
        opts = [
            ("todos", "Todos", ft.Icons.FILTER_ALT, self.p.accent),
            ("con", "Con color", ft.Icons.PALETTE, self.p.success),
            ("sin", "S/C", ft.Icons.INVERT_COLORS_OFF, self.p.warning),
        ]
        color_tooltips = {"todos": "Mostrar todos los productos", "con": "Solo productos con color asignado", "sin": "Solo productos sin color"}
        btns = []
        for val, label, icon, color in opts:
            sel = val == self.filtro_color
            txt_color = "#ffffff" if (sel and is_dark) else (color if sel else self.p.text)
            bg = color + "33" if (sel and is_dark) else (color + "1e" if sel else self.p.surface_hover)
            btns.append(
                ft.Container(
                    content=ft.Row(
                        [
                            ft.Icon(icon, size=12, color=txt_color),
                            ft.Text(
                                label, size=11, weight=ft.FontWeight.BOLD,
                                color=txt_color,
                            ),
                        ],
                        spacing=4,
                        vertical_alignment=ft.CrossAxisAlignment.CENTER,
                    ),
                    bgcolor=bg,
                    border_radius=8,
                    border=ft.Border(top=ft.BorderSide(1, color if sel else self.p.border), left=ft.BorderSide(1, color if sel else self.p.border), right=ft.BorderSide(1, color if sel else self.p.border), bottom=ft.BorderSide(1, color if sel else self.p.border)),
                    padding=ft.Padding(left=10, right=10, top=6, bottom=6),
                    on_click=lambda _, v=val: self._on_color_filter_change(v),
                    tooltip=color_tooltips.get(val, ""),
                )
            )
        return btns

    def _build_warehouse_sidebar(self) -> ft.Container:
        return ft.Container(
            content=ft.Column(
                self._make_sidebar_controls(),
                spacing=4,
                scroll=ft.ScrollMode.AUTO,
                expand=True,
            ),
            width=170,
            bgcolor=self.p.surface,
            border_radius=12,
            border=ft.Border(top=ft.BorderSide(1, self.p.glass_border), left=ft.BorderSide(1, self.p.glass_border), right=ft.BorderSide(1, self.p.glass_border), bottom=ft.BorderSide(1, self.p.glass_border)),
            padding=ft.Padding(left=4, right=4, top=0, bottom=8),
        )

    def _on_warehouse_sidebar_click(self, code: str | None):
        if self._active_warehouse == code:
            return
        self._active_warehouse = code
        self.current_page = 0
        self._refresh_sidebar()
        self._refresh_list()

    def _refresh_sidebar(self):
        if self._warehouse_sidebar is not None:
            col = self._warehouse_sidebar.content
            if isinstance(col, ft.Column):
                col.controls = self._make_sidebar_controls()

    def _on_color_filter_change(self, val: str):
        if val == self.filtro_color:
            return
        self.filtro_color = val
        self.current_page = 0
        self._refresh_sidebar()
        self._refresh_list()

    def _warehouse_stock(self, code: str, sku: str) -> int:
        info = self.source1_raw.get(code, {}).get(sku)
        if not info:
            return 0
        return info.get("stock", 0) or 0

    def _warehouse_predesp(self, code: str, sku: str) -> int:
        info = self.source1_raw.get(code, {}).get(sku)
        if not info:
            return 0
        return info.get("predespacho", 0) or 0

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
        wh = self._active_warehouse
        if k == 0:
            return p.sku
        if k == 1:
            return p.descripcion
        if k == 2:
            return self._warehouse_stock(wh, p.sku) if wh else p.stock_referencial
        if k == 3:
            return self._warehouse_predesp(wh, p.sku) if wh else p.predespacho_total
        if k == 4:
            return self._warehouse_disp(wh, p.sku) if wh else p.disponible
        if k == 5:
            return max((a.severidad.value for a in p.alertas), default="") if p.alertas else ""
        return p.sku

    # ── Header row (aligned with card columns) ───────────────────────────

    def _build_header_row(self):
        container = ft.Container(
            content=self._make_header_row(),
            padding=ft.Padding(left=12, right=12, top=8, bottom=8),
            bgcolor=self.p.surface_hover,
            border_radius=8,
            border=ft.Border(top=ft.BorderSide(1, self.p.border), left=ft.BorderSide(1, self.p.border), right=ft.BorderSide(1, self.p.border), bottom=ft.BorderSide(1, self.p.border)),
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
                size=13, weight=ft.FontWeight.BOLD,
                color=self.p.accent if is_sort and self.sort_col == sk else self.p.text_secondary,
            )
            cell = ft.Container(content=txt, padding=ft.Padding(left=4, right=4, top=0, bottom=0))
            if w is not None:
                cell.width = w
            else:
                cell.expand = True
            if is_sort:
                cell.on_click = lambda _, idx=sk: self._on_sort(_, idx)
                cell.tooltip = f"Ordenar por {label or 'columna'}"
            cells.append(cell)
        self._header_controls = cells
        return ft.Row(
            [ft.Container(width=17)] + cells,
            spacing=3, vertical_alignment=ft.CrossAxisAlignment.CENTER,
        )

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
            border=ft.Border(top=ft.BorderSide(1, self.p.glass_border), left=ft.BorderSide(1, self.p.glass_border), right=ft.BorderSide(1, self.p.glass_border), bottom=ft.BorderSide(1, self.p.glass_border)),
            bgcolor=self.p.surface,
            padding=ft.Padding(left=6, right=6, top=6, bottom=6),
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
            padding=ft.Padding(left=0, right=0, top=6, bottom=6),
        )

    def _build_product_card(self, p: ProductoConsolidado, idx: int = 0) -> ft.Column:
        is_expanded = p.sku in self.expanded
        alerta = self._alerta_info(p)
        labels = self._col_labels()
        widths = self._col_widths()

        cells = []
        wh = self._active_warehouse
        for i, label in enumerate(labels):
            w = widths[i]
            if i == 0:
                cell = self._card_text_cell(str(idx), w, self.p.text_secondary)
            elif i == 1:
                cell = self._card_text_cell(p.sku, w, self.p.text, ft.FontWeight.BOLD)
            elif i == 2:
                cell = self._card_text_cell(p.descripcion, w, self.p.text)
            elif i == 3:
                val = self._warehouse_stock(wh, p.sku) if wh else p.stock_referencial
                cell = self._card_text_cell(str(val), w, self.p.text_secondary)
            elif i == 4:
                val = self._warehouse_predesp(wh, p.sku) if wh else p.predespacho_total
                cell = self._card_text_cell(str(val), w, self.p.text_secondary)
            elif i == 5:
                val = self._warehouse_disp(wh, p.sku) if wh else p.disponible
                color = self.p.success if val > 0 else self.p.danger
                cell = self._card_text_cell(str(val), w, color, ft.FontWeight.BOLD)
            else:
                cell = ft.Container(width=34, height=0)
            cells.append(cell)
        cells[-1] = ft.Container(
            content=ft.Row(
                [
                    ft.Icon(alerta["icon"], size=16, color=alerta["color"]),
                    ft.Container(width=2),
                    ft.IconButton(
                        icon=ft.Icons.ACCOUNT_TREE_OUTLINED,
                        icon_size=12,
                        icon_color=self.p.text_secondary,
                        padding=0,
                        width=14,
                        height=14,
                        on_click=lambda _, sku=p.sku: self._show_warehouse_detail(sku),
                        tooltip="Ver detalle por almacén",
                    ),
                ],
                spacing=0,
                alignment=ft.MainAxisAlignment.START,
            ),
            width=34,
        )

        chevron = ft.Icon(
            ft.Icons.EXPAND_MORE if is_expanded else ft.Icons.CHEVRON_RIGHT,
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
            padding=ft.Padding(left=12, right=12, top=10, bottom=10),
            border_radius=8,
            border=ft.Border(top=ft.BorderSide(1, self.p.border), left=ft.BorderSide(1, self.p.border), right=ft.BorderSide(1, self.p.border), bottom=ft.BorderSide(1, self.p.border)),
            bgcolor=self.p.surface_hover if is_expanded else self.p.surface,
            shadow=ft.BoxShadow(
                spread_radius=0,
                blur_radius=6,
                color="rgba(15,23,42,0.03)" if self.modo == Modo.LIGHT else "rgba(0,0,0,0.25)",
                offset=ft.Offset(0, 2),
            ),
            on_click=lambda _, sku=p.sku: self._toggle_expand(sku),
            on_hover=lambda e: self._on_card_hover(e, p.sku),
            tooltip="Expandir para ver colores y modelos",
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
                            ft.Text("Modelo", size=11, weight=ft.FontWeight.BOLD, color=self.p.text_secondary, expand=3),
                            ft.Text("Color", size=11, weight=ft.FontWeight.BOLD, color=self.p.text_secondary, expand=2),
                            ft.Text("Cant", size=11, weight=ft.FontWeight.BOLD, color=self.p.text_secondary, width=50, text_align=ft.TextAlign.RIGHT),
                        ], spacing=3),
                        padding=ft.Padding(left=28, right=4, top=2, bottom=1),
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
                            padding=ft.Padding(left=28, right=4, top=2, bottom=2),
                        )
                    )
                items.append(ft.Column(sub_controls, spacing=0))

        return ft.Column(items, spacing=0)

    def _show_warehouse_detail(self, sku: str):
        rows = []
        for code in sorted(self.source1_raw.keys()):
            info = self.source1_raw.get(code, {}).get(sku)
            if not info:
                continue
            stock = info.get("stock", 0)
            predesp = info.get("predespacho", 0)
            disp = max(0, stock - predesp)
            color = self.p.success if disp > 0 else self.p.danger
            rows.append(
                ft.Container(
                    content=ft.Row(
                        [
                            ft.Icon(
                                ft.Icons.STAR if code == "VES" else ft.Icons.WAREHOUSE,
                                size=14,
                                color=self.p.accent if code == "VES" else self.p.text_secondary,
                            ),
                            ft.Text(code, size=13, weight=ft.FontWeight.BOLD, color=self.p.text, width=50),
                            ft.Text(str(stock), size=12, color=self.p.text_secondary, width=50, text_align=ft.TextAlign.RIGHT),
                            ft.Text(str(predesp), size=12, color=self.p.warning if predesp > 0 else self.p.text_secondary, width=50, text_align=ft.TextAlign.RIGHT),
                            ft.Text(str(disp), size=12, weight=ft.FontWeight.BOLD, color=color, width=50, text_align=ft.TextAlign.RIGHT),
                        ],
                        spacing=8,
                        vertical_alignment=ft.CrossAxisAlignment.CENTER,
                    ),
                    padding=ft.Padding(left=12, right=12, top=8, bottom=8),
                    border_radius=8,
                    bgcolor=self.p.surface_hover if code != "VES" else self.p.accent + "10",
                )
            )

        if not rows:
            return

        header = ft.Container(
            content=ft.Row(
                [
                    ft.Text("Almacén", size=11, weight=ft.FontWeight.BOLD, color=self.p.text_secondary, width=50),
                    ft.Text("Stock", size=11, weight=ft.FontWeight.BOLD, color=self.p.text_secondary, width=50, text_align=ft.TextAlign.RIGHT),
                    ft.Text("Predesp", size=11, weight=ft.FontWeight.BOLD, color=self.p.text_secondary, width=50, text_align=ft.TextAlign.RIGHT),
                    ft.Text("Disp", size=11, weight=ft.FontWeight.BOLD, color=self.p.text_secondary, width=50, text_align=ft.TextAlign.RIGHT),
                ],
                spacing=8,
            ),
            padding=ft.Padding(left=12, right=12, top=4, bottom=4),
        )

        dlg = ft.AlertDialog(
            modal=False,
            title=ft.Text(f"Detalle por almacén — {sku}"),
            content=ft.Column([header] + rows, tight=True, spacing=2, width=340),
            actions=[ft.TextButton("Cerrar", on_click=lambda _: self._close_warehouse_dlg(dlg), tooltip="Cerrar detalle de almacén")],
            bgcolor=self.p.surface,
            shape=ft.RoundedRectangleBorder(radius=16),
        )
        overlay = ft.Container(
            content=dlg,
            bgcolor="rgba(0,0,0,0.4)",
            expand=True,
            on_click=lambda _: self._close_warehouse_dlg(dlg),
            on_hover=lambda e: None,
        )
        self.page._active_dialog = dlg
        self.page.overlay.append(overlay)
        dlg.open = True
        self.page.update()

    def _close_warehouse_dlg(self, dlg):
        dlg.open = False
        for ctrl in list(self.page.overlay):
            if isinstance(ctrl, ft.Container) and ctrl.content == dlg:
                self.page.overlay.remove(ctrl)
                break
        self.page.update()

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

    def _show_sin_stock_modal(self):
        modal = SinStockModal(self.page, self.p, self.productos)
        if not modal.sin_stock:
            self._show_toast("No hay productos con stock disponible 0.")
            return
        modal.show()

    def _show_traslados_modal(self):
        modal = TrasladosModal(
            self.page, self.p, self.productos, self.source1_raw,
            self._warehouse_disp, self._warehouse_stock,
        )
        if not modal.traslados:
            self._show_toast("No hay productos pendientes de transferencia.")
            return
        modal.show()

    def _show_toast(self, msg: str):
        snack = ft.SnackBar(content=ft.Text(msg), duration=3000)
        self.page.snack_bar = snack
        snack.open = True
        self.page.update()

    def _toggle_expand(self, sku: str):
        if sku in self.expanded:
            self.expanded.discard(sku)
        else:
            self.expanded.add(sku)
        self._refresh_list()

    def _alerta_info(self, p: ProductoConsolidado) -> dict:
        if not p.alertas:
            return {"color": self.p.success, "icon": ft.Icons.CHECK_CIRCLE_OUTLINE, "msg": "OK"}

        # Ordenar alertas por severidad (ALTA > MEDIA > BAJA > INFO) y mostrar la más grave
        severidad_orden = {AlertaSeveridad.ALTA: 0, AlertaSeveridad.MEDIA: 1, AlertaSeveridad.BAJA: 2, AlertaSeveridad.INFO: 3}
        peor_alerta = min(p.alertas, key=lambda a: severidad_orden.get(a.severidad, 99))

        sev = peor_alerta.severidad
        if sev == AlertaSeveridad.ALTA:
            return {"color": self.p.danger, "icon": ft.Icons.ERROR_OUTLINE, "msg": peor_alerta.mensaje}
        if sev == AlertaSeveridad.MEDIA:
            return {"color": self.p.warning, "icon": ft.Icons.WARNING_AMBER_OUTLINED, "msg": peor_alerta.mensaje}
        if sev == AlertaSeveridad.BAJA:
            return {"color": self.p.info, "icon": ft.Icons.INFO_OUTLINE, "msg": peor_alerta.mensaje}
        return {"color": self.p.info, "icon": ft.Icons.INFO_OUTLINE, "msg": peor_alerta.mensaje}

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
                    tooltip=f"Ir a página {i + 1}",
                ),
            )
        self.pag_row.controls = pag_btns

        self._rebuild_kpis()
        self.page.update()

    def _go_to_page(self, page: int):
        self.current_page = page
        self._refresh_list()

    def set_productos(self, productos: list[ProductoConsolidado]):
        self.productos = productos
        self._post_process_alertas()
        self.expanded = set()
        if self._search_overlay:
            self._search_overlay.productos = productos
            self._search_overlay.source1_raw = self.source1_raw
        self._refresh_sidebar()
        self._apply_filters()
        self._refresh_list()

    def _post_process_alertas(self):
        for p in self.productos:
            for code in sorted(self.source1_raw.keys()):
                if code == "VES":
                    continue
                val = self._warehouse_disp(code, p.sku)
                if val <= 0:
                    continue

                # 121 = Inspección / Control de Calidad (importaciones)
                if code == "121":
                    p.alertas.append(Alerta(
                        tipo=AlertaTipo.STOCK_EN_OTRO_ALMACEN,
                        mensaje=(
                            f"Mercadería en inspección/CC ({val} uds). "
                            "Gestionar liberación con QC."
                        ),
                        severidad=AlertaSeveridad.MEDIA,
                    ))
                    continue

                # 40 = Producción / Fabricación
                if code == "40":
                    if val > 120:
                        msg = f"En producción ({val} uds)."
                        sev = AlertaSeveridad.BAJA
                    else:
                        msg = f"Stock rezagado en producción ({val} uds)."
                        sev = AlertaSeveridad.INFO
                    p.alertas.append(Alerta(
                        tipo=AlertaTipo.STOCK_EN_OTRO_ALMACEN,
                        mensaje=msg,
                        severidad=sev,
                    ))
                    continue

                # Otros almacenes → solo informativo
                p.alertas.append(Alerta(
                    tipo=AlertaTipo.STOCK_EN_OTRO_ALMACEN,
                    mensaje=f"Stock en almacén {code}: {val} uds.",
                    severidad=AlertaSeveridad.INFO,
                ))

            # ── Predespacho sin disponible → alerta de alta reserva ──
            if p.predespacho_total > 0 and p.disponible == 0:
                has_existente = any(
                    a.tipo == AlertaTipo.PREDESPACHO_SIN_DISPONIBLE for a in p.alertas
                )
                if not has_existente:
                    p.alertas.append(Alerta(
                        tipo=AlertaTipo.PREDESPACHO_SIN_DISPONIBLE,
                        mensaje=(
                            f"Altas reservas: predespacho {p.predespacho_total} sin disponible. "
                            "Coordinar con cliente entregas parciales o postergación."
                        ),
                        severidad=AlertaSeveridad.ALTA,
                    ))

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
        elif self._filtro_kpi == "sin_stock":
            filtered = [p for p in filtered if p.disponible == 0]
        elif self._filtro_kpi == "traslados":
            filtered = [p for p in filtered if producto_tiene_traslado(p, self.source1_raw, self._warehouse_disp)]
        if self._active_warehouse:
            filtered = [
                p for p in filtered
                if self._warehouse_stock(self._active_warehouse, p.sku) > 0
            ]
        self.productos_filtrados = filtered

    def _on_search_change(self, e):
        self.search_query = e.control.value.strip().lower()
        self.current_page = 0
        self._refresh_list()
        if self._search_overlay:
            self._search_overlay.search(e.control.value)

    def _on_search_focus(self, e):
        if e.data == "true" and self.search_field and self.search_field.value:
            self._search_overlay.search(self.search_field.value)
        elif e.data == "false":
            if self._search_overlay:
                self._search_overlay.hide()

    def _on_clear_filter(self):
        self._active_warehouse = None
        self.search_query = ""
        self.filtro_color = "todos"
        self.filtro_alerta = False
        self._filtro_kpi = None
        self.current_page = 0
        if self.search_field:
            self.search_field.value = ""
            self.search_field.update()
        if self._alerta_checkbox:
            self._alerta_checkbox.value = False
            self._alerta_checkbox.update()
        self._refresh_sidebar()
        self._rebuild_kpis()
        self._refresh_list()

    def _on_filtro_alerta_change(self, e):
        self.filtro_alerta = e.control.value
        self.current_page = 0
        self._refresh_list()

    def _on_kpi_click(self, kpi_key: str):
        if kpi_key in ("total", "con_stock"):
            if self._filtro_kpi == kpi_key:
                self._filtro_kpi = None
            else:
                self._filtro_kpi = kpi_key
            self.current_page = 0
            self._refresh_list()
        elif kpi_key == "sin_stock":
            self._show_sin_stock_modal()
        elif kpi_key == "traslados":
            self._show_traslados_modal()

    def _on_toggle_expand_all(self, e):
        self.all_expanded = not self.all_expanded
        if self.all_expanded:
            for p in self.productos_filtrados:
                self.expanded.add(p.sku)
        else:
            self.expanded.clear()
        if hasattr(self, '_toggle_expand_btn') and self._toggle_expand_btn:
            self._toggle_expand_btn.icon = ft.Icons.UNFOLD_LESS if self.all_expanded else ft.Icons.UNFOLD_MORE
            self._toggle_expand_btn.update()
        self._refresh_list()

    def _on_toggle_theme(self, e):
        if self._on_theme_toggle:
            self._on_theme_toggle()

    def _on_load_source1(self, e):
        if self._on_load_s1:
            self._on_load_s1()

    async def _on_load_source2(self, e):
        if self._on_load_s2:
            r = self._on_load_s2()
            if hasattr(r, "__await__"):
                await r

    async def _on_load_source2_manual(self, e):
        if self._on_load_s2_manual:
            r = self._on_load_s2_manual()
            if hasattr(r, "__await__"):
                await r

    async def _on_download_report(self, e):
        if self._on_download:
            r = self._on_download()
            if hasattr(r, "__await__"):
                await r

    def _calcular_kpis(self) -> dict:
        total = len(self.productos)
        con_stock = sum(1 for p in self.productos if p.disponible > 0)
        sin_stock = sum(1 for p in self.productos if p.disponible == 0)
        traslados = sum(
            1 for p in self.productos
            if producto_tiene_traslado(p, self.source1_raw, self._warehouse_disp)
        )
        return {
            "total_skus": total,
            "con_stock": con_stock,
            "sin_stock": sin_stock,
            "traslados": traslados,
        }

    def _rebuild_kpis(self):
        if not self.kpi_row or len(self.kpi_row.controls) != 4:
            return
        is_dark = self.modo == Modo.DARK
        kpi = self._calcular_kpis()
        cfgs = kpi_config(self.modo)
        for i, cfg in enumerate(cfgs):
            val = kpi[cfg.key] if cfg.key != "total" else kpi["total_skus"]
            card = self.kpi_row.controls[i]
            row = card.content
            col_ctrl = row.controls[1]
            col_ctrl.controls[0].value = str(val)
            is_active = self._filtro_kpi == cfg.key
            active_a = cfg.color + ("65" if is_dark else "45")
            card.bgcolor = active_a if is_active else cfg.idle_bg
            card.border = ft.Border(top=ft.BorderSide(1.5, cfg.color if is_active else (cfg.color + "30" if is_dark else cfg.color + "18")), left=ft.BorderSide(1.5, cfg.color if is_active else (cfg.color + "30" if is_dark else cfg.color + "18")), right=ft.BorderSide(1.5, cfg.color if is_active else (cfg.color + "30" if is_dark else cfg.color + "18")), bottom=ft.BorderSide(1.5, cfg.color if is_active else (cfg.color + "30" if is_dark else cfg.color + "18")))
        self.page.update()


