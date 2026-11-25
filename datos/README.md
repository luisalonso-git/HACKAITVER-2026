# datos/: fuentes del equipo y motor de limpieza

| Carpeta / archivo | Qué es |
|---|---|
| `fuentes/` | Datos del equipo: `compras.csv` (22), `almacen.csv` (19), `ordenes_trabajo.csv` (14) y la hoja de respuestas `errores_sembrados.csv` (23 errores) |
| `equipo/` | Scripts originales del compañero de datos (`limpieza.py`, `Reporte de errores.py`, `database.py`, `leer hojas de productos.py`), sin cambios |
| `motor_limpieza.py` | Motor integrado: usa la misma normalización de `equipo/limpieza.py` y agrega lo que faltaba para conectarlo |

```
python motor_limpieza.py        # resumen en pantalla y archivos en salida/
```

## Qué agrega el motor al trabajo del equipo

- Cada hallazgo queda anotado: archivo, línea, folio, campo, valor, regla y acción.
- **Formato** (fecha dd/mm/aaaa, mayúsculas, espacios) se corrige solo; todo lo demás abre una orden de trabajo.
- Duplicados aunque cambie el folio o las mayúsculas (casi duplicados).
- Cruce **registro por registro** entre compras y entradas de almacén (mismo SKU, 0 a 3 días): señala exactamente
  qué entrada no cuadra (M005, M012) y qué compra no llegó (C021), en lugar de solo totales por SKU.
- Evaluación contra `errores_sembrados.csv`: **23 de 23 detectados, ninguno fuera de la hoja**.
- Reporte para Excel con el formato de `Reporte de errores.py` (separador `;`, acentos correctos).

## Cómo se usa en el sistema

El `backend_mock` llama a `analizar()` al arrancar: cada hallazgo es una OT, la calidad "antes" sale de los datos
crudos y sube en vivo al cerrar OT. La compra C021 (sin recepción) es el bulto **B-0001** de la estación IoT:
al recibirlo correctamente, su OT se cierra sola.
