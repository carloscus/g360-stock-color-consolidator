from __future__ import annotations

from src.core.xls_fallback import leer_xls_fallback


def parse_source1_all(path: str) -> dict[str, dict[str, dict]]:
    filas = leer_xls_fallback(path)
    if not filas:
        return {}

    resultado: dict[str, dict[str, dict]] = {}
    for row in filas:
        if len(row) < 19:
            continue
        sku_raw = (row[1] or "").strip()
        desc_raw = (row[2] or "").strip()
        almacen_raw = (row[9] or "").strip().upper()
        stock_raw = (row[13] or "").strip()
        pred_raw = (row[16] or "").strip()

        if not sku_raw or sku_raw in (".", "ARTÍCULO", "ARTICULO"):
            continue
        if not stock_raw:
            continue
        if not almacen_raw:
            continue

        sku = sku_raw.lstrip("'").strip()
        if not sku:
            continue
        try:
            stock = int(float(stock_raw.replace(",", "")))
            pred = int(float(pred_raw.replace(",", ""))) if pred_raw else 0
        except (ValueError, TypeError):
            stock = 0
            pred = 0

        almacen_row = resultado.setdefault(almacen_raw, {})
        if sku not in almacen_row:
            almacen_row[sku] = {"stock": 0, "predespacho": 0, "descripcion": desc_raw}
        almacen_row[sku]["stock"] += stock
        almacen_row[sku]["predespacho"] += pred

    return resultado


def parse_source1(path: str) -> dict[str, dict]:
    return agregar_almacenes(parse_source1_all(path), ["VES"])


def agregar_almacenes(
    data: dict[str, dict[str, dict]],
    warehouses: list[str],
) -> dict[str, dict]:
    resultado: dict[str, dict] = {}
    for w in warehouses:
        w_upper = w.strip().upper()
        for sku, info in data.get(w_upper, {}).items():
            if sku not in resultado:
                resultado[sku] = {"stock": 0, "predespacho": 0, "descripcion": info.get("descripcion", "")}
            resultado[sku]["stock"] += info.get("stock", 0)
            resultado[sku]["predespacho"] += info.get("predespacho", 0)
    return resultado


def parse_source2(path: str) -> dict[str, list[tuple[str, str, int]]]:
    from bs4 import BeautifulSoup

    resultado: dict[str, list[tuple[str, str, int]]] = {}
    last_sku = ""
    last_modelo = ""
    last_grupo = ""

    try:
        with open(path, "rb") as f:
            raw = f.read()
    except FileNotFoundError:
        return resultado

    content = raw.decode("utf-8", errors="replace")
    soup = BeautifulSoup(content, "html.parser")
    rows = soup.find_all("tr")

    for row in rows:
        cells = row.find_all(["td", "th"])
        tags = [c.name for c in cells]
        texts = [c.get_text(strip=True) for c in cells]
        n = len(cells)
        last_is_td = tags[-1] == "td"

        if n <= 1 or not last_is_td:
            continue

        if n >= 5:
            mappings = {8: (3, 5, 6, 7), 7: (2, 4, 5, 6), 6: (1, 3, 4, 5), 5: (0, 2, 3, 4)}
            i_sku, i_mod, i_col, i_cant = mappings[n]
            sku_raw = texts[i_sku]
            modelo_raw = texts[i_mod]
            color_raw = texts[i_col]
            cant_text = texts[i_cant]

            # track Grupo (only n=8 has explicit Grupo at [0])
            if n == 8:
                grupo_raw = texts[0]
                if grupo_raw and grupo_raw != last_grupo:
                    last_grupo = grupo_raw
                    last_modelo = ""

            if sku_raw:
                last_sku = sku_raw.lstrip("'").strip()
                if not modelo_raw:
                    last_modelo = ""
            if modelo_raw:
                if modelo_raw in ("S/M", ""):
                    last_modelo = ""
                else:
                    last_modelo = modelo_raw

            target_color = _normalize_color(color_raw)
            if target_color is None:
                continue
            cant = _parse_cant(cant_text)
            # non-NACIONAL groups → force SIN COLOR
            if last_grupo != "NACIONAL":
                _add_row(resultado, last_sku, "SIN COLOR", "", cant)
            else:
                _add_row(resultado, last_sku, target_color, last_modelo, cant)

        elif n == 3:
            modelo_raw = texts[0]
            color_raw = texts[1]
            cant_text = texts[2]

            if modelo_raw:
                if modelo_raw in ("S/M", ""):
                    last_modelo = ""
                else:
                    last_modelo = modelo_raw

            target_color = _normalize_color(color_raw)
            if target_color is None:
                continue
            cant = _parse_cant(cant_text)
            if last_grupo != "NACIONAL":
                _add_row(resultado, last_sku, "SIN COLOR", "", cant)
            else:
                _add_row(resultado, last_sku, target_color, last_modelo, cant)

        elif n == 2:
            color_raw = texts[0]
            cant_text = texts[1]
            target_color = _normalize_color(color_raw)
            if target_color is None:
                continue
            cant = _parse_cant(cant_text)
            if last_grupo != "NACIONAL":
                _add_row(resultado, last_sku, "SIN COLOR", "", cant)
            else:
                _add_row(resultado, last_sku, target_color, last_modelo, cant)

    return resultado


def _parse_cant(text: str) -> int:
    try:
        return int(float(text.replace(",", "")))
    except (ValueError, TypeError):
        return 0


def _normalize_color(raw: str) -> str | None:
    if not raw:
        return None
    if raw == "S/C":
        return "SIN COLOR"
    return raw


def _is_sm(raw: str) -> bool:
    return raw in ("S/M", "")


def _add_row(
    result: dict[str, list[tuple[str, str, int]]],
    sku: str,
    color: str | None,
    modelo: str,
    cant: int,
):
    if not sku or not color or cant <= 0:
        return
    result.setdefault(sku, []).append((color, modelo, cant))
