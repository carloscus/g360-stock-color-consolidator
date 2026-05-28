from __future__ import annotations
from dataclasses import dataclass, field
from enum import Enum


class AlertaSeveridad(str, Enum):
    ALTA = "alta"
    MEDIA = "media"
    BAJA = "baja"
    INFO = "info"


class AlertaTipo(str, Enum):
    PREDESPACHO_EXCEDE_STOCK = "predespacho_excede_stock"
    COLORES_EXCEDEN_STOCK = "colores_exceden_stock"
    SIN_STOCK = "sin_stock"
    DISPONIBLE_CERO = "disponible_cero"
    REFERENCIA_STOCK_FALTANTE = "referencia_stock_faltante"
    DETALLE_COLOR_FALTANTE = "detalle_color_faltante"


@dataclass
class Diseno:
    nombre: str
    cantidad: int


@dataclass
class ColorStock:
    nombre: str
    total: int
    disenos: list[Diseno] = field(default_factory=list)


@dataclass
class Alerta:
    tipo: AlertaTipo
    mensaje: str
    severidad: AlertaSeveridad


@dataclass
class ProductoConsolidado:
    sku: str
    descripcion: str
    stock_referencial: int
    predespacho_total: int
    disponible: int
    modelo: str = ""
    colores: list[ColorStock] = field(default_factory=list)
    alertas: list[Alerta] = field(default_factory=list)
