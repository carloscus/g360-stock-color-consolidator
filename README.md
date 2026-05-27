# G360 Stock Color Consolidator

Consolida stock de colores desde el ERP (appweb.cipsa.com.pe) y genera reportes XLSX profesionales con disponibilidad por almacén y desglose por color/modelo.

## Características

- **Descarga automática** desde ERP (Source 1 + Source 2 vía Playwright)
- **Carga manual** de archivos .xls/.xlsx (cuando no hay acceso al ERP)
- **Consolidación** de stock, predespacho y colores por SKU
- **Reporte XLSX** con dos hojas: "Con Color" y "Sin Color", con stock por almacén
- **Dashboard interactivo** con filtros por SKU, alertas, almacén y tipo de color
- **Progreso en vivo** durante la descarga (cada paso se muestra en la interfaz)
- **Confirmación de re-descarga** para evitar descargas innecesarias
- **Limpieza automática** de archivos temporales después del procesamiento
- **Credenciales seguras**: la contraseña solo vive en memoria durante la sesión
- **Sin dependencias nativas**: no requiere Cairo/GTK ni VC++ Redistributable (Flet incluye sus propios DLLs)
- **Flet pinneado a 0.21.2**: evita breaking changes de versiones superiores

## Requisitos

- Windows 10/11
- Python 3.10+
- Navegador Chromium (Playwright lo instala automáticamente)
- Conexión a internet (solo la primera vez para dependencias)

## Instalación (desarrollo)

```bash
git clone https://github.com/carloscus/g360-stock-color-consolidator.git
cd g360-stock-consolidator

# Opción A: con uv (recomendado)
uv venv .venv --python 3.10 --seed
.venv\Scripts\activate
uv pip install -r requirements.txt

# Opción B: con pip estándar
python -m venv .venv
.venv\Scripts\activate
pip install -r requirements.txt

# Playwright browser
playwright install chromium
```

> **Nota:** `flet==0.21.2` y `playwright==1.60.0` están pinneados en `requirements.txt` para evitar breaking changes.

## Configuración

Copie `.env.example` como `.env` y ajuste los valores para su red local:

```env
G360_S2_URL=http://appweb.cipsa.com.pe:9091/
```

Si no usa `.env`, las variables se pueden definir como variables de entorno del sistema.

## Uso

```bash
python run.py
```

### Flujo típico

1. **Credenciales**: al abrir la app, ingrese usuario y contraseña del ERP (la contraseña no se guarda)
2. **Descargar Source 1**: stock general desde el servidor HTTP
3. **Descargar Source 2**: colores por SKU desde el ERP (automático con Playwright)
4. **Explorar datos**: filtre por SKU, alertas, almacenes o tipo de color
5. **Descargar reporte XLSX**: genera el consolidado en Excel

### Manejo de errores de credenciales

Si el login al ERP falla, el diálogo de error ofrece tres opciones:

- **Cargar manualmente** → abre el selector de archivos para elegir un XLS descargado previamente
- **Cambiar credenciales** → abre el diálogo para corregir usuario/contraseña
- **OK** → cierra el mensaje para reintentar manualmente

### Carga manual

Si no tiene acceso al ERP, use el botón 📂 para cargar manualmente un archivo
`STOCK_MODELO_COLOR.xls` exportado previamente.

## Versión Portable

Para usuarios sin Python instalado, use la carpeta `g360-stock-consolidator-portable/`:

```
g360-stock-consolidator-portable/
├── run.bat              ← Doble clic para ejecutar (auto-instala todo)
├── run.py
├── requirements.txt
├── pyproject.toml
├── create_shortcut.vbs
├── INSTRUCCIONES.txt
└── src/
```

La primera ejecución:
1. Descarga **uv** portable desde GitHub (ZIP directo, sin `iex`)
2. Crea entorno virtual con **Python 3.10**
3. Instala dependencias (flet 0.21.2, playwright 1.60.0, requests, etc.)
4. Descarga **Chromium** (con hasta 3 reintentos automáticos)
5. Verifica la importación de todos los paquetes antes de lanzar la app

`run.bat` se auto-minimiza al iniciar, muestra un log discreto con 5 pasos, y se cierra automáticamente cuando la app finaliza. Si hay errores, la ventana se pausa y se puede revisar `run_log.txt`.

## Arquitectura

```
src/
├── main.py                    # Punto de entrada, orquestación
├── config/
│   └── theme.py               # Paleta de colores (modo claro/oscuro)
├── core/
│   ├── parsers.py             # Parseo de HTML .xls del ERP
│   ├── consolidator.py        # Consolidación stock + colores (pandas)
│   ├── browser_automation.py  # Automatización Playwright (login + descarga)
│   ├── downloader.py          # Descarga Source 1 vía HTTP
│   ├── models.py              # Dataclasses (Producto, Color, Alerta)
│   └── xls_fallback.py        # Lector legacy .xls con xlrd
└── ui/
    ├── dashboard.py           # Componentes de la interfaz Flet
    ├── sku_detail.py          # Modal detalle de producto
    └── logo.py                # Logo G360 en base64
```

## Stack

| Capa | Tecnologia |
|------|-----------|
| UI | Flet (Python -> Flutter, logo PNG base64 embebido) |
| Automatizacion | Playwright (Chromium) |
| Procesamiento | pandas, openpyxl |
| Parseo HTML | BeautifulSoup4, lxml |
| Legacy .xls | xlrd |
| Launcher portable | uv (auto-descarga), sin dependencias nativas DLL |

---

## 🌐 Familia G360

Este proyecto forma parte de la familia de microherramientas **G360** para apoyo CRM y gestion de datos en escritorio, enfocadas en areas como ventas, finanzas y logistica.

### Identidad Visual G360

- **Isotipo**: 3 puntos verticales paralelos (gris-verde-gris) + chevron `>`
- **Tipografia**: Monospace, uppercase para "G360"
- **Marca**: G360 (no "G360 Ecosystem")
- **Enfoque**: Microherramientas para apoyo CRM y datos en escritorio
- **Familia**: Herramientas por area (Ventas, Finanzas, Logistica)

---

## Licencia

MIT License

---

**Marca**: G360
**Isotipo**: 3 puntos verticales paralelos (gris-verde-gris) + chevron `>`
**Autor**: Carlos Cusi
**Desarrollo**: Con asistencia de herramientas de codigo IA (Vibe Code)
**Powered by**: [g360-signature](https://github.com/carloscus/g360-signature)

