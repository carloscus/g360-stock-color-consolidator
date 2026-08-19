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



