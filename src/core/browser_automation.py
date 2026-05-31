from __future__ import annotations

import logging
import os
import tempfile
from pathlib import Path

from playwright.async_api import async_playwright


_dotenv_loaded = False
def _cargar_env():
    global _dotenv_loaded
    if _dotenv_loaded:
        return
    _dotenv_loaded = True
    env_path = Path(__file__).resolve().parent.parent.parent / ".env"
    if env_path.exists():
        for line in env_path.read_text(encoding="utf-8").splitlines():
            line = line.strip()
            if not line or line.startswith("#") or "=" not in line:
                continue
            key, _, val = line.partition("=")
            os.environ.setdefault(key.strip(), val.strip().strip("\"'"))

_cargar_env()

def _get_url() -> str:
    return os.environ.get("G360_S2_URL", "http://appweb.cipsa.com.pe:9091/")

def _get_user() -> str:
    return os.environ.get("G360_S2_USER", "")

def _get_pass() -> str:
    return os.environ.get("G360_S2_PASS", "")

_log = logging.getLogger("s2_browser")


async def download_source2(
    *,
    headless: bool = True,
    download_dir: str | None = None,
    line_search: str = "PELOTAS",
    progress_callback: callable | None = None,
) -> str:
    if download_dir is None:
        download_dir = tempfile.mkdtemp(prefix="g360_s2_")

    _log_path = Path(download_dir) / "s2_automation.log"
    _log.setLevel(logging.DEBUG)
    fh = logging.FileHandler(str(_log_path), mode="w", encoding="utf-8")
    fh.setFormatter(logging.Formatter("%(asctime)s %(levelname)s %(message)s"))
    _log.addHandler(fh)
    _log.info("Inicio download_source2, download_dir=%s", download_dir)

    def log(msg: str):
        _log.info(msg)
        try:
            print(f"[s2] {msg}", flush=True)
        except UnicodeEncodeError:
            safe = msg.encode("ascii", errors="replace").decode("ascii")
            print(f"[s2] {safe}", flush=True)

    def progress(msg: str):
        if callable(progress_callback):
            progress_callback(msg)

    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=headless)
        context = await browser.new_context(accept_downloads=True)
        page = await context.new_page()

        async def dbg(step: str):
            await page.screenshot(path=Path(download_dir) / f"s2_dbg_{step}.png")
            html = await page.content()
            with open(Path(download_dir) / f"s2_html_{step}.html", "w", encoding="utf-8") as f:
                f.write(html[:50000])
            _log.info("Screenshot + HTML guardado: %s", step)

        try:
            # ── 1. Login ───────────────────────────────────────────────
            log("1. Login")
            progress("Iniciando sesión en ERP...")
            await page.goto(_get_url())
            # Usamos fill con wait implícito
            await page.fill("#Codigo", _get_user())
            await page.fill("#contrasena", _get_pass())
            
            # Presionamos Enter y esperamos activamente por un indicador de éxito (la tabla de empresas)
            await page.keyboard.press("Enter")
            try:
                # Esperar hasta 10 segundos a que aparezca el selector de empresas
                await page.wait_for_selector("#TbEmpresa", timeout=10000)
            except Exception:
                await page.wait_for_load_state("load")
            
            await dbg("01_login")

            # Detección de error: si el campo de código sigue visible, el login falló
            codigo_visible = await page.locator("#Codigo").is_visible()
            if codigo_visible:
                log(f"1x. Login fallo — el formulario sigue visible en {page.url}")
                raise ValueError(
                    "Credenciales incorrectas o sin acceso al ERP.\n"
                    "Verifique usuario y contraseña en el diálogo de credenciales."
                )

            # ── 2. Select company ──────────────────────────────────────
            log("2. Seleccionar empresa")
            progress("Accediendo al panel principal...")
            # Intentamos buscar el texto 'ALMACENES' para ser más robustos que tr:nth-child(3)
            try:
                await page.get_by_text("ALMACENES", exact=True).click(timeout=5000)
            except Exception:
                await page.locator("#TbEmpresa > tbody > tr:nth-child(3) > td").click()
            
            await page.wait_for_load_state("networkidle")
            await page.wait_for_timeout(2000)
            await dbg("02_empresa")

            # ── 3. Navigate menu ────────────────────────────────────────
            log("3. Navegar menu 317 -> 322 -> 501")
            progress("Navegando menú...")
            await page.locator('[id="317"] > a > b').click()
            await page.wait_for_timeout(400)
            await page.locator('[id="317"] > a > span').click()
            await page.wait_for_timeout(400)
            await page.locator('[id="317"] > a > span').click()
            await page.wait_for_timeout(300)
            await page.locator('[id="322"] > a > span').click()
            await page.wait_for_timeout(300)
            await page.locator('[id="501"] > a > span').click()
            await page.wait_for_load_state("load")
            await page.wait_for_timeout(2000)
            log(f"3a. URL actual: {page.url}")
            await dbg("03_menu")

            # ── 4. Warehouse selector ───────────────────────────────────
            log("4. Seleccionar almacen VES")
            progress("Seleccionando almacén VES...")
            wh_btn_text_before = await page.locator("#divAlmanecesMultiple > button").inner_text()
            log(f"4a. Btn texto antes: '{wh_btn_text_before}'")
            await page.locator("#divAlmanecesMultiple > button").click()
            await page.wait_for_timeout(800)

            log("4b. Seleccionar VES con JavaScript")
            ves_result = await page.evaluate("""() => {
                const items = document.querySelectorAll('#divAlmanecesMultiple li');
                for (const item of items) {
                    if (item.textContent.includes('CENTRO LOGISTICO VES')) {
                        const cb = item.querySelector('input[type="checkbox"]');
                        if (cb) {
                            item.scrollIntoView({block: 'center'});
                            cb.checked = true;
                            cb.dispatchEvent(new Event('change', { bubbles: true }));
                            cb.dispatchEvent(new Event('click', { bubbles: true }));
                            return {found: true, checked: cb.checked};
                        }
                        return {found: true, checked: false, reason: 'no_checkbox'};
                    }
                }
                for (const item of items) {
                    if (item.textContent.includes('VES')) {
                        const cb = item.querySelector('input[type="checkbox"]');
                        if (cb) {
                            item.scrollIntoView({block: 'center'});
                            cb.checked = true;
                            cb.dispatchEvent(new Event('change', { bubbles: true }));
                            cb.dispatchEvent(new Event('click', { bubbles: true }));
                            return {found: true, checked: cb.checked, text: item.textContent.trim().slice(0,80)};
                        }
                        return {found: true, checked: false, reason: 'no_checkbox', text: item.textContent.trim().slice(0,80)};
                    }
                }
                return {found: false, total: items.length};
            }""")
            log(f"4b. VES JS result: {ves_result}")
            await page.wait_for_timeout(500)
            await page.locator("#divAlmanecesMultiple > button").click()
            await page.wait_for_timeout(400)
            wh_btn_text_after = await page.locator("#divAlmanecesMultiple > button").inner_text()
            log(f"4c. Btn texto despues: '{wh_btn_text_after}'")
            await dbg("04_almacen")

            # ── 5. Select line ──────────────────────────────────────────
            log("5. Seleccionar linea PELOTAS")
            progress("Seleccionando línea PELOTAS...")
            line_js = await page.evaluate("""(search) => {
                const ids = ['cboLinea', 'cbo_Linea', 'cbLinea', 'linea', 'Linea'];
                for (const id of ids) {
                    const el = document.getElementById(id);
                    if (el && el.tagName === 'SELECT') {
                        for (const opt of el.options) {
                            if (opt.text.toUpperCase().includes(search.toUpperCase())) {
                                el.value = opt.value;
                                el.dispatchEvent(new Event('change', {bubbles: true}));
                                try { jQuery(el).trigger('chosen:updated'); } catch(e) {}
                                return {method: 'id_' + id, value: opt.value, text: opt.text};
                            }
                        }
                    }
                }
                const allSelects = document.querySelectorAll('select');
                for (const sel of allSelects) {
                    const chosenId = sel.id + '_chosen';
                    if (document.getElementById(chosenId)) {
                        for (const opt of sel.options) {
                            if (opt.text.toUpperCase().includes(search.toUpperCase())) {
                                sel.value = opt.value;
                                sel.dispatchEvent(new Event('change', {bubbles: true}));
                                try { jQuery(sel).trigger('chosen:updated'); } catch(e) {}
                                return {method: 'chosen_match', selId: sel.id, value: opt.value, text: opt.text};
                            }
                        }
                    }
                }
                const chosenContainer = document.getElementById('cboLinea_chosen');
                if (chosenContainer) {
                    let prev = chosenContainer.previousElementSibling;
                    while (prev) {
                        if (prev.tagName === 'SELECT') {
                            for (const opt of prev.options) {
                                if (opt.text.toUpperCase().includes(search.toUpperCase())) {
                                    prev.value = opt.value;
                                    prev.dispatchEvent(new Event('change', {bubbles: true}));
                                    try { jQuery(prev).trigger('chosen:updated'); } catch(e) {}
                                    return {method: 'prev_sibling', selId: prev.id, value: opt.value, text: opt.text};
                                }
                            }
                        }
                        prev = prev.previousElementSibling;
                    }
                }
                return {found: false, selectCount: allSelects.length};
            }""", line_search)
            log(f"5. Linea JS result: {line_js}")

            if not line_js.get('found', False):
                log("5a. Fallback: click UI Chosen.js")
                await page.locator("#cboLinea_chosen > a").click()
                await page.wait_for_timeout(1000)
                inp = page.locator("#cboLinea_chosen > div > div > input")
                await inp.click()
                search_val = line_search.lower()
                await inp.type(search_val, delay=60)
                await page.wait_for_timeout(1500)
                clicked = False
                for sel in ["#cboLinea_chosen .active-result", "#cboLinea_chosen li", "#cboLinea_chosen em"]:
                    el = page.locator(sel).first
                    count = await el.count()
                    if count > 0 and await el.is_visible():
                        txt = await el.inner_text()
                        if search_val in txt.lower():
                            await el.click()
                            log(f"5a. Clickeado: {sel} -> '{txt}'")
                            clicked = True
                            break
                if not clicked:
                    log("5a. No se encontro resultado para clickear")
                await page.wait_for_timeout(400)

            line_text = await page.locator("#cboLinea_chosen > a > span").inner_text()
            log(f"5b. Linea texto despues: '{line_text}'")
            await dbg("05_linea")
            log("5d. Checkbox chk (Consolidar)")
            chk_info = await page.evaluate("""() => {
                const el = document.getElementById('chk');
                if (!el) return {found: false};
                return {
                    found: true,
                    tag: el.tagName,
                    type: el.type || '',
                    checked: el.checked !== undefined ? el.checked : null,
                    value: el.value || '',
                    text: (el.parentElement ? el.parentElement.textContent.trim() : '').slice(0,60)
                };
            }""")
            log(f"5d. chk info: {chk_info}")
            if chk_info.get('found'):
                if not chk_info.get('checked'):
                    await page.evaluate("""() => {
                        const el = document.getElementById('chk');
                        if (el && el.type === 'checkbox' && !el.checked) {
                            el.checked = true;
                            el.dispatchEvent(new Event('change', {bubbles: true}));
                            el.dispatchEvent(new Event('click', {bubbles: true}));
                        } else if (el) {
                            // might be a text input - type "on"
                            el.value = 'on';
                            el.dispatchEvent(new Event('input', {bubbles: true}));
                            el.dispatchEvent(new Event('change', {bubbles: true}));
                        }
                    }""")
                    await page.wait_for_timeout(300)
                    log("5d. chk activado")
                else:
                    log("5d. chk ya estaba activo")
            await dbg("05d_chk")

            # ── 6. Tree / group ─────────────────────────────────────────
            log("6. Arbol modal")
            progress("Configurando filtros...")
            try:
                await page.locator("#btnArbol").click(timeout=3000)
                await page.wait_for_load_state("load")
                await page.wait_for_timeout(2000)
                await dbg("06_arbol_abierto")

                # try using dynatree JS API to expand and select
                tree_api = await page.evaluate("""() => {
                    const $tree = jQuery('#tree');
                    if (!$tree || !$tree.dynatree) return {api: false};
                    try {
                        const tree = $tree.dynatree('getTree');
                        if (!tree) return {api: true, tree: false};
                        const root = tree.getRoot();
                        
                        // Expandir y seleccionar TODO el árbol de forma recursiva
                        root.visit((node) => {
                            node.expand(true);
                            node.select(true);
                        });
                        return {api: true, expanded: true, childCount: root.children.length};
                    } catch (e) {
                        return {api: true, error: e.message};
                    }
                }""")
                log(f"6b. Tree API result: {tree_api}")
                await page.wait_for_timeout(1500)

                # click OK button if present
                try:
                    await page.locator("#mdlListaGrupo button.btn.btn-sm.btn-primary").click(timeout=3000)
                    await page.wait_for_timeout(400)
                    log("6b. Tree OK button clicked")
                except Exception:
                    log("6b. No OK button found, trying to close modal")
                    await page.keyboard.press("Escape")
                    await page.wait_for_timeout(400)

                # always clean up modals
                await page.evaluate("""document.querySelectorAll('.bootbox, .modal, .modal-backdrop')
                    .forEach(el => el.remove());
                document.body.classList.remove('modal-open');
                document.body.style.overflow = '';
                document.body.style.paddingRight = '';""")
                await page.wait_for_timeout(500)
            except Exception as exc:
                log(f"6x. No se pudo abrir arbol modal: {exc}")
            await dbg("06_post_modal")

            # ── 7. Export option radio ──────────────────────────────────
            log("7. Click radio opcion exportar")
            progress("Configurando exportación...")
            # recording: #idTabsTablas > div.widget-box > div.widget-body > div > div > div:nth-child(4) > div > label:nth-child(3) > span
            radio_selector = "#idTabsTablas > div.widget-box > div.widget-body > div > div > div:nth-child(4) > div > label:nth-child(3) > span"
            radio_span = page.locator(radio_selector)
            radio_visible = await radio_span.is_visible()
            log(f"7a. Radio span visible: {radio_visible}")
            await radio_span.click()
            await page.wait_for_timeout(400)
            log("7b. Radio exportar clickeado")
            await dbg("07_radio")

            # ── 8. Search ───────────────────────────────────────────────
            log("8. Click Buscar")
            progress("Buscando datos...")
            await page.locator("#btnBuscar").click()
            await page.wait_for_timeout(3000)

            # wait dynamically for results table to have rows (max 60s)
            log("8a. Esperando resultados...")
            for attempt in range(120):
                await page.wait_for_timeout(500)
                row_count = await page.evaluate(
                    "document.querySelectorAll('table tbody tr').length"
                )
                if row_count > 0:
                    log(f"8a. Tabla tiene {row_count} filas tras {attempt*0.5:.0f}s")
                    break
            else:
                log("8a. Timeout esperando resultados (60s)")

            has_rows = await page.evaluate(
                "document.querySelectorAll('table tbody tr').length"
            )
            log(f"8b. Filas en tabla resultado: {has_rows}")

            await dbg("08_post_search")

            # remove any modal that might have appeared
            log("8c. Remover modales post-search")
            await page.evaluate("""document.querySelectorAll('.bootbox, .modal, .modal-backdrop')
                .forEach(el => el.remove());
            document.body.classList.remove('modal-open');""")
            await page.wait_for_timeout(500)

            # ── 9. Export XLS ───────────────────────────────────────────
            log("9. Click exportar")
            progress("Descargando archivo...")
            export_btn = page.locator("#hrefExportar")
            export_btn_visible = await export_btn.is_visible()
            export_btn_text = await export_btn.inner_text()
            log(f"9b. Export btn visible: {export_btn_visible}")
            log(f"9c. Export btn text: '{export_btn_text}'")

            async with page.expect_download() as download_info:
                await page.locator("#hrefExportar > i").click()

            download = await download_info.value
            download_path = os.path.join(download_dir, download.suggested_filename)
            await download.save_as(download_path)
            log(f"9d. Archivo guardado: {download_path}")

            file_size = Path(download_path).stat().st_size
            log(f"9e. Tamano archivo: {file_size} bytes")

            with open(download_path, "rb") as f:
                header = f.read(200)
            log(f"9f. Header bytes: {header[:80]}")

            await page.wait_for_timeout(1000)
            await dbg("09_exportado")

            # ── 10. Logout ──────────────────────────────────────────────
            log("10. Logout")
            progress("Cerrando sesión...")
            await page.locator("div.navbar-buttons span").first.click()
            await page.wait_for_timeout(300)
            await page.locator("#navbar li > ul a").click()
            await page.wait_for_load_state("networkidle")
            await dbg("10_logout")

            await browser.close()
            log(f"Fin OK, archivo: {download_path}")

        except Exception:
            await dbg("error")
            await browser.close()
            _log.exception("Error en automation")
            raise

    return download_path
