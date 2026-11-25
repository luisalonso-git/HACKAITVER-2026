# Contrato de datos v1: HackaITVER 2026, Área 2

Propuesta del 25-nov, 10:30. Si alguien necesita cambiar algo, avisa en el grupo y actualiza este archivo. Todo lo demás se construye sobre esto.

## 1. Evento IoT (simulador o ESP32 → backend)

`POST /api/evento`, `Content-Type: application/json`

```json
{
  "estacion": "E1",
  "tipo": "presencia",
  "magnitud": 0.99,
  "ts": "2026-11-25T11:03:12.345",
  "origen": "simulado"
}
```

| Campo | Valores | Notas |
|---|---|---|
| `estacion` | texto, p. ej. `"E1"` | Identifica la estación de recibo |
| `tipo` | `presencia`, `peso`, `golpe`, `inclinacion` | Ver tabla de abajo |
| `magnitud` | número | La unidad depende del tipo |
| `ts` | ISO 8601 local, sin zona horaria | Hora del evento |
| `origen` | `simulado` o `fisico` | **Obligatorio.** El dashboard debe mostrarlo |

| Tipo | Unidad | Significado |
|---|---|---|
| `presencia` | g | Se colocó un bulto (pico de aceleración ≥ 0.4 g) |
| `peso` | kg | Lectura estable de la celda de carga (simulada: no hay celda) |
| `golpe` | g | Manipulación brusca (pico ≥ 2.5 g). Siempre viene junto con una `presencia` |
| `inclinacion` | grados | Inclinación mayor a 30° sostenida 0.5 s |

Respuestas: `201 {"ok": true, "id": n}` · `400` JSON inválido · `422 {"error": "..."}` contrato incumplido.

`GET /api/eventos` devuelve la lista de eventos recibidos.

## 2. Escaneo de QR (frontend → backend)

`POST /api/escaneo`

```json
{ "codigo": "B-0001", "estacion": "E1", "ts": "2026-11-25T11:03:10.000" }
```

El QR solo contiene el identificador del bulto (`bulto_id`). El backend busca el resto (OC, SKU, cantidad, peso esperado) en la base de datos.

## 3. Cómo se correlaciona una recepción

Una **recepción** = un escaneo de QR + los eventos de la **misma estación** dentro de la ventana `[ts_escaneo − 5 s, ts_escaneo + 20 s]` (configurable).

Chequeos propuestos (los afina la persona de datos y reglas):

| Chequeo | Pasa si… |
|---|---|
| QR válido | El bulto existe en la base y el folio no está repetido |
| Presencia | Hay al menos un evento `presencia` en la ventana |
| Peso | `abs(peso_medido − peso_esperado) / peso_esperado ≤ 5 %` (tolerancia configurable) |
| Manipulación | No hay eventos `golpe` ni `inclinacion` |

Resultado: **OK** si todo pasa, **SOSPECHOSO** si falla alguno. Cada fallo abre una OT.

## 4. Orden de trabajo (OT)

```json
{
  "id": "OT-0012",
  "tipo": "cantidad_distinta",
  "prioridad": "media",
  "causa": "Peso medido 10.05 kg vs esperado 12.50 kg (−19.6 %)",
  "evidencia": [{"tipo": "peso", "magnitud": 10.05, "origen": "simulado"}],
  "bulto_id": "B-0001",
  "estacion": "E1",
  "estado": "abierta",
  "creada_ts": "2026-11-25T11:03:13.000",
  "cerrada_ts": null,
  "comentario": null
}
```

| Campo | Valores |
|---|---|
| `tipo` | `duplicado`, `sin_respaldo_fisico`, `cantidad_distinta`, `dato_incompleto`, `inspeccion` |
| `prioridad` | `baja` (1 fallo), `media` (2 fallos), `alta` (3 o más, o golpe) |
| `estado` | `abierta` → `en_revision` → `cerrada` |

Endpoints: `GET /api/ot` · `PATCH /api/ot/{id}` con `{"estado": "cerrada", "comentario": "..."}` (el humano confirma o descarta).

## 5. Tipos de OT frente a las situaciones de la demo

| Situación | Tipo de OT |
|---|---|
| Mismo folio escaneado dos veces | `duplicado` |
| QR escaneado y ningún evento `presencia` | `sin_respaldo_fisico` |
| Peso fuera de tolerancia | `cantidad_distinta` |
| Fila con costo vacío, SKU inexistente, etc. | `dato_incompleto` |
| `golpe` o `inclinacion` | `inspeccion` |

## 6. Agregados para el frontend (propuesta v1.1, 25-nov 12:30)

No cambian nada de las secciones 1 a 5; solo agregan respuestas y consultas que la pantalla necesita.
Están implementados en `backend_mock/servidor_mock.py`, que sirve de referencia para el backend de FastAPI.

**Respuesta de `POST /api/escaneo`** (201):
```json
{"ok": true, "recepcion_id": 3, "estado": "PENDIENTE", "qr_valido": true, "mensaje": "QR válido",
 "bulto": {"bulto_id": "B-0001", "oc": "OC-1042", "sku": "1001", "descripcion": "Tornillo hexagonal M6x20 (caja)"}}
```
Si el código no existe, `bulto` es `null` y el chequeo de QR falla (OT `dato_incompleto`).

**`GET /api/recepcion/{id}`** y **`GET /api/recepciones`** (la más reciente primero):
```json
{"id": 3, "codigo": "B-0001", "estacion": "E1", "ts": "...", "estado": "PENDIENTE | OK | SOSPECHOSO",
 "mensaje": "QR válido", "bulto": {...},
 "checks": {"qr": "OK", "presencia": "OK", "peso": "PENDIENTE", "manipulacion": "PENDIENTE"},
 "peso_medido_kg": 12.66, "peso_esperado_kg": null, "diferencia_pct": null,
 "eventos": [ ...eventos de la ventana... ], "ots": ["OT-0007"], "cerrada_ts": null}
```
Cada chequeo vale `OK`, `FALLO` o `PENDIENTE`. Recepción ciega: `peso_esperado_kg` y `bulto.cantidad` solo aparecen al cerrar.

Reglas de cierre usadas en el mock:
- Se correlaciona por la **hora en que el servidor recibe** cada mensaje (no por `ts`), para que no afecte si los relojes de las laptops difieren.
- Una recepción se cierra al terminar la ventana (20 s) o antes, si ya hay `presencia` y `peso` y pasan 4 s sin eventos nuevos.
- Un evento que ya usó una recepción no se cuenta en otra.
- Sin lectura de peso = chequeo de peso fallido. Una recepción correcta suma la cantidad del bulto al inventario.

**`GET /api/bultos`**: `[{"bulto_id", "oc", "sku", "descripcion", "cantidad", "peso_kg"}]`

**`GET /api/calidad`** (valores entre 0 y 1):
```json
{"global": {"antes": 0.76, "despues": 0.95}, "total_registros": 1560,
 "por_fuente": [{"fuente": "compras", "total": 420, "antes": 0.81, "despues": 0.97}],
 "hallazgos": {"duplicado": 37, "dato_incompleto": 58, "cantidad_distinta": 24,
               "sin_respaldo_fisico": 0, "inspeccion": 0},
 "recepciones": {"total": 8, "ok": 2, "sospechosas": 6, "pendientes": 0}}
```

**`GET /api/inventario`**: `[{"sku": "1001", "descripcion": "...", "existencia": 1700}]`
