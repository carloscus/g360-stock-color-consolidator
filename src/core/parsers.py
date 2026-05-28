from __future__ import annotations

from src.core.xls_fallback import leer_xls_fallback


def parse_source1_all(path: str) -> dict[str, dict[str, dict]]:
    filas = leer_xls_fallback(path)
    if not filas:
        return {}

    resultado: dict[str, dict[str, dict]] = {}
    last_sku, last_desc = "", ""

    # Reversión: Uso de posiciones fijas y omisión de las primeras 10 filas (metadatos)
    for row in filas[10:]:
        if len(row) < 17:
            continue
            
        r_sku = str(row[1] or "").strip().lstrip("'")
        r_desc = str(row[2] or "").strip()
        r_sku_upper = r_sku.upper()

        # 1. Detectar fin de bloque o filas de sistema para resetear el 'sticky'
        if r_sku_upper in ("TOTAL", "SUBTOTAL", "TOTAL GENERAL"):
            last_sku = ""
            continue

        # 2. Lógica Sticky: Solo actualizar si hay un nuevo SKU válido
        if r_sku and r_sku_upper not in (".", "ARTÍCULO", "ARTICULO"):
            last_sku = r_sku
            last_desc = r_desc
        
        # 3. Si no tenemos un SKU de referencia (celda vacía y sin 'last_sku'), ignorar
        if not last_sku:
            continue

        almacen_raw = str(row[9] or "").strip().upper()
        stock_raw = str(row[13] or "0").strip()
        pred_raw = str(row[16] or "0").strip() if len(row) > 16 else "0"

        try:
            stock = int(float(stock_raw.replace(",", "")))
            pred = int(float(pred_raw.replace(",", ""))) if pred_raw else 0
        except (ValueError, TypeError, AttributeError):
            continue

        almacen_row = resultado.setdefault(almacen_raw, {})
        if last_sku not in almacen_row:
            almacen_row[last_sku] = {"stock": 0, "predespacho": 0, "descripcion": last_desc}
        almacen_row[last_sku]["stock"] += stock
        almacen_row[last_sku]["predespacho"] += pred

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

        if n <= 1:
            continue

        last_is_td = tags[-1] == "td"
        if not last_is_td:
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
            if modelo_raw:
                last_modelo = "" if modelo_raw in ("S/M", "") else modelo_raw

            target_color = _normalize_color(color_raw)
            if target_color is None:
                continue
            
            cant = _parse_cant(cant_text)

            # Validación extra: No procesar si no hay SKU de referencia
            if not last_sku:
                continue
                
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
            _add_row(resultado, last_sku, target_color, last_modelo, cant)

        elif n == 2:
            color_raw = texts[0]
            cant_text = texts[1]
            target_color = _normalize_color(color_raw)
            if target_color is None:
                continue
            cant = _parse_cant(cant_text)
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
