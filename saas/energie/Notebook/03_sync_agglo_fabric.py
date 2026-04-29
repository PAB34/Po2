# =============================================================================
# Fabric Notebook — ENEDIS Sync Quotidien AGGLO (Sète Agglopôle Méditerranée)
# Workspace : ENEDIS  |  Lakehouse : ENEDIS_LAKEHOUSE
#
# ► Identique au notebook Ville mais pointe vers Files/agglo/ dans OneLake.
# ► Les données sont mergées dans les mêmes Delta tables (enedis_data, etc.)
#   → les PRMs agglo coexistent avec les PRMs Sète, séparables via usage_point_id.
# ► Planifier à 05:45 (heure Paris) via Fabric Schedule (décalé de 15 min / Sète).
# ► Coller chaque section "── CELLULE N ──" dans une cellule séparée.
# =============================================================================

# ── CELLULE 1 : Installation des dépendances ────────────────────────────────
# ⚠️ TOUJOURS exécuter EN PREMIER — le pip install redémarre le kernel.
%pip install cryptography python-dotenv --quiet

# ── CELLULE 2 : Configuration ─────────────────────────────────────────────────
import os
from notebookutils import mssparkutils

WORKSPACE_ID     = "d7959e21-626e-42c4-87f6-a6e79ece7c42"
LAKEHOUSE_ID     = "a9b125bc-cf18-41fc-a4f2-1a8918bbb4e3"
ONELAKE_BASE     = f"abfss://{WORKSPACE_ID}@onelake.dfs.fabric.microsoft.com/{LAKEHOUSE_ID}"
LAKEHOUSE_FILES  = f"{ONELAKE_BASE}/Files"
LAKEHOUSE_TABLES = f"{ONELAKE_BASE}/Tables"
LOCAL_TMP        = "/tmp/enedis_agglo"   # ← répertoire séparé pour éviter conflits avec Sète

os.makedirs(f"{LOCAL_TMP}/output", exist_ok=True)
os.makedirs(f"{LOCAL_TMP}/state",  exist_ok=True)
os.makedirs(f"{LOCAL_TMP}/config", exist_ok=True)
os.makedirs(f"{LOCAL_TMP}/DJU",    exist_ok=True)
print(f"✅ Config OK — LAKEHOUSE_FILES={LAKEHOUSE_FILES}")
print(f"   LOCAL_TMP={LOCAL_TMP}  (agglo — séparé de /tmp/enedis Sète)")

# ── CELLULE 3 : Chargement des secrets depuis .env agglo dans OneLake ────────
# Uploader votre fichier .env agglo dans :
#   ENEDIS_LAKEHOUSE → Files → agglo → config → .env

from dotenv import load_dotenv

env_onelake = f"{LAKEHOUSE_FILES}/agglo/config/.env"
env_local   = f"{LOCAL_TMP}/config/.env"

try:
    mssparkutils.fs.cp(env_onelake, f"file://{env_local}", False)
    load_dotenv(env_local, override=True)
    print(f"✅ .env agglo chargé depuis OneLake")
except Exception as e:
    raise FileNotFoundError(
        f".env agglo introuvable dans OneLake ({env_onelake}).\n"
        f"→ Uploader votre fichier .env dans ENEDIS_LAKEHOUSE/Files/agglo/config/.env\n{e}"
    )

secrets_requis = ["ENEDIS_CLIENT_ID", "ENEDIS_CLIENT_SECRET"]
manquants = [s for s in secrets_requis if not os.getenv(s)]
if manquants:
    raise EnvironmentError(f"Secrets manquants dans .env agglo : {manquants}")
print(f"✅ {len(secrets_requis)} secrets présents.")

# ── CELLULE 4 : Restaurer état et config depuis OneLake ──────────────────────

def onelake_to_local(onelake_path, local_path):
    """Copie un fichier OneLake vers /tmp local."""
    try:
        mssparkutils.fs.cp(onelake_path, f"file://{local_path}", False)
        print(f"  ✅ Restauré : {local_path}")
        return True
    except Exception as e:
        print(f"  ⚠️  Absent (sera créé) : {local_path} — {e}")
        return False

