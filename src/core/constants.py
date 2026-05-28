"""Constantes centralizadas del proyecto G360 Stock Consolidator."""
from __future__ import annotations


# Almacenes
WAREHOUSE_PRINCIPAL = "VES"
WAREHOUSE_KPI = "121"  # Almacén usado en KPI de filtro

# URLs
SOURCE1_DEFAULT_URL = (
    'http://appweb.cipsa.com.pe:8054/AlmacenStock/DownLoadFiles'
    '?value={"linea":"0101","parametroX2":"","parametroX1":"0"}'
)
SOURCE2_DEFAULT_URL = "http://appweb.cipsa.com.pe:9091/"

# UI
PAGE_SIZE = 50
WINDOW_WIDTH = 960
WINDOW_HEIGHT = 780
WINDOW_MIN_WIDTH = 720
WINDOW_MIN_HEIGHT = 600

# Colores de botones header
BTN_S1_COLOR = "#1B3A5C"
BTN_S1_HOVER = "#244b75"
BTN_S2_COLOR = "#2C3E50"
BTN_S2_HOVER = "#34495e"

# Logging / temp
TEMP_DIR_PREFIX = "g360_s2_"

# Colores
COLOR_SIN_COLOR = "SIN COLOR"
COLOR_SIN_COLOR_ABBR = "S/C"
MODELO_SIN_MODELO = "S/M"

# Export
REPORT_FILENAME_PREFIX = "reporte_stock_colores_"
REPORT_FILENAME_FORMAT = "%d%m%Y"