# =============================================================================
# Fabric Notebook — ENEDIS Backfill Consommation Journalière
# Workspace : ENEDIS  |  Lakehouse : ENEDIS_LAKEHOUSE
# =============================================================================

# ── CELLULE 1 : Installation des dépendances ─────────────────────────────────
%pip install cryptography python-dotenv --quiet

# ── CELLULE 2 : Configuration ─────────────────────────────────────────────────
import os, csv
from datetime import date, timedelta
from notebookutils import mssparkutils

WORKSPACE_ID     = "d7959e21-626e-42c4-87f6-a6e79ece7c42"
LAKEHOUSE_ID     = "a9b125bc-cf18-41fc-a4f2-1a8918bbb4e3"
ONELAKE_BASE     = f"abfss://{WORKSPACE_ID}@onelake.dfs.fabric.microsoft.com/{LAKEHOUSE_ID}"
LAKEHOUSE_FILES  = f"{ONELAKE_BASE}/Files"
LAKEHOUSE_TABLES = f"{ONELAKE_BASE}/Tables"
LOCAL_TMP        = "/tmp/enedis"

CHUNK_DAYS       = 7
MAX_ITERATIONS   = 300
HISTORY_DAYS     = 1825
ITER_TIMEOUT     = 1200
HEARTBEAT_SECONDS = 60

os.makedirs(f"{LOCAL_TMP}/output", exist_ok=True)
os.makedirs(f"{LOCAL_TMP}/state",  exist_ok=True)
os.makedirs(f"{LOCAL_TMP}/config", exist_ok=True)
os.makedirs(f"{LOCAL_TMP}/logs",   exist_ok=True)
print(f"✅ Config OK — LAKEHOUSE_FILES={LAKEHOUSE_FILES}")

# ── CELLULE 3 : Chargement des secrets depuis .env dans OneLake ───────────────
def _load_env_file(path):
    with open(path, encoding="utf-8") as f:
        for raw_line in f:
            line = raw_line.strip()
            if not line or line.startswith("#") or "=" not in line:
                continue
            key, value = line.split("=", 1)
            key = key.strip()
            value = value.strip().strip('"').strip("'")
            os.environ[key] = value
 
env_onelake = f"{LAKEHOUSE_FILES}/config/.env"
env_local   = f"{LOCAL_TMP}/config/.env"

try:
    mssparkutils.fs.cp(env_onelake, f"file://{env_local}", False)
    _load_env_file(env_local)
    print("✅ .env chargé depuis OneLake")
except Exception as e:
    raise FileNotFoundError(
        f".env introuvable dans OneLake ({env_onelake}).\n"
        f"→ Uploader votre fichier .env dans ENEDIS_LAKEHOUSE/Files/config/.env\n{e}"
    )

# ── CELLULE 4 : Helpers ───────────────────────────────────────────────────────
def onelake_to_local(onelake_path, local_path):
    os.makedirs(os.path.dirname(local_path), exist_ok=True)
    try:
        mssparkutils.fs.cp(onelake_path, f"file://{local_path}", False)
        print(f"  ✅ Restauré  : {local_path}")
    except Exception:
        print(f"  ⚠️  Absent (ignoré) : {onelake_path}")

def local_to_onelake(local_path, onelake_path, required=True):
    if not os.path.exists(local_path):
        if required:
            raise FileNotFoundError(f"Fichier local introuvable : {local_path}")
        print(f"  ⚠️  Absent (ignoré) : {local_path}")
        return
    crc = os.path.join(os.path.dirname(local_path), f".{os.path.basename(local_path)}.crc")
    if os.path.exists(crc):
        os.remove(crc)
    mssparkutils.fs.cp(f"file://{local_path}", onelake_path, True)
    print(f"  ✅ Sauvegardé : {onelake_path}")