def local_to_onelake(local_path, onelake_path, required=True):
    """Copie un fichier /tmp local vers OneLake. Si required=False, ignore si absent."""
    import os as _os
    if not _os.path.exists(local_path):
        if required:
            raise FileNotFoundError(f"Fichier local introuvable : {local_path}")
        print(f"  ⚠️  Absent (ignoré) : {local_path}")
        return
    crc = _os.path.join(_os.path.dirname(local_path), f".{_os.path.basename(local_path)}.crc")
    if _os.path.exists(crc):
        _os.remove(crc)
    mssparkutils.fs.cp(f"file://{local_path}", onelake_path, True)
    print(f"  ✅ Sauvegardé : {onelake_path}")

print("Restauration depuis OneLake (agglo)…")
onelake_to_local(f"{LAKEHOUSE_FILES}/agglo/state/processed_files.json",
                 f"{LOCAL_TMP}/state/processed_files.json")
onelake_to_local(f"{LAKEHOUSE_FILES}/agglo/config/prm_list.txt",
                 f"{LOCAL_TMP}/config/prm_list.txt")
# Template partagé avec Sète (même structure JSON)
onelake_to_local(f"{LAKEHOUSE_FILES}/config/enedis_request_template.json",
                 f"{LOCAL_TMP}/config/enedis_request_template.json")
onelake_to_local(f"{LAKEHOUSE_FILES}/agglo/output/enedis_load_curve.csv",
                 f"{LOCAL_TMP}/output/enedis_load_curve.csv")
# DJU partagé avec Sète (même zone géographique)
onelake_to_local(f"{LAKEHOUSE_FILES}/DJU/dju_sete.csv",
                 f"{LOCAL_TMP}/DJU/dju_sete.csv")

# ── CELLULE 5b : Collecte DJU via Open-Meteo ─────────────────────────────────
import subprocess, sys

onelake_to_local(f"{LAKEHOUSE_FILES}/scripts/dju_sete.py",
                 f"{LOCAL_TMP}/dju_sete.py")

env_dju = os.environ.copy()
env_dju.update({
    "CITY_NAME":          os.getenv("CITY_NAME",          "Sète"),
    "COUNTRY_CODE":       os.getenv("COUNTRY_CODE",       "FR"),
    "BASE_HEATING":       os.getenv("BASE_HEATING",       "18.0"),
    "BASE_COOLING":       os.getenv("BASE_COOLING",       "22.0"),
    "HISTORY_START_DATE": os.getenv("DJU_HISTORY_START",  "2015-01-01"),
    "DJU_OUTPUT_PATH":    f"{LOCAL_TMP}/DJU/dju_sete.csv",
})

proc_dju = subprocess.Popen(
    [sys.executable, f"{LOCAL_TMP}/dju_sete.py"],
    env=env_dju, cwd=LOCAL_TMP,
    stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
    text=True, bufsize=1,
)
for line in proc_dju.stdout:
    print(line, end="", flush=True)
proc_dju.wait()
if proc_dju.returncode != 0:
    print(f"⚠️  DJU script terminé avec code {proc_dju.returncode} — run ENEDIS continue.")

# ── CELLULE 5 : Exécution du script de sync ENEDIS (agglo) ───────────────────
import subprocess, sys

onelake_to_local(f"{LAKEHOUSE_FILES}/scripts/enedis_to_powerbi.py",
                 f"{LOCAL_TMP}/enedis_to_powerbi.py")

env = os.environ.copy()
env.update({
    "CSV_OUTPUT_PATH":             f"{LOCAL_TMP}/output/enedis_data.csv",
    "LOAD_CURVE_OUTPUT_PATH":      f"{LOCAL_TMP}/output/enedis_load_curve.csv",
    "STATE_FILE_PATH":             f"{LOCAL_TMP}/state/processed_files.json",
    "PRM_LIST_PATH":               f"{LOCAL_TMP}/config/prm_list.txt",
    "REQUEST_TEMPLATE_PATH":       f"{LOCAL_TMP}/config/enedis_request_template.json",
    "HISTORY_DAYS":                os.getenv("HISTORY_DAYS", "365"),
    "LOAD_CURVE_HISTORY_DAYS":     os.getenv("LOAD_CURVE_HISTORY_DAYS", "365"),
    "LOAD_CURVE_MAX_DAYS_PER_RUN": os.getenv("LOAD_CURVE_MAX_DAYS_PER_RUN", "28"),
    "ALERT_WEBHOOK_URL":           os.getenv("ALERT_WEBHOOK_URL", ""),
    "ALERT_ON_SUCCESS":            os.getenv("ALERT_ON_SUCCESS", "true"),
    # Stubs pour compatibilité avec les anciennes versions du script
    "PBI_TENANT_ID":               os.getenv("PBI_TENANT_ID",     "stub"),
    "PBI_CLIENT_ID":               os.getenv("PBI_CLIENT_ID",     "stub"),
    "PBI_CLIENT_SECRET":           os.getenv("PBI_CLIENT_SECRET", "stub"),
    "PBI_WORKSPACE_ID":            os.getenv("PBI_WORKSPACE_ID",  "stub"),
    "PBI_DATASET_ID":              os.getenv("PBI_DATASET_ID",    "stub"),
})

