"""G360 Stock Color Consolidator - Aplicacion principal."""
from __future__ import annotations

import json
import os
import shutil
import tempfile
from datetime import datetime
from pathlib import Path

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


def _close_dlg(page: ft.Page, dlg: ft.AlertDialog, extra_cb=None):
    dlg.open = False
    page.update()
    if callable(extra_cb):
        extra_cb()


def _show_error(page: ft.Page, title: str, ex: Exception, close_cb=None, on_retry_creds=None, on_manual_file=None):
    message = friendly_error(ex)
    is_cred = "credenciales" in message.lower()

    def _change(e):
        _close_dlg(page, dlg, None)
        if callable(on_retry_creds):
            on_retry_creds()

    def _manual(e):
        _close_dlg(page, dlg, None)
        if callable(on_manual_file):
            on_manual_file()

    actions = [
        ft.TextButton(
            "OK",
            on_click=lambda _: _close_dlg(page, dlg, close_cb),
        ),
    ]
    if is_cred and on_retry_creds:
        actions.insert(0, ft.ElevatedButton("Cambiar credenciales", on_click=_change))
    if on_manual_file:
        actions.insert(0, ft.TextButton("Cargar manualmente", on_click=_manual))

    dlg = ft.AlertDialog(
        title=ft.Text(title),
        content=ft.Text(message),
        actions=actions,
    )
    page.dialog = dlg
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
        self._picker: ft.FilePicker | None = None
        self._save_picker: ft.FilePicker | None = None
        self._creds: dict[str, str] = self._load_cached_credentials()
        self._setup_window()
        self._build()
        self._show_credentials_dialog()

    def _setup_window(self):
        self.page.title = "G360 - Stock Color Consolidator"
        self.page.theme_mode = ft.ThemeMode.LIGHT
        self.page.padding = 0
        self.page.window_width = WINDOW_WIDTH
        self.page.window_height = WINDOW_HEIGHT
        self.page.window_min_width = WINDOW_MIN_WIDTH
        self.page.window_min_height = WINDOW_MIN_HEIGHT
        self.page.window_center()
        self.page.bgcolor = LIGHT.bg

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

        self._save_picker = ft.FilePicker(on_result=self._on_save_report)
        self.page.overlay.append(self._save_picker)

        view = self.dashboard.build()

        self.page.clean()
        self.page.add(view)

        # Cargamos productos
        self.dashboard.set_productos(self.productos)
        self.page.update()

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

    def _on_download_source2(self):
        if self.source2_data:
            self._confirm_reload(
                "Ya hay datos de Source 2 procesados.\n"
                "Solo descargue de nuevo si hay nuevos colores o productos.\n"
                "¿Desea continuar?",
                self._run_download_source2_with_creds,
            )
            return
        self._run_download_source2_with_creds()

    def _run_download_source2_with_creds(self):
        if not self._creds.get("user") or not self._creds.get("pass"):
            self._show_credentials_dialog(on_save_callback=self._run_download_source2)
            return
        self._run_download_source2()

    def _run_download_source2(self):
        download_dir: str | None = None
        os.environ["G360_S2_USER"] = self._creds.get("user", "")
        os.environ["G360_S2_PASS"] = self._creds.get("pass", "")
        self.dashboard.set_loading(True, "Descargando Source 2 (ERP)...")
        try:
            path = browser_download_source2(
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
            _show_error(self.page, "Error al descargar Source 2", ex, on_retry_creds=self._show_credentials_dialog, on_manual_file=self._pick_file)
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

    def _pick_file(self):
        if self._picker:
            self.page.overlay.remove(self._picker)
        self._picker = ft.FilePicker(on_result=self._on_file_picked)
        self.page.overlay.append(self._picker)
        self.page.update()

        self._picker.pick_files(
            allow_multiple=False,
            allowed_extensions=["xlsx", "xls", "csv"],
            dialog_title="Seleccionar Source 2 (Colores)",
        )

    def _on_file_picked(self, e: ft.FilePickerResultEvent):
        if not e.files or not e.files[0].path:
            return

        path = e.files[0].path
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

    def _close_dialog(self, dlg: ft.AlertDialog, extra_cb=None):
        _close_dlg(self.page, dlg, extra_cb)

    def _confirm_reload(self, message: str, on_confirm):
        dlg = ft.AlertDialog(
            title=ft.Text("Confirmar descarga"),
            content=ft.Text(message),
            actions=[
                ft.TextButton("Cancelar", on_click=lambda _: self._close_dialog(dlg)),
                ft.ElevatedButton("Descargar", on_click=lambda _: self._close_dialog(dlg, on_confirm)),
            ],
        )
        self.page.dialog = dlg
        dlg.open = True
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

    def _show_credentials_dialog(self, on_save_callback=None):
        hint_user = self._creds.get("user", "")
        user_field = ft.TextField(
            label="Usuario",
            hint_text=hint_user if hint_user else "usuario",
            autofocus=True,
        )
        pass_field = ft.TextField(
            label="Contraseña",
            password=True,
            can_reveal_password=True,
        )

        def _on_save(e):
            self._creds["user"] = user_field.value.strip()
            self._creds["pass"] = pass_field.value
            self._cache_credentials()
            self._close_dialog(dlg)
            self._show_toast("Credenciales guardadas.")
            if callable(on_save_callback):
                on_save_callback()

        dlg = ft.AlertDialog(
            title=ft.Text("Credenciales ERP (appweb.cipsa.com.pe)"),
            content=ft.Column([user_field, pass_field], tight=True, width=320),
            actions=[
                ft.TextButton("Cancelar", on_click=lambda _: self._close_dialog(dlg)),
                ft.ElevatedButton("Guardar", on_click=_on_save),
            ],
        )
        self.page.dialog = dlg
        dlg.open = True
        self.page.update()

    def _on_download_report(self):
        if not self.productos:
            self._show_toast("No hay datos. Cargue Source 1 y Source 2 primero.")
            return
        self._save_picker.save_file(
            file_name=f"reporte_stock_colores_{datetime.now():%d%m%Y}.xlsx",
            allowed_extensions=["xlsx"],
            dialog_title="Guardar reporte XLSX",
        )

    def _on_save_report(self, e: ft.FilePickerResultEvent):
        if not e.path:
            return
        try:
            os.environ["G360_S2_USER"] = self._creds.get("user", "")
            generar_reporte_xlsx(self.productos, e.path, self.source1_raw)
            self._show_toast(f"Reporte guardado: {e.path}")
        except Exception as ex:
            import traceback
            traceback.print_exc()
            _show_error(self.page, "Error al guardar reporte", ex)

    def _show_toast(self, msg: str):
        snack = ft.SnackBar(content=ft.Text(msg), duration=3000)
        self.page.overlay.append(snack)
        snack.open = True
        self.page.update()


def main(page: ft.Page):
    StockConsolidatorApp(page)