# fabric/notebooks/05_dim_date.py
# Génère la table de dates dim_date et l'enregistre dans ENEDIS_LAKEHOUSE.
# À exécuter UNE SEULE FOIS (ou après reset du Lakehouse).
# ─────────────────────────────────────────────────────────────────────────────

# ── CELLULE 1 : Imports et configuration ─────────────────────────────────────
import os

import pandas as pd
from pyspark.sql import functions as F
from pyspark.sql.types import (
    BooleanType, DateType, IntegerType, StringType,
    StructField, StructType,
)
from delta.tables import DeltaTable

WORKSPACE_ID     = "d7959e21-626e-42c4-87f6-a6e79ece7c42"
LAKEHOUSE_ID     = "a9b125bc-cf18-41fc-a4f2-1a8918bbb4e3"
ONELAKE_BASE     = f"abfss://{WORKSPACE_ID}@onelake.dfs.fabric.microsoft.com/{LAKEHOUSE_ID}"
LAKEHOUSE_TABLES = f"{ONELAKE_BASE}/Tables"

DATE_START = os.getenv("DIM_DATE_START", "2020-01-01")
DATE_END   = os.getenv("DIM_DATE_END",   "2030-12-31")

print(f"dim_date : plage {DATE_START} → {DATE_END}")

# ── CELLULE 2 : Génération des dates ─────────────────────────────────────────
MOIS_FR = {
    1: "Janvier",   2: "Février",   3: "Mars",      4: "Avril",
    5: "Mai",       6: "Juin",      7: "Juillet",    8: "Août",
    9: "Septembre", 10: "Octobre",  11: "Novembre",  12: "Décembre",
}
MOIS_ABR_FR = {
    1: "Jan", 2: "Fév",  3: "Mar", 4: "Avr",
    5: "Mai", 6: "Juin", 7: "Jul", 8: "Aoû",
    9: "Sep", 10: "Oct", 11: "Nov", 12: "Déc",
}
JOUR_FR = {
    0: "Lundi", 1: "Mardi", 2: "Mercredi", 3: "Jeudi",
    4: "Vendredi", 5: "Samedi", 6: "Dimanche",
}

def _saison(m: int) -> str:
    if m in (12, 1, 2): return "Hiver"
    if m in (3, 4, 5):  return "Printemps"
    if m in (6, 7, 8):  return "Été"
    return "Automne"

dates = pd.date_range(start=DATE_START, end=DATE_END, freq="D")
rows = []
for d in dates:
    iso = d.isocalendar()
    rows.append({
        "date":              d.date(),
        "annee":             int(d.year),
        "trimestre":         int(d.quarter),
        "mois":              int(d.month),
        "mois_nom":          MOIS_FR[d.month],
        "mois_abr":          MOIS_ABR_FR[d.month],
        "annee_mois":        f"{d.year}-{d.month:02d}",
        "semaine_iso":       int(iso[1]),
        "jour_mois":         int(d.day),
        "jour_semaine":      int(d.dayofweek + 1),
        "jour_semaine_nom":  JOUR_FR[d.dayofweek],
        "is_weekend":        bool(d.dayofweek >= 5),
        "saison":            _saison(d.month),
    })

df_pd = pd.DataFrame(rows)
print(f"Lignes générées : {len(df_pd):,}")

# ── CELLULE 3 : Conversion Spark + écriture Delta ────────────────────────────
schema_dim_date = StructType([
    StructField("date",             DateType(),    False),
    StructField("annee",            IntegerType(), True),
    StructField("trimestre",        IntegerType(), True),
    StructField("mois",             IntegerType(), True),
    StructField("mois_nom",         StringType(),  True),
    StructField("mois_abr",         StringType(),  True),
    StructField("annee_mois",       StringType(),  True),
    StructField("semaine_iso",      IntegerType(), True),
    StructField("jour_mois",        IntegerType(), True),
    StructField("jour_semaine",     IntegerType(), True),
    StructField("jour_semaine_nom", StringType(),  True),
    StructField("is_weekend",       BooleanType(), True),
    StructField("saison",           StringType(),  True),
])

df = spark.createDataFrame(df_pd, schema=schema_dim_date)
table_path = f"{LAKEHOUSE_TABLES}/dim_date"

df.write.format("delta") \
    .mode("overwrite") \
    .option("overwriteSchema", "true") \
    .save(table_path)

print(f"✅ dim_date : {df.count():,} lignes écrites.")

# ── CELLULE 4 : Enregistrement dans le métastore Fabric ──────────────────────
spark.sql(f"CREATE TABLE IF NOT EXISTS dim_date USING delta LOCATION '{table_path}'")
print("✅ dim_date enregistrée dans le métastore.")
print()
print("Relations à créer dans Power BI (modèle sémantique) :")
print("  dim_date.date  →  enedis_data.date         (1 : *)")
print("  dim_date.date  →  dju_sete.date             (1 : *)")
print("  dim_date.date  →  enedis_load_curve.date    (1 : *)")
