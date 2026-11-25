# -*- coding: utf-8 -*-
"""
Created on Wed Nov 25 13:02:33 2026

@author: iende
"""

# -*- coding: utf-8 -*-
"""
Genera un reporte CSV (compatible con Excel) con los errores y discrepancias
detectados en compras, almacén, OT históricas y eventos en tiempo real.
"""

from pathlib import Path
import sqlite3
import pandas as pd

DB_PATH = "almacen_hackaitver.db"
OUT_FILE = Path("reporte_errores_excel.csv")


def normalizar_sku(serie: pd.Series) -> pd.Series:
    s = serie.astype("string").str.strip().str.upper()
    return s.replace({"": pd.NA, "NAN": pd.NA, "NONE": pd.NA, "NULL": pd.NA})


def normalizar_fecha_valida(serie: pd.Series) -> pd.Series:
    """Devuelve True donde la fecha es válida (aaaa-mm-dd o dd/mm/aaaa)."""
    s = serie.astype("string").str.strip()
    f1 = pd.to_datetime(s, format="%Y-%m-%d", errors="coerce")
    f2 = pd.to_datetime(s, format="%d/%m/%Y", errors="coerce")
    return f1.notna() | f2.notna()


def agregar_error(
    errores: list[dict],
    fuente: str,
    fila_origen: int,
    sku: object,
    campo: str,
    valor_actual: object,
    tipo_error: str,
    detalle: str,
) -> None:
    errores.append(
        {
            "fuente": fuente,
            "fila_origen": fila_origen,
            "sku": "" if pd.isna(sku) else str(sku),
            "campo": campo,
            "valor_actual": "" if pd.isna(valor_actual) else str(valor_actual),
            "tipo_error": tipo_error,
            "detalle": detalle,
        }
    )


def auditar_compras(df: pd.DataFrame, errores: list[dict]) -> None:
    for idx, row in df.iterrows():
        fila = idx + 2  # +2 considerando encabezado en fila 1 de CSV
        sku = normalizar_sku(pd.Series([row.get("sku", pd.NA)])).iloc[0]

        if pd.isna(sku):
            agregar_error(errores, "compras", fila, sku, "sku", row.get("sku"), "DATO_FALTANTE", "SKU vacío o inválido")

        if "fecha" in df.columns:
            val_f = row.get("fecha", "")
            if str(val_f).strip() == "":
                agregar_error(errores, "compras", fila, sku, "fecha", val_f, "DATO_FALTANTE", "Fecha vacía")
            elif not normalizar_fecha_valida(pd.Series([val_f])).iloc[0]:
                agregar_error(errores, "compras", fila, sku, "fecha", val_f, "FORMATO_INVALIDO", "Fecha no cumple aaaa-mm-dd ni dd/mm/aaaa")

        if "cantidad" in df.columns:
            val_c = row.get("cantidad", "")
            num_c = pd.to_numeric(str(val_c).strip(), errors="coerce")
            if str(val_c).strip() == "" or pd.isna(num_c):
                agregar_error(errores, "compras", fila, sku, "cantidad", val_c, "DATO_INVALIDO", "Cantidad no numérica o vacía")
            elif num_c < 0:
                agregar_error(errores, "compras", fila, sku, "cantidad", val_c, "VALOR_NEGATIVO", "Cantidad negativa en compra")

        if "costo_unitario" in df.columns:
            val_k = row.get("costo_unitario", "")
            num_k = pd.to_numeric(str(val_k).strip(), errors="coerce")
            if str(val_k).strip() == "" or pd.isna(num_k):
                agregar_error(errores, "compras", fila, sku, "costo_unitario", val_k, "DATO_INVALIDO", "Costo unitario no numérico o vacío")
            elif num_k < 0:
                agregar_error(errores, "compras", fila, sku, "costo_unitario", val_k, "VALOR_NEGATIVO", "Costo unitario negativo")


def auditar_almacen(df: pd.DataFrame, errores: list[dict]) -> None:
    for idx, row in df.iterrows():
        fila = idx + 2
        sku = normalizar_sku(pd.Series([row.get("sku", pd.NA)])).iloc[0]

        if pd.isna(sku):
            agregar_error(errores, "almacen", fila, sku, "sku", row.get("sku"), "DATO_FALTANTE", "SKU vacío o inválido")

        if "fecha" in df.columns:
            val_f = row.get("fecha", "")
            if str(val_f).strip() == "":
                agregar_error(errores, "almacen", fila, sku, "fecha", val_f, "DATO_FALTANTE", "Fecha vacía")
            elif not normalizar_fecha_valida(pd.Series([val_f])).iloc[0]:
                agregar_error(errores, "almacen", fila, sku, "fecha", val_f, "FORMATO_INVALIDO", "Fecha no cumple aaaa-mm-dd ni dd/mm/aaaa")

        if "cantidad_recibida" in df.columns:
            val_r = row.get("cantidad_recibida", "")
            num_r = pd.to_numeric(str(val_r).strip(), errors="coerce")
            if str(val_r).strip() == "" or pd.isna(num_r):
                agregar_error(errores, "almacen", fila, sku, "cantidad_recibida", val_r, "DATO_INVALIDO", "Cantidad recibida no numérica o vacía")
            elif num_r < 0:
                agregar_error(errores, "almacen", fila, sku, "cantidad_recibida", val_r, "VALOR_NEGATIVO", "Cantidad recibida negativa")