def _get_max_date_from_csv(csv_path, date_col):
    if not os.path.exists(csv_path):
        return None
    max_d = None
    try:
        with open(csv_path, encoding="utf-8-sig", newline="") as f:
            reader = csv.reader(f)
            header = next(reader, None)
            if not header:
                return None
            try:
                idx = header.index(date_col)
            except ValueError:
                return None
            for row in reader:
                if len(row) > idx:
                    try:
                        d = date.fromisoformat(row[idx][:10])
                        if max_d is None or d > max_d:
                            max_d = d
                    except ValueError:
                        pass
    except Exception as exc:
        print(f"  ⚠️  _get_max_date_from_csv({csv_path}) : {exc}")
        return None
    return max_d.isoformat() if max_d else None

def _get_date_from_state(state_path, key):
    if not os.path.exists(state_path):
        return None
    try:
        import json
        with open(state_path, encoding="utf-8-sig") as f:
            state = json.load(f)
        value = state.get(key)
        if not value:
            return None
        return value[:10]
    except Exception as exc:
        print(f"  ⚠️  _get_date_from_state({state_path}, {key}) : {exc}")
        return None

def _max_iso_date(*values):
    dates = [v for v in values if v]
    return max(dates) if dates else None

def _should_echo_subprocess_line(line):
    text = (line or "").strip()
    if not text:
        return False
    markers = (
        "[ERROR]",
        "Traceback",
        "Erreur fatale",
        "=== Run terminé ===",
        "CSV upsert :",
        "--- Collecte",
        "Périmètre total",
        "Token ENEDIS obtenu.",
        "SKIP_CUSTOMER_COLLECTION activé",
        "Consommation :",
        "déjà à jour",
        "aucun point collecté",
    )
    return any(marker in text for marker in markers)

# ── CELLULE 4b : Nettoyage local /tmp ─────────────────────────────────────────
_to_clean = [
    f"{LOCAL_TMP}/output/enedis_data.csv",
    f"{LOCAL_TMP}/state/processed_files.json",
]
for _p in _to_clean:
    if os.path.exists(_p):
        os.remove(_p)
        print(f"  🗑️  Nettoyé localement : {_p}")
    else:
        print(f"  ℹ️  Absent (OK) : {_p}")

# ── CELLULE 5 : Restauration initiale depuis OneLake ─────────────────────────
print("Restauration initiale depuis OneLake…")
onelake_to_local(f"{LAKEHOUSE_FILES}/scripts/enedis_to_powerbi.py",
                 f"{LOCAL_TMP}/enedis_to_powerbi.py")
with open(f"{LOCAL_TMP}/enedis_to_powerbi.py", "r", encoding="utf-8") as f:
    content = f.read()
_required_markers = [
    "SKIP_CUSTOMER_COLLECTION",
    "sync_max_days_per_run",
    "ENABLE_DAILY_CONSUMPTION",
]
_missing_markers = [marker for marker in _required_markers if marker not in content]
if _missing_markers:
    raise ValueError(
        "Le script OneLake enedis_to_powerbi.py est trop ancien pour le backfill robuste. "
        f"Marqueurs absents : {_missing_markers}. "
        "Mettez à jour Files/scripts/enedis_to_powerbi.py avant de relancer le notebook."
    )
print("✅ Script OneLake validé : version backfill robuste détectée")
onelake_to_local(f"{LAKEHOUSE_FILES}/state/processed_files.json",
                 f"{LOCAL_TMP}/state/processed_files.json")
onelake_to_local(f"{LAKEHOUSE_FILES}/config/prm_list.txt",
                 f"{LOCAL_TMP}/config/prm_list.txt")
onelake_to_local(f"{LAKEHOUSE_FILES}/config/enedis_request_template.json",
                 f"{LOCAL_TMP}/config/enedis_request_template.json")
onelake_to_local(f"{LAKEHOUSE_FILES}/output/enedis_data.csv",
                 f"{LOCAL_TMP}/output/enedis_data.csv")
onelake_to_local(f"{LAKEHOUSE_FILES}/output/enedis_contracts.csv",
                 f"{LOCAL_TMP}/output/enedis_contracts.csv")

