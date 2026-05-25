# Business Rules - Stock Color Consolidator

## Data Sources

### Source 1 - Stock ERP (API directa)
- URL: `http://appweb.cipsa.com.pe:8054/AlmacenStock/DownLoadFiles`
- Formato: XLSX
- Columnas: SKU | Stock Total
- Proposito: Stock referencial "foto del momento"
- Precision: EXACTA (dato contable)

### Source 2 - Predespacho (Web App)
- URL: `http://appweb.cipsa.com.pe:9091/`
- Formato: XLS (puede requerir reparacion)
- Columnas: SKU | Color | Diseno | Cantidad
- Proposito: Desglose de cantidades comprometidas por color y diseno
- Precision: ESTIMADA (dato informativo de planeamiento)

## Reglas de Consolidacion

### Calculo de Disponible
```
disponible = max(0, stock_referencial - predespacho_total)
```
- `disponible` NUNCA es negativo (se clamp a 0)
- `predespacho_total` = suma de todas las cantidades en Source 2 para ese SKU

### Alertas

| Condicion | Severidad | Mensaje |
|---|---|---|
| stock = 0 y predespacho > 0 | ALTA | "Stock 0 con N predespachado" |
| predespacho > stock | ALTA | "Predespacho (N) excede stock (M)" |
| suma colores > stock | MEDIA | "Suma colores (N) excede stock (M)" |
| stock > 0 y disponible = 0 | MEDIA | "Stock completamente comprometido" |
| disponible > 0 | INFO (si hay predespacho) | "Disponible: N unidades" |

### Reglas de Color
- Los colores son INFORMATIVOS y FLEXIBLES
- No afectan el calculo de disponible
- Si suma_colores > stock, se muestra alerta pero no se bloquea nada
- Sirven para planeamiento de produccion (que colores/disenos fabricar)

### Datos por SKU
- Un SKU puede tener 0, 1 o varios colores
- Un color puede tener 0, 1 o varios disenos
- Sin diseno = cantidad base del color

### Interpretacion de Resultados
- `disponible = 0` + colores surtidos = evaluar nueva produccion
- `predespacho > stock` = posible sobreventa o error de etiquetas
- `colores > stock` = posible error en cantidades de colores