proc = subprocess.Popen(
    [sys.executable, f"{LOCAL_TMP}/enedis_to_powerbi.py"],
    env=env, cwd=LOCAL_TMP,
    stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
    text=True, bufsize=1,
)
for line in proc.stdout:
    print(line, end="", flush=True)
proc.wait()
if proc.returncode != 0:
    raise RuntimeError(f"Script terminé avec code {proc.returncode}")

# ── CELLULE 6 : Sauvegarder état et CSVs agglo dans OneLake ──────────────────
print("Sauvegarde vers OneLake (agglo)…")
local_to_onelake(f"{LOCAL_TMP}/state/processed_files.json",
                 f"{LAKEHOUSE_FILES}/agglo/state/processed_files.json")
local_to_onelake(f"{LOCAL_TMP}/output/enedis_data.csv",
                 f"{LAKEHOUSE_FILES}/agglo/output/enedis_data.csv", required=False)
local_to_onelake(f"{LOCAL_TMP}/output/enedis_load_curve.csv",
                 f"{LAKEHOUSE_FILES}/agglo/output/enedis_load_curve.csv", required=False)
for name in [
    "enedis_contracts",
    "enedis_addresses",
    "enedis_connections",
    "enedis_contract_summary",
    "enedis_alimentation",
    "enedis_situation_contrat",
]:
    local_to_onelake(f"{LOCAL_TMP}/output/{name}.csv",
                     f"{LAKEHOUSE_FILES}/agglo/output/{name}.csv", required=False)

# ── CELLULE 7 : Upsert Delta tables (mêmes tables que Sète — merge unifié) ───
# Les PRMs agglo s'ajoutent aux PRMs Sète dans les mêmes tables.
# Power BI peut filtrer par usage_point_id via la table enedis_contracts.

import os
from pyspark.sql import functions as F
from pyspark.sql.types import StructType, StructField, StringType, DoubleType, TimestampType, DateType
from delta.tables import DeltaTable
from datetime import datetime, timedelta, timezone

schema_data = StructType([
    StructField("usage_point_id",   StringType(),    True),
    StructField("date",             DateType(),      True),
    StructField("value_wh",         DoubleType(),    True),
    StructField("unit",             StringType(),    True),
    StructField("quality",          StringType(),    True),
    StructField("flow_direction",   StringType(),    True),
    StructField("_ingested_at_utc", TimestampType(), True),
])

schema_lc = StructType([
    StructField("usage_point_id",   StringType(),    True),
    StructField("datetime",         TimestampType(), True),
    StructField("value_w",          DoubleType(),    True),
    StructField("unit",             StringType(),    True),
    StructField("quality",          StringType(),    True),
    StructField("_ingested_at_utc", TimestampType(), True),
])

spark.conf.set("spark.databricks.delta.schema.autoMerge.enabled", "true")

def upsert_delta(local_csv, onelake_csv, schema, table_name, merge_keys,
                 partition_cols=None, post_read_transform=None):
    table_path = f"{LAKEHOUSE_TABLES}/{table_name}"
    if not os.path.exists(local_csv):
        print(f"⚠️  {table_name} : CSV absent localement, ignoré.")
        return
    df = spark.read.option("header", "true").schema(schema).csv(onelake_csv)
    if post_read_transform:
        df = post_read_transform(df)
    n = df.count()
    if n == 0:
        print(f"⚠️  {table_name} : 0 ligne, ignoré.")
        return
    if DeltaTable.isDeltaTable(spark, table_path):
        cond = " AND ".join(f"t.{k} = s.{k}" for k in merge_keys)
        set_cols = {c: f"s.{c}" for c in df.columns}
        (DeltaTable.forPath(spark, table_path).alias("t")
         .merge(df.alias("s"), cond)
         .whenMatchedUpdate(set=set_cols)
         .whenNotMatchedInsert(values=set_cols)
         .execute())
        print(f"✅ {table_name} : merge {n:,} lignes (agglo)")
    else:
        w = df.write.format("delta").mode("overwrite").option("overwriteSchema", "true")
        if partition_cols:
            for c in partition_cols:
                df = df.withColumn(c, F.year("date") if c == "year" else F.month("date"))
            w = w.partitionBy(*partition_cols)
        w.save(table_path)
        print(f"✅ {table_name} : chargement initial {n:,} lignes (agglo)")