# ── CELLULE 6 : Boucle de backfill consommation journalière ───────────────────
import subprocess, sys, queue, threading, time as _time

target_date    = (date.today() - timedelta(days=1)).isoformat()
target_start   = (date.today() - timedelta(days=HISTORY_DAYS)).isoformat()
data_csv       = f"{LOCAL_TMP}/output/enedis_data.csv"
state_json     = f"{LOCAL_TMP}/state/processed_files.json"

print(f"Backfill cible : {target_start} → {target_date} ({HISTORY_DAYS}j, tranches {CHUNK_DAYS}j)\n")

for iteration in range(1, MAX_ITERATIONS + 1):
    data_last_csv   = _get_max_date_from_csv(data_csv, "date")
    data_last_state = _get_date_from_state(state_json, "last_sync_date")
    data_last       = _max_iso_date(data_last_csv, data_last_state)

    data_start = (date.fromisoformat(data_last) + timedelta(days=1)).isoformat() if data_last else target_start
    data_done = data_start > target_date

    print(f"── Itération {iteration}/{MAX_ITERATIONS} ──────────────────────────────────────────────")
    print(f"   Consommation : données={data_last_csv or 'aucune'} | curseur={data_last_state or 'jamais'} → {'✅ À JOUR' if data_done else f'reprise depuis {data_start}'}")

    if data_done:
        print(f"\n✅ Backfill complet après {iteration - 1} itération(s) !")
        break

    iteration_log = f"{LOCAL_TMP}/logs/backfill_daily_iteration_{iteration:03d}.log"

    env = os.environ.copy()
    env.update({
        "SYNC_MAX_DAYS_PER_RUN":        str(CHUNK_DAYS),
        "HISTORY_DAYS":                 str(HISTORY_DAYS),
        "ENABLE_LOAD_CURVE":            "false",
        "ENABLE_DAILY_CONSUMPTION":     "true",
        "SKIP_CUSTOMER_COLLECTION":     "1",
        "PYTHONUNBUFFERED":             "1",
        "ALERT_WEBHOOK_URL":            "",
        "PBI_TENANT_ID":               os.getenv("PBI_TENANT_ID",     "stub"),
        "PBI_CLIENT_ID":               os.getenv("PBI_CLIENT_ID",     "stub"),
        "PBI_CLIENT_SECRET":           os.getenv("PBI_CLIENT_SECRET", "stub"),
        "PBI_WORKSPACE_ID":            os.getenv("PBI_WORKSPACE_ID",  "stub"),
        "PBI_DATASET_ID":              os.getenv("PBI_DATASET_ID",    "stub"),
    })

    try:
        print(f"   Lancement subprocess ENEDIS (silence max {ITER_TIMEOUT}s, heartbeat {HEARTBEAT_SECONDS}s)...")

        proc = subprocess.Popen(
            [sys.executable, "-u", f"{LOCAL_TMP}/enedis_to_powerbi.py"],
            env=env, cwd=LOCAL_TMP,
            stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
            text=True, bufsize=1,
        )

        output_queue = queue.Queue()

        def _reader():
            try:
                for line in proc.stdout:
                    output_queue.put(("line", line))
            finally:
                output_queue.put(("eof", None))

        reader_thread = threading.Thread(target=_reader, daemon=True)
        reader_thread.start()

        last_output_at = _time.monotonic()
        last_heartbeat_at = last_output_at
        reader_done = False
        killed_for_silence = False
        suppressed_line_count = 0

        with open(iteration_log, "w", encoding="utf-8") as _logf:
            _logf.write(f"=== Iteration {iteration} ===\n")
            _logf.write(f"consumption_resume={data_start}\n")

            while True:
                try:
                    event_type, payload = output_queue.get(timeout=1)
                    if event_type == "line":
                        last_output_at = _time.monotonic()
                        _logf.write(payload)
                        _logf.flush()
                        if _should_echo_subprocess_line(payload):
                            if suppressed_line_count:
                                print(f"… {suppressed_line_count} ligne(s) de détail masquées (voir log itération).", flush=True)
                                suppressed_line_count = 0
                            print(payload, end="", flush=True)
                        else:
                            suppressed_line_count += 1
                    elif event_type == "eof":
                        reader_done = True
                except queue.Empty:
                    pass

                now_mono = _time.monotonic()
                silent_for = now_mono - last_output_at
                if now_mono - last_heartbeat_at >= HEARTBEAT_SECONDS:
                    state = "running" if proc.poll() is None else f"code={proc.returncode}"
                    hb = f"⏳ Toujours en cours — subprocess {state}, silence depuis {int(silent_for)}s, détails masqués={suppressed_line_count}.\n"
                    print(hb, end="", flush=True)
                    _logf.write(hb)
                    _logf.flush()
                    last_heartbeat_at = now_mono

                if proc.poll() is not None and reader_done and output_queue.empty():
                    break

                if silent_for >= ITER_TIMEOUT and proc.poll() is None:
                    killed_for_silence = True
                    proc.kill()
                    timeout_msg = f"⏱️  Itération interrompue après {int(silent_for)}s sans aucun log.\n"
                    print(timeout_msg, end="", flush=True)
                    _logf.write(timeout_msg)
                    _logf.flush()
                    break

            proc.wait()
            reader_thread.join(timeout=5)
            if suppressed_line_count:
                print(f"… {suppressed_line_count} ligne(s) de détail masquées (voir log itération).", flush=True)

            if killed_for_silence:
                msg = "⚠️  Le subprocess a été arrêté pour silence prolongé — sauvegarde partielle et itération suivante.\n"
                print(msg, end="", flush=True)
                _logf.write(msg)
            elif proc.returncode not in (0, None):
                msg = f"⚠️  Script code={proc.returncode} — erreurs ignorées, on continue.\n"
                print(msg, end="", flush=True)
                _logf.write(msg)
            _logf.flush()
    except Exception as exc:
        print(f"⚠️  Erreur lancement script : {exc} — on continue.")

    print(f"\n  → Sauvegarde itération {iteration} vers OneLake…")
    local_to_onelake(f"{LOCAL_TMP}/output/enedis_data.csv",
                     f"{LAKEHOUSE_FILES}/output/enedis_data.csv", required=False)
    local_to_onelake(f"{LOCAL_TMP}/state/processed_files.json",
                     f"{LAKEHOUSE_FILES}/state/processed_files.json", required=False)
    local_to_onelake(iteration_log,
                     f"{LAKEHOUSE_FILES}/logs/backfill_daily_iteration_{iteration:03d}.log", required=False)
    print()

