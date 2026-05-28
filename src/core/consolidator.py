from __future__ import annotations

from collections import defaultdict

from .models import (
    Alerta,
    AlertaSeveridad,
    AlertaTipo,
    ColorStock,
    Diseno,
    ProductoConsolidado,
)


def consolidar(
    source1: dict[str, dict],
    source2: dict[str, list[tuple[str, str, int]]],
) -> list[ProductoConsolidado]:
    all_skus = set(source1.keys()) | set(source2.keys())

    # ── Agrupar source2 por SKU → color → modelo ──────────────────────
    # color_totals: {sku: {color: total}}
    # modelo_cants: {(sku, color): [(modelo, cant), ...]}
    color_totals: dict[str, dict[str, int]] = defaultdict(lambda: defaultdict(int))
    modelo_cants: dict[tuple[str, str], list[tuple[str, int]]] = defaultdict(list)

    for sku, tuples in source2.items():
        for color, modelo, cant in tuples:
            color_totals[sku][color] += cant
            modelo_cants[(sku, color)].append((modelo, cant))

    productos: list[ProductoConsolidado] = []

    for sku in sorted(all_skus):
        in_s1 = sku in source1
        in_s2 = sku in source2

        info = source1.get(sku, {})
        stock = info.get("stock", 0) or 0
        predespacho = info.get("predespacho", 0) or 0
        descripcion = info.get("descripcion", "") or ""

        # Fallback: Si Source 1 no tiene descripción, buscar el nombre en el detalle de Source 2
        if not descripcion and in_s2:
            for _, mod, _ in source2[sku]:
                if mod and mod.strip():
                    descripcion = mod
                    break
        
        # Fallback final: Si sigue sin nombre, usar el SKU como referencia
        if not descripcion:
            descripcion = f"ARTÍCULO {sku}"

        modelo_base = info.get("modelo", "") or ""
        disponible = max(0, stock - predespacho)

        colores: list[ColorStock] = []
        suma_colores = 0

        for color_nombre, total in sorted(color_totals.get(sku, {}).items()):
            disenos = [
                Diseno(nombre=m, cantidad=c)
                for m, c in modelo_cants.get((sku, color_nombre), [])
            ]
            if total > 0:
                colores.append(ColorStock(nombre=color_nombre, total=total, disenos=disenos))
                suma_colores += total

        if not colores:
            suma_colores = 0

        alertas = _inferir_alertas(
            stock=stock,
            predespacho=predespacho,
            suma_colores=suma_colores,
            disponible=disponible,
            found_in_s1=in_s1,
            found_in_s2=in_s2
        )

        productos.append(
            ProductoConsolidado(
                sku=sku,
                descripcion=descripcion,
                modelo=modelo_base,
                stock_referencial=stock,
                predespacho_total=predespacho,
                disponible=disponible,
                colores=colores,
                alertas=alertas,
            )
        )

    return productos


def _inferir_alertas(
    stock: int,
    predespacho: int,
    suma_colores: int,
    disponible: int,
    found_in_s1: bool = True,
    found_in_s2: bool = True,
) -> list[Alerta]:
    alertas: list[Alerta] = []

    # ── Verificación de Cruce (Cross-check) ───────────────────────────
    if not found_in_s1:
        alertas.append(
            Alerta(
                tipo=AlertaTipo.REFERENCIA_STOCK_FALTANTE,
                mensaje="SKU no encontrado en reporte de Stock (Source 1)",
                severidad=AlertaSeveridad.ALTA,
            )
        )
    elif not found_in_s2:
        alertas.append(
            Alerta(
                tipo=AlertaTipo.DETALLE_COLOR_FALTANTE,
                mensaje="Sin detalle de colores en Source 2",
                severidad=AlertaSeveridad.INFO,
            )
        )

    if stock == 0 and predespacho > 0:
        alertas.append(
            Alerta(
                tipo=AlertaTipo.SIN_STOCK,
                mensaje=f"Stock 0 con {predespacho} predespachado",
                severidad=AlertaSeveridad.ALTA,
            )
        )

    if predespacho > stock:
        alertas.append(
            Alerta(
                tipo=AlertaTipo.PREDESPACHO_EXCEDE_STOCK,
                mensaje=f"Predespacho ({predespacho}) excede stock ({stock})",
                severidad=AlertaSeveridad.ALTA,
            )
        )

    if suma_colores > stock:
        alertas.append(
            Alerta(
                tipo=AlertaTipo.COLORES_EXCEDEN_STOCK,
                mensaje=f"Suma colores ({suma_colores}) excede stock ({stock})",
                severidad=AlertaSeveridad.BAJA,
            )
        )

    if suma_colores > predespacho and predespacho > 0:
        alertas.append(
            Alerta(
                tipo=AlertaTipo.COLORES_EXCEDEN_STOCK,
                mensaje=f"Colores ({suma_colores}) exceden predespacho ({predespacho})",
                severidad=AlertaSeveridad.BAJA,
            )
        )

    if stock > 0 and disponible == 0:
        alertas.append(
            Alerta(
                tipo=AlertaTipo.DISPONIBLE_CERO,
                mensaje="Stock completamente comprometido",
                severidad=AlertaSeveridad.MEDIA,
            )
        )

    if stock > 0 and disponible > 0 and predespacho > 0:
        alertas.append(
            Alerta(
                tipo=AlertaTipo.DISPONIBLE_CERO,
                mensaje=f"Disponible: {disponible} unidades",
                severidad=AlertaSeveridad.INFO,
            )
        )

    return alertas