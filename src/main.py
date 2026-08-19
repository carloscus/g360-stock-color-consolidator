"""Stock Color Consolidator - Aplicacion principal CIPSA."""
from __future__ import annotations

import asyncio
import json
import os
import shutil
import subprocess
import tkinter as tk
from datetime import datetime
from pathlib import Path
from tkinter import filedialog

import flet as ft

# Core imports
from src.config.theme import LIGHT, DARK, Modo
from src.core.parsers import parse_source2, agregar_almacenes
from src.core.consolidator import consolidar
from src.core.downloader import download_source1
from src.core.browser_automation import download_source2 as browser_download_source2
from src.core.models import ProductoConsolidado
from src.core.constants import (
    WINDOW_WIDTH,
    WINDOW_HEIGHT,
    WINDOW_MIN_WIDTH,
    WINDOW_MIN_HEIGHT,
    TEMP_DIR_PREFIX,
)
from src.core.errors import friendly_error
from src.core.report import generar_reporte_xlsx

# UI imports
from src.ui.dashboard import Dashboard
from src.ui.sku_detail import SkuDetailModal

CREDENTIALS_DIR = Path(os.environ.get("APPDATA", Path.home())) / "g360-stock-consolidator"
CREDENTIALS_FILE = CREDENTIALS_DIR / "creds.json"


def _validar_archivo_source2(path: str) -> bool:
    try:
        with open(path, "rb") as f:
            raw = f.read(2000)
        content = raw.decode("utf-8", errors="replace").lower()
        return "<html" in content and "color" in content and "cantidad" in content
    except Exception:
        return False


def _close_dlg(page: ft.Page, extra_cb=None):
    dlg = getattr(page, '_active_dialog', None)
    if dlg:
        page.close(dlg)
    page.update()
    if callable(extra_cb):
        page.run_task(extra_cb)


def _show_error(page: ft.Page, title: str, ex: Exception, close_cb=None, on_retry_creds=None, on_manual_file=None):
    message = friendly_error(ex)
    is_cred = "credenciales" in message.lower()

    def _change(e):
        _close_dlg(page)
        if callable(on_retry_creds):
            on_retry_creds()

    async def _manual(e):
        _close_dlg(page)
        if callable(on_manual_file):
            r = on_manual_file()
            if hasattr(r, "__await__"):
                await r

    actions = [
        ft.TextButton(
            "OK",
            on_click=lambda _: _close_dlg(page, close_cb),
            tooltip="Cerrar mensaje",
        ),
    ]
    if is_cred and on_retry_creds:
        actions.insert(0, ft.Button("Cambiar credenciales", on_click=_change, tooltip="Abrir diálogo para cambiar credenciales ERP"))
    if on_manual_file:
        actions.insert(0, ft.TextButton("Cargar manualmente", on_click=_manual, tooltip="Seleccionar archivo local"))

    dlg = ft.AlertDialog(
        title=ft.Text(title),
        content=ft.Text(message),
        actions=actions,
    )
    page._active_dialog = dlg
    page.open(dlg)
    dlg.open = True
    page.update()


