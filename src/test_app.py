from __future__ import annotations

import unittest
from src.core.models import (
    ProductoConsolidado, ColorStock, Diseno, Alerta,
    AlertaTipo, AlertaSeveridad,
)
from src.core.consolidator import consolidar, _inferir_alertas


def s1(**kw):
    return {k: {"stock": v.get("stock", 0), "predespacho": v.get("predespacho", 0), "descripcion": v.get("descripcion", "")} for k, v in kw.items()}


class TestModels(unittest.TestCase):
    def test_diseno_creation(self):
        d = Diseno(nombre="Fresa", cantidad=15)
        self.assertEqual(d.nombre, "Fresa")
        self.assertEqual(d.cantidad, 15)

    def test_color_stock_with_disenos(self):
        d = Diseno(nombre="Fresa", cantidad=15)
        c = ColorStock(nombre="Rojo", total=30, disenos=[d])
        self.assertEqual(c.nombre, "Rojo")
        self.assertEqual(c.total, 30)
        self.assertEqual(len(c.disenos), 1)

    def test_producto_consolidado_defaults(self):
        p = ProductoConsolidado(
            sku="012230",
            descripcion="PELOTA",
            stock_referencial=180,
            predespacho_total=170,
            disponible=10,
        )
        self.assertEqual(p.colores, [])
        self.assertEqual(p.alertas, [])


class TestConsolidator(unittest.TestCase):
    def test_basic_consolidation(self):
        s1_data = s1(**{"012230": {"stock": 180, "predespacho": 170}})
        s2_data = {"012230": [("Rojo", "Fresa", 15), ("Rojo", "Oso", 15), ("Verde", "Perrito", 30)]}

        result = consolidar(s1_data, s2_data)
        self.assertEqual(len(result), 1)
        p = result[0]
        self.assertEqual(p.sku, "012230")
        self.assertEqual(p.stock_referencial, 180)
        self.assertEqual(p.predespacho_total, 170)
        self.assertEqual(p.disponible, 10)

    def test_disponible_never_negative(self):
        s1_data = s1(**{"012230": {"stock": 50, "predespacho": 60}})
        s2_data = {}
        result = consolidar(s1_data, s2_data)
        self.assertEqual(result[0].disponible, 0)
        self.assertNotEqual(result[0].disponible, -10)

    def test_colores_exceden_predespacho_alerta(self):
        s1_data = s1(**{"012230": {"stock": 50, "predespacho": 30}})
        s2_data = {"012230": [("Rojo", "", 30), ("Verde", "", 40)]}
        result = consolidar(s1_data, s2_data)
        p = result[0]
        tipos = [a.tipo for a in p.alertas]
        self.assertIn(AlertaTipo.COLORES_EXCEDEN_STOCK, tipos)

    def test_predespacho_excede_stock_alerta(self):
        s1_data = s1(**{"012230": {"stock": 50, "predespacho": 60}})
        s2_data = {}
        result = consolidar(s1_data, s2_data)
        p = result[0]
        tipos = [a.tipo for a in p.alertas]
        self.assertIn(AlertaTipo.PREDESPACHO_EXCEDE_STOCK, tipos)

    def test_multiple_skus(self):
        s1_data = s1(**{"A": {"stock": 100}, "B": {"stock": 200}})
        s2_data = {"A": [("Rojo", "", 30)], "B": [("Azul", "", 50)]}
        result = consolidar(s1_data, s2_data)
        self.assertEqual(len(result), 2)
        skus = [p.sku for p in result]
        self.assertIn("A", skus)
        self.assertIn("B", skus)

    def test_sku_only_in_source2(self):
        s1_data = {}
        s2_data = {"X": [("Rojo", "", 10)]}
        result = consolidar(s1_data, s2_data)
        self.assertEqual(len(result), 1)
        self.assertEqual(result[0].stock_referencial, 0)
        self.assertEqual(result[0].predespacho_total, 0)

    def test_sku_only_in_source1(self):
        s1_data = s1(**{"X": {"stock": 100}})
        s2_data = {}
        result = consolidar(s1_data, s2_data)
        self.assertEqual(len(result), 1)
        self.assertEqual(result[0].stock_referencial, 100)
        self.assertEqual(result[0].predespacho_total, 0)
        self.assertEqual(result[0].colores, [])

    def test_color_grouping_with_modelo(self):
        s1_data = s1(**{"012230": {"stock": 200, "predespacho": 60}})
        s2_data = {"012230": [
            ("Rojo", "Fresa", 15),
            ("Rojo", "Oso", 15),
            ("Verde", "Perrito", 30),
            ("Verde", "Avion", 30),
        ]}
        result = consolidar(s1_data, s2_data)
        p = result[0]
        self.assertEqual(len(p.colores), 2)
        rojo = next(c for c in p.colores if c.nombre == "Rojo")
        self.assertEqual(rojo.total, 30)
        self.assertEqual(len(rojo.disenos), 2)
        self.assertEqual(rojo.disenos[0].nombre, "Fresa")
        self.assertEqual(rojo.disenos[1].nombre, "Oso")


class TestAlertas(unittest.TestCase):
    def test_sin_stock_con_predespacho(self):
        alertas = _inferir_alertas(0, 10, 10, 0)
        self.assertTrue(any(a.tipo == AlertaTipo.SIN_STOCK for a in alertas))

    def test_disponible_cero_alerta(self):
        alertas = _inferir_alertas(100, 100, 100, 0)
        self.assertTrue(any(a.tipo == AlertaTipo.DISPONIBLE_CERO for a in alertas))

    def test_no_alertas_con_disponible(self):
        alertas = _inferir_alertas(100, 50, 50, 50)
        self.assertFalse(any(a.severidad in (AlertaSeveridad.ALTA, AlertaSeveridad.MEDIA) for a in alertas))


if __name__ == "__main__":
    unittest.main()
