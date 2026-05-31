# G360 Stock Color Consolidator — Portable v1.1.0

Consolida stock de colores desde el ERP de CIPSA y exporta a XLSX.

## Uso rapido

1. Haga doble clic en `run.bat`
2. La primera vez se auto-instala Python + dependencias (requiere internet)
3. Ingrese credenciales del ERP y descargue los datos
4. Explore y exporte a Excel

## Archivos importantes

| Archivo | Propósito |
|--------|----------|
| `run.bat` | Lanzador principal (doble clic) |
| `.env` | Configuración de red local (URL del ERP) |
| `.env.example` | Plantilla para crear `.env` |
| `run_log.txt` | Bitácora de errores (se genera al ejecutar) |
| `INSTRUCCIONES.txt` | Manual de usuario detallado |

## Estructura del proyecto

```
g360-stock-consolidator/
├── run.bat                  # Lanzador principal
├── run.py                   # Entry point de la app Flet
├── requirements.txt         # Dependencias Python
├── pyproject.toml           # Configuración del proyecto
├── src/
│   ├── main.py              # Orquestación principal de la app
│   ├── config/
│   │   ├── __init__.py
│   │   └── theme.py         # Paletas de colores (LIGHT/DARK)
│   ├── core/
│   │   ├── __init__.py
│   │   ├── constants.py     # Constantes centralizadas
│   │   ├── models.py        # Modelos de datos (dataclasses)
│   │   ├── consolidator.py  # Lógica de consolidación stock+colores
│   │   ├── parsers.py       # Parsers de Source 1 y Source 2
│   │   ├── downloader.py    # Descarga HTTP de Source 1
│   │   ├── browser_automation.py  # Automatización Playwright para Source 2
│   │   ├── xls_fallback.py  # Motor multi-formato para leer XLS
│   │   ├── errors.py        # Mensajes de error amigables
│   │   └── report.py        # Generación de reportes XLSX
│   ├── ui/
│   │   ├── __init__.py
│   │   ├── dashboard.py     # Interfaz principal (Flet)
│   │   ├── sku_detail.py    # Modal de detalle por SKU
│   │   └── logo.py          # Logos en base64
│   └── test_app.py          # Tests unitarios
├── assets/
│   └── images/              # Logos e íconos
└── samples/                 # Archivos de prueba
```

## Requisitos

- Windows 10/11
- Conexión a internet (solo primera ejecución)
- Red local CIPSA para acceder al ERP

Para más detalles, lea `INSTRUCCIONES.txt`.