class StockConsolidatorApp:
    def __init__(self, page: ft.Page):
        self.page = page
        self.modo = Modo.LIGHT
        self.source1_raw: dict[str, dict[str, dict]] = {}
        self.source2_data: dict[str, list[tuple[str, str, int]]] = {}
        self.productos: list[ProductoConsolidado] = []
        self.dashboard: Dashboard | None = None
        self._creds: dict[str, str] = self._load_cached_credentials()
        self._setup_window()
        self._build()

    def _setup_window(self):
        self.page.title = "Stock Color Consolidator - CIPSA"
        self.page.theme_mode = ft.ThemeMode.LIGHT
        self.page.padding = 0
        self.page.window_width = WINDOW_WIDTH
        self.page.window_height = WINDOW_HEIGHT
        self.page.window_min_width = WINDOW_MIN_WIDTH
        self.page.window_min_height = WINDOW_MIN_HEIGHT
        self.page.on_keyboard_event = self._on_keyboard
        try:
            self.page.window_center()
        except AttributeError:
            pass
        self.page.bgcolor = LIGHT.bg

    def _on_keyboard(self, e: ft.KeyboardEvent):
        if self.dashboard and self.dashboard._search_overlay:
            self.dashboard._search_overlay.on_key(e)

    def _build(self):
        paleta = DARK if self.modo == Modo.DARK else LIGHT
        self.page.bgcolor = paleta.bg

        self.dashboard = Dashboard(self.page)
        self.dashboard.set_on_sku_click(self._on_sku_click)
        self.dashboard.set_on_theme_toggle(self._on_theme_toggle)
        self.dashboard.set_on_download_report(self._on_download_report)
        self.dashboard.set_on_credentials(self._show_credentials_dialog)
        self.dashboard.set_on_expand_all(self._on_expand_all)
        self.dashboard.set_on_load_source(
            self._on_download_source1,
            self._on_download_source2,
            self._pick_file,
        )
        self.dashboard.set_source1_raw(self.source1_raw)
        self.dashboard.set_theme(self.modo)

        view = self.dashboard.build()

        self.page.clean()
        self.page.add(view)

        # Cargamos productos
        self.dashboard.set_productos(self.productos)
        self.page.update()

        # Mostrar dialog de credenciales en la primera ejecucion (sin usuario cacheado)
        if not self._creds.get("user"):
            self._schedule_credentials_dialog()

    def _on_expand_all(self, expand: bool):
        if self.dashboard:
            self.dashboard.expand_all(expand)

    def _on_theme_toggle(self):
        self.modo = Modo.DARK if self.modo == Modo.LIGHT else Modo.LIGHT
        paleta = DARK if self.modo == Modo.DARK else LIGHT
        self.page.theme_mode = ft.ThemeMode.DARK if self.modo == Modo.DARK else ft.ThemeMode.LIGHT
        self.page.bgcolor = paleta.bg
        self._build()

    def _on_download_source1(self):
        if self.source1_raw:
            self._confirm_reload(
                "Ya hay datos de Source 1 cargados.\n"
                "Solo descargue de nuevo si hubo movimientos de stock nuevos.\n"
                "¿Desea continuar?",
                self._run_download_source1,
            )
            return
        self._run_download_source1()

    def _run_download_source1(self):
        self.dashboard.set_loading(True, "Descargando Source 1...")
        try:
            result = download_source1()
            if not result:
                self.dashboard.set_loading(False)
                self._show_toast("No se obtuvieron datos del servidor.")
                return
            self.source1_raw = result
            self.productos = consolidar(
                agregar_almacenes(self.source1_raw, ["VES"]),
                self.source2_data,
            )
            if self.dashboard:
                self.dashboard.set_source1_raw(self.source1_raw)
                self.dashboard.set_productos(self.productos)
            self.page.update()
            self._show_toast("Source 1 descargado correctamente.")
        except Exception as ex:
            import traceback
            traceback.print_exc()
            _show_error(self.page, "Error al descargar Source 1", ex)
        finally:
            self.dashboard.set_loading(False)
            self.page.update()

    async def _on_download_source2(self):
        if self.source2_data:
            self._confirm_reload(
                "Ya hay datos de Source 2 procesados.\n"
                "Solo descargue de nuevo si hay nuevos colores o productos.\n"
                "¿Desea continuar?",
                self._run_download_source2_with_creds,
            )
            return
        await self._run_download_source2_with_creds()

    async def _run_download_source2_with_creds(self):
        if not self._creds.get("user") or not self._creds.get("pass"):
            self._show_credentials_dialog(on_save_callback=self._run_download_source2)
            return
        await self._run_download_source2()

    async def _run_download_source2(self):
        download_dir: str | None = None
        os.environ["G360_S2_USER"] = self._creds.get("user", "")
        os.environ["G360_S2_PASS"] = self._creds.get("pass", "")
        self._show_toast("Iniciando descarga Source 2...")
        self.dashboard.set_loading(True, "Descargando Source 2 (ERP)...")
        try:
            path = await browser_download_source2(
                progress_callback=lambda msg: self.dashboard.set_loading(True, msg)
            )
            if not path:
                self.dashboard.set_loading(False)
                self._show_toast("No se obtuvo archivo del servidor.")
                return

            download_dir = str(Path(path).parent)

            file_size = Path(path).stat().st_size
            if file_size < 100:
                self.dashboard.set_loading(False)
                self._show_toast(f"Archivo muy pequeno ({file_size} bytes). Revise logs.")
                return

            if not _validar_archivo_source2(path):
                self.dashboard.set_loading(False)
                self._show_toast("El archivo descargado no tiene el formato esperado del ERP.")
                return

            self.dashboard.set_loading(True, "Procesando colores...")
            self.source2_data = parse_source2(path)
            if not self.source2_data:
                self.dashboard.set_loading(False)
                self._show_toast("El archivo descargado no contiene datos de colores. Revise logs.")
                return
            self.productos = consolidar(
                agregar_almacenes(self.source1_raw, ["VES"]),
                self.source2_data,
            )
            if self.dashboard:
                self.dashboard.set_productos(self.productos)
            self.page.update()
            self._show_toast(f"Source 2 descargado: {Path(path).name} ({len(self.source2_data)} SKUs)")
        except Exception as ex:
            import traceback
            traceback.print_exc()
            _show_error(
                self.page,
                "Error al descargar Source 2",
                ex,
                on_retry_creds=lambda: self._show_credentials_dialog(
                    on_save_callback=self._run_download_source2
                ),
                on_manual_file=self._pick_file,
            )
        finally:
            self.dashboard.set_loading(False)
            self._limpiar_descarga(download_dir)
            self.page.update()

    def _on_sku_click(self, sku: str):
        producto = next((p for p in self.productos if p.sku == sku), None)
        if producto:
            paleta = DARK if self.modo == Modo.DARK else LIGHT
            modal = SkuDetailModal(self.page, producto, paleta)
            modal.show()

    async def _pick_file(self):
        root = tk.Tk()
        root.withdraw()
        root.wm_attributes("-topmost", True)
        path = filedialog.askopenfilename(
            title="Seleccionar Source 2 (Colores)",
            filetypes=[("Archivos Excel", "*.xlsx *.xls *.csv"), ("Todos", "*.*")],
        )
        root.destroy()
        if not path:
            return

        self.dashboard.set_loading(True, "Procesando archivo de colores...")
        try:
            self.source2_data = parse_source2(path)
            self.productos = consolidar(
                agregar_almacenes(self.source1_raw, ["VES"]),
                self.source2_data,
            )

            if self.dashboard:
                self.dashboard.set_productos(self.productos)
            self.page.update()
        except Exception as ex:
            import traceback
            traceback.print_exc()
            _show_error(self.page, "Error al procesar archivo", ex)
        finally:
            self.dashboard.set_loading(False)
            self.page.update()

    def _close_dialog(self, extra_cb=None):
        _close_dlg(self.page, extra_cb)

    def _confirm_reload(self, message: str, on_confirm):
        dlg = ft.AlertDialog(
            title=ft.Text("Confirmar descarga"),
            content=ft.Text(message),
            actions=[
                ft.TextButton("Cancelar", on_click=lambda _: self._close_dialog(), tooltip="Cancelar descarga"),
                ft.Button("Descargar", on_click=lambda _: self._close_dialog(on_confirm), tooltip="Confirmar y descargar"),
            ],
        )
        self.page._active_dialog = dlg
        self.page.open(dlg)
        self.page.update()

    def _limpiar_descarga(self, download_dir: str | None):
        if download_dir and TEMP_DIR_PREFIX in download_dir:
            try:
                shutil.rmtree(download_dir, ignore_errors=True)
            except Exception:
                pass

    def _load_cached_credentials(self) -> dict[str, str]:
        if CREDENTIALS_FILE.exists():
            try:
                return json.loads(CREDENTIALS_FILE.read_text())
            except Exception:
                pass
        return {"user": "", "pass": ""}

    def _cache_credentials(self):
        CREDENTIALS_DIR.mkdir(parents=True, exist_ok=True)
        safe = {"user": self._creds.get("user", "")}
        CREDENTIALS_FILE.write_text(json.dumps(safe))

    async def _show_credentials_dialog_async(self):
        await asyncio.sleep(0.1)
        self._show_credentials_dialog()

    def _schedule_credentials_dialog(self):
        asyncio.ensure_future(self._show_credentials_dialog_async())

    def _show_credentials_dialog(self, on_save_callback=None):
        cached_user = self._creds.get("user", "")

        error_text = ft.Text("", color=ft.Colors.RED, size=12, visible=False)
        _dlg_ref = [None]

        def _on_save(e=None):
            user = user_field.value.strip()
            pwd = pass_field.value
            if not user or not pwd:
                error_text.value = "Debe ingresar usuario y contraseña."
                error_text.visible = True
                self.page.update()
                return
            error_text.visible = False
            self._creds["user"] = user
            self._creds["pass"] = pwd
            self._cache_credentials()
            dlg = _dlg_ref[0]
            if dlg:
                dlg.open = False
                self.page.update()
            if callable(on_save_callback):
                self.page.run_task(on_save_callback)
            else:
                self._show_toast("Credenciales guardadas.")

        user_field = ft.TextField(
            label="Usuario ERP",
            value=cached_user,
            hint_text="ej. jperez",
            autofocus=not bool(cached_user),
        )
        pass_field = ft.TextField(
            label="Contraseña",
            password=True,
            can_reveal_password=True,
            autofocus=bool(cached_user),
            on_submit=lambda e: _on_save(e),
        )

        save_label = "Guardar y descargar" if on_save_callback else "Guardar"

        dlg = ft.AlertDialog(
            title=ft.Container(
                content=ft.Column(
                    [
                        ft.Container(
                            content=ft.Icon(ft.Icons.LOCK_OUTLINE, size=24, color=ft.Colors.with_opacity(0.7, self.dashboard.p.accent)),
                            bgcolor=ft.Colors.with_opacity(0.1, self.dashboard.p.accent),
                            padding=10,
                            border_radius=10,
                        ),
                        ft.Container(height=8),
                        ft.Text("LOGIN", size=18, weight=ft.FontWeight.W_700, color=self.dashboard.p.text),
                        ft.Text("appweb.cipsa.com.pe", size=11, color=self.dashboard.p.text_secondary),
                    ],
                    horizontal_alignment=ft.CrossAxisAlignment.CENTER,
                    spacing=0,
                ),
                padding=ft.Padding(left=0, right=0, top=8, bottom=0),
            ),
            title_padding=0,
            content=ft.Column(
                [
                    ft.Divider(height=1, color=self.dashboard.p.glass_border),
                    ft.Container(height=8),
                    user_field,
                    ft.Container(height=4),
                    pass_field,
                    error_text,
                ],
                tight=True,
                width=360,
                spacing=0,
                horizontal_alignment=ft.CrossAxisAlignment.STRETCH,
            ),
            actions=[
                ft.TextButton("Cancelar", on_click=lambda _: self._close_dialog(), tooltip="Cerrar sin guardar"),
                ft.FilledTonalButton(save_label, on_click=_on_save, tooltip="Guardar credenciales y continuar"),
            ],
            actions_alignment=ft.MainAxisAlignment.END,
        )
        _dlg_ref[0] = dlg
        self.page._active_dialog = dlg
        self.page.open(dlg)
        self.page.update()

    async def _on_download_report(self):
        if not self.productos:
            self._show_toast("No hay datos. Cargue Source 1 y Source 2 primero.")
            return
        desktop = os.path.join(os.path.expanduser("~"), "Desktop")
        filename = f"reporte_stock_colores_{datetime.now():%d%m%Y}.xlsx"
        path = os.path.join(desktop, filename)
        try:
            os.environ["G360_S2_USER"] = self._creds.get("user", "")
            generar_reporte_xlsx(self.productos, path, self.source1_raw)
            subprocess.Popen(["explorer", f"/select,{os.path.normpath(path)}"])
            self._show_toast(f"Reporte guardado en Escritorio")
        except Exception as ex:
            import traceback
            traceback.print_exc()
            _show_error(self.page, "Error al guardar reporte", ex)

    def _show_toast(self, msg: str):
        snack = ft.SnackBar(content=ft.Text(msg), duration=3000)
        self.page.snack_bar = snack
        snack.open = True
        self.page.update()


def main(page: ft.Page):
    StockConsolidatorApp(page)