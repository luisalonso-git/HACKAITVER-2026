from datetime import datetime, timezone
import sqlite3

DB_PATH = "almacen_hackaitver.db"


def get_conn() -> sqlite3.Connection:
    conn = sqlite3.connect(DB_PATH, check_same_thread=False)
    conn.row_factory = sqlite3.Row
    return conn


def now_iso() -> str:
    return datetime.now(timezone.utc).astimezone().isoformat(timespec="seconds")


def init_db() -> None:
    with get_conn() as conn:
        conn.executescript(
            """
            CREATE TABLE IF NOT EXISTS inventario (
                sku TEXT PRIMARY KEY,
                descripcion TEXT NOT NULL,
                cantidad INTEGER NOT NULL DEFAULT 0,
                peso_unitario_kg REAL NOT NULL DEFAULT 1.0,
                actualizado_en TEXT NOT NULL
            );

            CREATE TABLE IF NOT EXISTS eventos (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                qr_codigo TEXT NOT NULL,
                sku TEXT NOT NULL,
                cantidad INTEGER NOT NULL,
                qr_valido INTEGER NOT NULL,
                presencia_ok INTEGER NOT NULL,
                peso_ok INTEGER NOT NULL,
                peso_kg REAL NOT NULL,
                resultado TEXT NOT NULL,
                ot_id INTEGER,
                origen TEXT NOT NULL,
                creado_en TEXT NOT NULL
            );

            CREATE TABLE IF NOT EXISTS ordenes_trabajo (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                tipo TEXT NOT NULL,
                prioridad TEXT NOT NULL,
                causa TEXT NOT NULL,
                evidencia_json TEXT NOT NULL,
                estado TEXT NOT NULL DEFAULT 'abierta',
                hora TEXT NOT NULL
            );

            CREATE TABLE IF NOT EXISTS calidad_datos (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                fuente TEXT NOT NULL,
                registros_antes INTEGER NOT NULL,
                registros_despues INTEGER NOT NULL,
                duplicados_removidos INTEGER NOT NULL,
                inconsistencias_detectadas INTEGER NOT NULL,
                porcentaje_calidad_antes REAL NOT NULL,
                porcentaje_calidad_despues REAL NOT NULL,
                registrado_en TEXT NOT NULL
            );
            """
        )

        seed_items = [
            ("SKU-001", "Caja tornillería industrial M8", 120, 2.5),
            ("SKU-002", "Sensor inductivo NPN 12V", 45, 0.4),
            ("SKU-003", "Rollo cinta de empaque", 80, 1.2),
        ]
        ts = now_iso()
        for sku, desc, cant, peso in seed_items:
            conn.execute(
                """
                INSERT OR IGNORE INTO inventario (sku, descripcion, cantidad, peso_unitario_kg, actualizado_en)
                VALUES (?, ?, ?, ?, ?)
                """,
                (sku, desc, cant, peso, ts),
            )
        conn.commit()
        
if __name__ == "__main__":
    init_db()
    print("Base creada:", DB_PATH)
