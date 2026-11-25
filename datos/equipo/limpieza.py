# -*- coding: utf-8 -*-
"""
Limpieza y validación de datos de almacén (compras, almacén, OT históricas y eventos).
"""

from pathlib import Path
import sqlite3
import pandas as pd

DB_PATH = "almacen_hackaitver.db"
OUT_DIR = Path("csv_cln")


def vacios_a_nulo(df: pd.DataFrame) -> pd.DataFrame:
    """Quita espacios en los extremos y convierte cadenas vacías en pd.NA."""
    for col in df.columns:
        df[col] = df[col].astype("string").str.strip()
    return df.replace({"": pd.NA, "nan": pd.NA, "NaN": pd.NA, "None": pd.NA, "null": pd.NA})


def normalizar_fecha(serie: pd.Series) -> pd.Series:
    """Acepta aaaa-mm-dd y dd/mm/aaaa; devuelve texto aaaa-mm-dd."""
    f1 = pd.to_datetime(serie, format="%Y-%m-%d", errors="coerce")
    f2 = pd.to_datetime(serie, format="%d/%m/%Y", errors="coerce")
    return f1.fillna(f2).dt.strftime("%Y-%m-%d")


def unificar_texto(serie: pd.Series) -> pd.Series:
    """Unifica variantes que solo difieren en espacios o mayúsculas/minúsculas."""
    s = serie.astype("string").str.replace(r"\s+", " ", regex=True).str.strip()
    clave = s.str.casefold()
    canon = (
        s.dropna()
        .groupby(clave.dropna())
        .agg(lambda x: x.value_counts().index[0])
    )
    return clave.map(canon)


def limpiar_entero_no_negativo(serie: pd.Series) -> pd.Series:
    """Convierte a entero no negativo; valores negativos o no numéricos pasan a <NA>."""
    num = pd.to_numeric(serie, errors="coerce")
    valido = num.where(num >= 0)
    return valido.astype("Int64")


def limpiar_decimal_no_negativo(serie: pd.Series) -> pd.Series:
    """Convierte a flotante no negativo; valores negativos o no numéricos pasan a NaN."""
    num = pd.to_numeric(serie, errors="coerce")
    return num.where(num >= 0)


def limpiar_compras(df: pd.DataFrame) -> pd.DataFrame:
    df = vacios_a_nulo(df.copy())
    if "sku" in df.columns:
        df["sku"] = df["sku"].str.upper()
    if "fecha" in df.columns:
        df["fecha"] = normalizar_fecha(df["fecha"])
    if "proveedor" in df.columns:
        df["proveedor"] = unificar_texto(df["proveedor"])
    if "descripcion" in df.columns:
        df["descripcion"] = unificar_texto(df["descripcion"])
    if "cantidad" in df.columns:
        df["cantidad"] = limpiar_entero_no_negativo(df["cantidad"])
    if "costo_unitario" in df.columns:
        df["costo_unitario"] = limpiar_decimal_no_negativo(df["costo_unitario"])
    return df.drop_duplicates().reset_index(drop=True)


def limpiar_almacen(df: pd.DataFrame) -> pd.DataFrame:
    df = vacios_a_nulo(df.copy())
    if "sku" in df.columns:
        df["sku"] = df["sku"].str.upper()
    if "fecha" in df.columns:
        df["fecha"] = normalizar_fecha(df["fecha"])
    if "descripcion" in df.columns:
        df["descripcion"] = unificar_texto(df["descripcion"])
    if "ubicacion" in df.columns:
        df["ubicacion"] = df["ubicacion"].str.upper()
    if "cantidad_recibida" in df.columns:
        df["cantidad_recibida"] = limpiar_entero_no_negativo(df["cantidad_recibida"])
    return df.drop_duplicates().reset_index(drop=True)


def limpiar_ot(df: pd.DataFrame) -> pd.DataFrame:
    df = vacios_a_nulo(df.copy())
    if "sku" in df.columns:
        df["sku"] = df["sku"].str.upper()
    if "fecha" in df.columns:
        df["fecha"] = normalizar_fecha(df["fecha"])
    if "estado" in df.columns:
        df["estado"] = df["estado"].str.lower()
    if "cantidad" in df.columns:
        df["cantidad"] = limpiar_entero_no_negativo(df["cantidad"])
    return df.drop_duplicates().reset_index(drop=True)