def auditar_ot(df: pd.DataFrame, errores: list[dict]) -> None:
    for idx, row in df.iterrows():
        fila = idx + 2
        sku = normalizar_sku(pd.Series([row.get("sku", pd.NA)])).iloc[0]

        if pd.isna(sku):
            agregar_error(errores, "ordenes_trabajo_hist", fila, sku, "sku", row.get("sku"), "DATO_FALTANTE", "SKU vacío o inválido")

        if "cantidad" in df.columns:
            val_c = row.get("cantidad", "")
            num_c = pd.to_numeric(str(val_c).strip(), errors="coerce")
            if str(val_c).strip() == "" or pd.isna(num_c):
                agregar_error(errores, "ordenes_trabajo_hist", fila, sku, "cantidad", val_c, "DATO_INVALIDO", "Cantidad no numérica o vacía")
            elif num_c < 0:
                agregar_error(errores, "ordenes_trabajo_hist", fila, sku, "cantidad", val_c, "VALOR_NEGATIVO", "Cantidad negativa en OT histórica")


def auditar_discrepancias_sku(
    compras: pd.DataFrame,
    almacen: pd.DataFrame,
    eventos: pd.DataFrame,
    errores: list[dict],
) -> None:
    c_df = compras.copy()
    c_df["sku_norm"] = normalizar_sku(c_df["sku"])
    c_df["cant_num"] = pd.to_numeric(c_df.get("cantidad", pd.Series(dtype="object")), errors="coerce")
    c_valid = c_df[c_df["cant_num"].notna() & (c_df["cant_num"] >= 0)]
    tot_compras = c_valid.groupby("sku_norm", dropna=True)["cant_num"].sum()

    a_df = almacen.copy()
    a_df["sku_norm"] = normalizar_sku(a_df["sku"])
    a_df["cant_num"] = pd.to_numeric(a_df.get("cantidad_recibida", pd.Series(dtype="object")), errors="coerce")
    a_valid = a_df[a_df["cant_num"].notna() & (a_df["cant_num"] >= 0)]
    tot_almacen = a_valid.groupby("sku_norm", dropna=True)["cant_num"].sum()

    e_df = eventos.copy()
    e_df["sku_norm"] = normalizar_sku(e_df["sku"])
    e_df["cant_num"] = pd.to_numeric(e_df.get("cantidad", pd.Series(dtype="object")), errors="coerce")
    if "qr_valido" in e_df.columns:
        e_df = e_df[pd.to_numeric(e_df["qr_valido"], errors="coerce") == 1]
    e_valid = e_df[e_df["cant_num"].notna() & (e_df["cant_num"] >= 0)]
    tot_eventos = e_valid.groupby("sku_norm", dropna=True)["cant_num"].sum()

    skus = sorted(
        set(tot_compras.dropna().index)
        | set(tot_almacen.dropna().index)
        | set(tot_eventos.dropna().index)
    )

    for sku in skus:
        val_c = float(tot_compras.get(sku, 0.0)) if sku in tot_compras.index else 0.0
        val_a = float(tot_almacen.get(sku, 0.0)) if sku in tot_almacen.index else 0.0
        val_e = float(tot_eventos.get(sku, 0.0)) if sku in tot_eventos.index else 0.0

        if val_c != val_a:
            agregar_error(
                errores,
                "cruce_sku",
                0,
                sku,
                "cantidad_vs_cantidad_recibida",
                f"compra={val_c:g} | almacen={val_a:g}",
                "DISCREPANCIA_COMPRA_ALMACEN",
                f"Diferencia de {val_c - val_a:g} unidades entre compra y almacén",
            )

        if val_a != val_e:
            agregar_error(
                errores,
                "cruce_sku",
                0,
                sku,
                "almacen_vs_eventos",
                f"almacen={val_a:g} | eventos={val_e:g}",
                "DISCREPANCIA_ALMACEN_EVENTOS",
                f"Diferencia de {val_a - val_e:g} unidades entre almacén y eventos en tiempo real",
            )


def main() -> None:
    conn = sqlite3.connect(DB_PATH)
    stg_compras = pd.read_sql("SELECT * FROM stg_compras", conn, dtype=str)
    stg_almacen = pd.read_sql("SELECT * FROM stg_almacen", conn, dtype=str)
    stg_ot = pd.read_sql("SELECT * FROM stg_ot_historicas", conn, dtype=str)
    eventos = pd.read_sql("SELECT * FROM eventos", conn, dtype=str)
    conn.close()

    errores: list[dict] = []
    auditar_compras(stg_compras, errores)
    auditar_almacen(stg_almacen, errores)
    auditar_ot(stg_ot, errores)
    auditar_discrepancias_sku(stg_compras, stg_almacen, eventos, errores)

    df_errores = pd.DataFrame(
        errores,
        columns=[
            "fuente",
            "fila_origen",
            "sku",
            "campo",
            "valor_actual",
            "tipo_error",
            "detalle",
        ],
    )

    # Formato CSV amigable para Excel en español (; como separador y BOM UTF-8)
    df_errores.to_csv(OUT_FILE, sep=";", index=False, encoding="utf-8-sig")
    print(f"Reporte generado en '{OUT_FILE}' con {len(df_errores)} hallazgos.")


if __name__ == "__main__":
    main()