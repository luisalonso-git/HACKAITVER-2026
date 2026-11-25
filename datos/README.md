# datos/: fuentes de información con errores

## Paso 1 (listo): CSV sucios

`python generar_csv.py` crea en `crudos/` (siempre los mismos, semilla fija):

| Archivo | Qué contiene | Registros |
|---|---|---|
| `compras.csv` | Líneas de órdenes de compra: OC, proveedor, SKU, cantidad, precio, factura | 99 |
| `almacen.csv` | Entradas (por OC) y salidas (por OT operativa) | 149 |
| `costos.csv` | Costo vigente por SKU | 11 |
| `ot_operativas.csv` | Órdenes de mantenimiento que consumen material | 63 |
| `catalogo.csv` | SKU válidos (referencia limpia) | 10 |
| `errores_sembrados.json` | Hoja de respuestas: archivo, línea y tipo de cada error | 69 errores |

Las OC-1042 a OC-1046 están en tránsito: no tienen entrada en almacén porque se reciben en la estación IoT
(son los bultos B-0001 a B-0006 del backend).

## Errores sembrados

| Categoría | Ejemplos | Cuántos | Qué hará el motor |
|---|---|---|---|
| `dato_incompleto` | Campo vacío, SKU 9999, OC inexistente, cantidad 0 o negativa | 23 | Abre OT |
| `formato` | Fecha dd/mm/aaaa, mayúsculas y espacios, estado "CERRADA ", costo en USD | 16 | Corrige solo |
| `duplicado` | Copia exacta, misma compra con otra descripción, OT repetida, costo doble | 14 | Abre OT |
| `cantidad_distinta` | Entrada menor que la compra, salida mayor que el consumo de la OT | 8 | Abre OT |
| `costo_distinto` | Precio fuera de ±10 % del costo vigente, costo de OT que no cuadra | 8 | Abre OT |

La línea de cada error cuenta el encabezado como línea 1, igual que Excel.