def validar_por_sku(
    compras: pd.DataFrame,
    almacen: pd.DataFrame,
    eventos: pd.DataFrame,
) -> pd.DataFrame:
    """
    Compara por SKU:
    - Total comprado vs total recibido en almacén
    - Total de eventos en tiempo real (enfoque en eventos válidos)
    """
    cant_compras = (
        compras.groupby("sku", dropna=True)["cantidad"]
        .sum(min_count=1)
        .rename("total_comprado")
    )
    cant_almacen = (
        almacen.groupby("sku", dropna=True)["cantidad_recibida"]
        .sum(min_count=1)
        .rename("total_almacen")
    )

    ev = eventos.copy()
    if "sku" in ev.columns:
        ev["sku"] = ev["sku"].astype("string").str.strip().str.upper()
    if "cantidad" in ev.columns:
        ev["cantidad"] = limpiar_entero_no_negativo(ev["cantidad"])

    # Si existe columna de validez/resultado en eventos, priorizamos los válidos
    if "qr_valido" in ev.columns:
        ev_validos = ev[pd.to_numeric(ev["qr_valido"], errors="coerce") == 1]
    else:
        ev_validos = ev

    cant_eventos = (
        ev_validos.groupby("sku", dropna=True)["cantidad"]
        .sum(min_count=1)
        .rename("total_eventos_ok")
    )

    resumen = (
        pd.concat([cant_compras, cant_almacen, cant_eventos], axis=1)
        .reset_index()
        .rename(columns={"index": "sku"})
    )

    c_num = pd.to_numeric(resumen["total_comprado"], errors="coerce")
    a_num = pd.to_numeric(resumen["total_almacen"], errors="coerce")
    e_num = pd.to_numeric(resumen["total_eventos_ok"], errors="coerce")

    resumen["dif_compra_vs_almacen"] = c_num - a_num
    resumen["dif_almacen_vs_eventos"] = a_num - e_num
    resumen["coincide_compra_almacen"] = (c_num.fillna(-1) == a_num.fillna(-1))
    resumen["coincide_almacen_eventos"] = (a_num.fillna(-1) == e_num.fillna(-1))

    return resumen


def main() -> None:
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(DB_PATH)

    stg_compras = pd.read_sql("SELECT * FROM stg_compras", conn, dtype=str)
    stg_almacen = pd.read_sql("SELECT * FROM stg_almacen", conn, dtype=str)
    stg_ot = pd.read_sql("SELECT * FROM stg_ot_historicas", conn, dtype=str)
    eventos = pd.read_sql("SELECT * FROM eventos", conn, dtype=str)

    cln_compras = limpiar_compras(stg_compras)
    cln_almacen = limpiar_almacen(stg_almacen)
    cln_ot = limpiar_ot(stg_ot)
    validacion_sku = validar_por_sku(cln_compras, cln_almacen, eventos)

    # Guardar CSV limpios en la carpeta csv_cln
    cln_compras.to_csv(OUT_DIR / "compras_cln.csv", index=False)
    cln_almacen.to_csv(OUT_DIR / "almacen_cln.csv", index=False)
    cln_ot.to_csv(OUT_DIR / "ordenes_trabajo_cln.csv", index=False)
    validacion_sku.to_csv(OUT_DIR / "validacion_sku.csv", index=False)

    # También refrescar tablas cln_* en SQLite por si las consultas luego
    cln_compras.to_sql("cln_compras", conn, if_exists="replace", index=False)
    cln_almacen.to_sql("cln_almacen", conn, if_exists="replace", index=False)
    cln_ot.to_sql("cln_ot_historicas", conn, if_exists="replace", index=False)

    conn.close()
    print(f"Archivos limpios guardados en '{OUT_DIR}/':")
    print(f"  - compras_cln.csv ({len(cln_compras)} filas)")
    print(f"  - almacen_cln.csv ({len(cln_almacen)} filas)")
    print(f"  - ordenes_trabajo_cln.csv ({len(cln_ot)} filas)")
    print(f"  - validacion_sku.csv ({len(validacion_sku)} SKUs)")


if __name__ == "__main__":
    main()