# -*- coding: utf-8 -*-
"""
Created on Wed Nov 25 11:45:40 2026

@author: iende
"""
import sqlite3
import pandas as pd

DB_PATH = "almacen_hackaitver.db"
ARCHIVOS = {
    "stg_compras": "compras.csv",
    "stg_almacen": "almacen.csv",
    "stg_ot_historicas": "ordenes_trabajo.csv",
}

def ingerir():
    conn = sqlite3.connect(DB_PATH)
    for tabla, archivo in ARCHIVOS.items():
        df = pd.read_csv(archivo, dtype=str, keep_default_na=False)
        df.to_sql(tabla, conn, if_exists="replace", index=False)
        print(f"{tabla}: {len(df)} filas")
    conn.close()

if __name__ == "__main__":
    ingerir()