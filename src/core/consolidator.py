from __future__ import annotations

import pandas as pd

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
    s1_rows = [
        {"sku": sku, "stock": info.get("stock", 0),
         "predespacho": info.get("predespacho", 0),
         "descripcion": info.get("descripcion", "")}
        for sku, info in source1.items()
    ]
    s1_df = pd.DataFrame(s1_rows)
    if not s1_rows:
        s1_df = pd.DataFrame(columns=["sku", "stock", "predespacho", "descripcion"])

    s2_rows = [
        {"sku": sku, "color": color, "modelo": modelo, "cantidad": cant}
        for sku, tuples in source2.items()
        for color, modelo, cant in tuples
    ]
    s2_df = pd.DataFrame(s2_rows)
    if not s2_rows:
        s2_df = pd.DataFrame(columns=["sku", "color", "modelo", "cantidad"])

    if s2_df.empty:
        sku_colores = pd.DataFrame(columns=["sku", "color", "total"])
        sku_modelos = pd.DataFrame(columns=["sku", "color", "modelo", "cantidad"])
        sku_totals = pd.DataFrame(columns=["sku", "suma_colores"])
    else:
        sku_modelos = (
            s2_df.groupby(["sku", "color", "modelo"], as_index=False)["cantidad"]
            .sum()
        )
        sku_colores = (
            s2_df.groupby(["sku", "color"], as_index=False)["cantidad"]
            .sum()
            .rename(columns={"cantidad": "total"})
        )
        sku_totals = (
            s2_df.groupby("sku", as_index=False)["cantidad"]
            .sum()
            .rename(columns={"cantidad": "suma_colores"})
        )

    all_skus = set(source1.keys()) | set(source2.keys())
    all_df = pd.DataFrame({"sku": list(all_skus)})

    merged = (
        all_df
        .merge(s1_df, on="sku", how="left")
        .merge(sku_totals, on="sku", how="left")
        .fillna({"stock": 0, "predespacho": 0, "descripcion": "", "suma_colores": 0})
    )
    merged["stock"] = merged["stock"].astype(int)
    merged["predespacho"] = merged["predespacho"].astype(int)
    merged["suma_colores"] = merged["suma_colores"].astype(int)
    merged["disponible"] = (merged["stock"] - merged["predespacho"]).clip(lower=0)

    color_map = {}
    if not sku_colores.empty:
        for _, row in sku_colores.iterrows():
            color_map.setdefault(row["sku"], []).append(
                {"nombre": row["color"], "total": int(row["total"])}
            )
    modelo_map = {}
    if not sku_modelos.empty:
        for _, row in sku_modelos.iterrows():
            modelo_map.setdefault((row["sku"], row["color"]), []).append(
                {"nombre": row["modelo"] or "S/M", "cantidad": int(row["cantidad"])}
            )

    productos = []
    for _, row in merged.iterrows():
        sku = row["sku"]
        stock = int(row["stock"])
        predespacho = int(row["predespacho"])
        disponible = int(row["disponible"])
        descripcion = str(row["descripcion"])
        suma_colores = int(row["suma_colores"])

        colores = []
        for cinfo in color_map.get(sku, []):
            key = (sku, cinfo["nombre"])
            disenos = [
                Diseno(nombre=m["nombre"], cantidad=m["cantidad"])
                for m in modelo_map.get(key, [])
            ]
            colores.append(
                ColorStock(
                    nombre=cinfo["nombre"],
                    total=cinfo["total"],
                    disenos=disenos,
                )
            )

        alertas = _inferir_alertas(stock, predespacho, suma_colores, disponible)

        productos.append(
            ProductoConsolidado(
                sku=sku,
                descripcion=descripcion,
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
) -> list[Alerta]:
    alertas: list[Alerta] = []

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