upsert_delta(
    f"{LOCAL_TMP}/output/enedis_data.csv",
    f"{LAKEHOUSE_FILES}/agglo/output/enedis_data.csv",
    schema_data, "enedis_data", ["usage_point_id", "date"], ["year", "month"]
)

upsert_delta(
    f"{LOCAL_TMP}/output/enedis_load_curve.csv",
    f"{LAKEHOUSE_FILES}/agglo/output/enedis_load_curve.csv",
    schema_lc, "enedis_load_curve", ["usage_point_id", "datetime"],
    post_read_transform=lambda df: df.withColumn("date", F.to_date("datetime"))
)

schema_str = StructType([
    StructField("usage_point_id", StringType(), True),
    StructField("contract_id",    StringType(), True),
    StructField("segment",        StringType(), True),
    StructField("contract_type",  StringType(), True),
    StructField("subscribed_power_kva", DoubleType(), True),
])

for csv_name, tbl, keys in [
    ("enedis_contracts",        "enedis_contracts",        ["usage_point_id"]),
    ("enedis_addresses",        "enedis_addresses",        ["usage_point_id"]),
    ("enedis_connections",      "enedis_connections",      ["usage_point_id"]),
    ("enedis_contract_summary", "enedis_contract_summary", ["usage_point_id"]),
    ("enedis_alimentation",     "enedis_alimentation",     ["usage_point_id"]),
    ("enedis_situation_contrat", "enedis_situation_contrat", ["usage_point_id"]),
]:
    local_csv    = f"{LOCAL_TMP}/output/{csv_name}.csv"
    onelake_csv  = f"{LAKEHOUSE_FILES}/agglo/output/{csv_name}.csv"
    if os.path.exists(local_csv):
        df = spark.read.option("header", "true").option("inferSchema", "true").csv(onelake_csv)
        n  = df.count()
        table_path = f"{LAKEHOUSE_TABLES}/{tbl}"
        if DeltaTable.isDeltaTable(spark, table_path):
            cond     = " AND ".join(f"t.{k} = s.{k}" for k in keys)
            set_cols = {c: f"s.{c}" for c in df.columns}
            (DeltaTable.forPath(spark, table_path).alias("t")
             .merge(df.alias("s"), cond)
             .whenMatchedUpdate(set=set_cols)
             .whenNotMatchedInsert(values=set_cols)
             .execute())
            print(f"✅ {tbl} : merge {n:,} lignes (agglo)")
        else:
            df.write.format("delta").mode("overwrite").option("overwriteSchema", "true").save(table_path)
            print(f"✅ {tbl} : chargement initial {n:,} lignes (agglo)")

print("\n✅ Sync ENEDIS Agglo terminé — Delta tables mises à jour.")

# ── CELLULE 8 : Enregistrer les tables Delta dans le metastore Fabric ─────────
# À exécuter une seule fois seulement si les tables ne sont pas déjà présentes.
from delta.tables import DeltaTable

_tables = [
    "enedis_load_curve", "enedis_data", "enedis_addresses",
    "enedis_contracts", "enedis_connections", "enedis_contract_summary",
    "enedis_alimentation", "enedis_situation_contrat",
    "dju_sete",
]
for _tbl in _tables:
    _path = f"{LAKEHOUSE_TABLES}/{_tbl}"
    if DeltaTable.isDeltaTable(spark, _path):
        spark.sql(f"CREATE TABLE IF NOT EXISTS {_tbl} USING delta LOCATION '{_path}'")
        print(f"  ✅ {_tbl} enregistrée (ou déjà présente)")
    else:
        print(f"  ⚠️  {_tbl} : table Delta absente, ignorée")
