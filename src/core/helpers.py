from __future__ import annotations


def producto_tiene_traslado(p, source1_raw, warehouse_disp_fn) -> bool:
    if warehouse_disp_fn("121", p.sku) > 0:
        return True
    vd = warehouse_disp_fn("VES", p.sku)
    return any(
        warehouse_disp_fn(code, p.sku) > vd
        for code in source1_raw
        if code not in ("VES", "121")
    )


def warehouse_order_for_traslados(products, source1_raw, warehouse_disp_fn) -> list[str]:
    wh_totals: dict[str, int] = {}
    for p in products:
        vd = warehouse_disp_fn("VES", p.sku)
        for code in source1_raw:
            if code in ("VES", "121"):
                continue
            d = warehouse_disp_fn(code, p.sku)
            if d > vd:
                wh_totals[code] = wh_totals.get(code, 0) + d
    return [c for c, _ in sorted(wh_totals.items(), key=lambda x: -x[1])]