else:
    print(f"⚠️  Limite de {MAX_ITERATIONS} itérations atteinte — relancer le notebook pour continuer.")

# ── CELLULE 7 : Chargement final dans la Delta table enedis_data ──────────────
from pyspark.sql.types import (
    StructType, StructField, StringType, DoubleType, TimestampType, DateType
)

if mssparkutils.fs.exists(f"{LAKEHOUSE_FILES}/output/enedis_data.csv"):
    schema_data = StructType([
        StructField("usage_point_id",   StringType(),    True),
        StructField("date",             DateType(),      True),
        StructField("value_wh",         DoubleType(),    True),
        StructField("unit",             StringType(),    True),
        StructField("quality",          StringType(),    True),
        StructField("flow_direction",   StringType(),    True),
        StructField("_ingested_at_utc", TimestampType(), True),
    ])
    df_data = spark.read.option("header","true").schema(schema_data).csv(
        f"{LAKEHOUSE_FILES}/output/enedis_data.csv")
    n_data = df_data.count()
    if n_data > 0:
        df_data.write.format("delta").mode("overwrite") \
            .option("overwriteSchema","true") \
            .save(f"{LAKEHOUSE_TABLES}/enedis_data")
        print(f"✅ enedis_data : {n_data:,} lignes chargées.")
    else:
        print("⚠️  enedis_data : CSV vide, ignoré.")
else:
    print("ℹ️  enedis_data : aucun CSV livré — chargement ignoré.")
