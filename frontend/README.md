# Kardex Vivo · Frontend (Streamlit)

Tres pantallas: **Recepción** (operador), **Órdenes de trabajo** y **Dashboard**.
Funciona sin backend en modo simulado (`USAR_MOCK = True` en `config.py`).

## Arranque

```
cd frontend
pip install -r requirements.txt
streamlit run app.py
```

Streamlit muestra dos direcciones: `Local URL` (para la laptop) y `Network URL` (para el celular).
Copia la `Network URL` en `FRONT_URL` de `config.py` y genera los QR:

```
python generar_qr.py
```

Todos los dispositivos deben estar en la misma red (hotspot del equipo).
Si el celular no abre la página, permite Python en el firewall de Windows (red privada).

## Estructura

| Archivo | Qué hace |
|---|---|
| `app.py` | Menú y navegación |
| `config.py` | Modo simulado, URL del backend, IP del frontend, estación |
| `api.py` | Única puerta hacia el backend; las páginas solo llaman a estas funciones |
| `mock_api.py` | Backend simulado con los escenarios de demo |
| `utils.py` | Lectura del QR y nombres legibles |
| `paginas/*.py` | Las pantallas |
| `generar_qr.py` | QR con URL para escanear con la cámara del celular |

## Escenarios de demo (modo simulado)

| QR | Resultado |
|---|---|
| KV-1042-1001-0001 | Correcto; escanearlo otra vez = duplicado |
| KV-1042-1002-0002 | Peso 18 % menor, OT de diferencia de cantidad |
| KV-1043-1003-0003 | Sin producto, OT de prioridad alta |
| KV-9999-1001-0001 | Orden de compra inexistente, OT de prioridad alta |

## Cambiar al backend real

1. En `config.py`: `USAR_MOCK = False` y `API_URL = "http://IP-del-backend:8000"`.
2. El backend debe responder con estos formatos (pásaselos a la persona 1).
   Streamlit llama a la API desde Python, no desde el navegador, así que no hace falta CORS.

### POST /api/recepcion/scan
Entrada: `{"qr": "KV-1042-1001-0001", "estacion": "EST01"}`
```json
{"recepcion_id": 17, "estado": "PENDIENTE", "qr_valido": true, "mensaje": "QR válido",
 "orden_compra": "1042", "articulo": "1001", "lote": "0001",
 "descripcion": "Tornillo hexagonal M6x20"}
```

### GET /api/recepcion/{id}
`estado`: PENDIENTE | OK | SOSPECHOSO. Cada check: OK | FALLO | PENDIENTE.
Mientras está PENDIENTE, `cantidad_esperada` y `peso_esperado_kg` van en `null` (recepción ciega).
```json
{"recepcion_id": 17, "estado": "SOSPECHOSO",
 "checks": {"qr": "OK", "presencia": "OK", "peso": "FALLO"},
 "orden_compra": "1042", "articulo": "1002", "lote": "0002",
 "descripcion": "Rondana plana 1/4", "mensaje": "QR válido",
 "peso_kg": 1.64, "peso_esperado_kg": 2.0,
 "cantidad_calculada": 820, "cantidad_esperada": 1000, "ot_id": "OTV-0005"}
```

### GET /api/ot
Lista de OT de validación con el esquema del contrato
(`ot_id, tipo, prioridad, causa, evidencia, origen, referencias, estado, asignado_a, creada, cerrada, resolucion`).

### PATCH /api/ot/{ot_id}
Entrada: `{"estado": "CERRADA", "resolucion": "Se recontó, faltaban 180 piezas"}`. Devuelve la OT actualizada.

### GET /api/calidad
Valores de calidad entre 0 y 1.
```json
{"global": {"antes": 0.76, "despues": 0.95}, "total_registros": 1560,
 "por_fuente": [{"fuente": "compras", "total": 420, "antes": 0.81, "despues": 0.97}],
 "hallazgos": {"DUPLICADO": 37, "REGISTRO_INCOMPLETO": 58, "DIFERENCIA_CANTIDAD": 24,
               "INCONSISTENCIA_COSTO": 11, "RECEPCION_SOSPECHOSA": 2}}
```

### GET /api/inventario
```json
[{"articulo": "1001", "descripcion": "Tornillo hexagonal M6x20", "existencia": 1700}]
```
