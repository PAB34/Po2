# =============================================================================
# Fabric Notebook — ENEDIS Collecte Données Client (contrats, adresses, …)
# Workspace : ENEDIS  |  Lakehouse : ENEDIS_LAKEHOUSE
# =============================================================================
# Ce notebook exécute la collecte des 6 API "customer" ENEDIS :
#   - /contract/v1              → enedis_contracts.csv
#   - /address/v1               → enedis_addresses.csv
#   - /connection/v1            → enedis_connections.csv
#   - /contract_summary/v1      → enedis_contract_summary.csv
#   - /alimentation_auto/v1     → enedis_alimentation.csv
#   - /situation_contrat_auto/v1 → enedis_situation_contrat.csv
#
# Il ne collecte NI la consommation journalière NI la courbe de charge NI la puissance max.
# À lancer indépendamment des notebooks backfill load curve / daily consumption.
# =============================================================================

# ── CELLULE 1 : Installation des dépendances ─────────────────────────────────
%pip install cryptography python-dotenv --quiet

# ── CELLULE 2 : Configuration ─────────────────────────────────────────────────
import os
from notebookutils import mssparkutils

WORKSPACE_ID     = "d7959e21-626e-42c4-87f6-a6e79ece7c42"
LAKEHOUSE_ID     = "a9b125bc-cf18-41fc-a4f2-1a8918bbb4e3"
ONELAKE_BASE     = f"abfss://{WORKSPACE_ID}@onelake.dfs.fabric.microsoft.com/{LAKEHOUSE_ID}"
LAKEHOUSE_FILES  = f"{ONELAKE_BASE}/Files"
LAKEHOUSE_TABLES = f"{ONELAKE_BASE}/Tables"
LOCAL_TMP        = "/tmp/enedis"

ITER_TIMEOUT     = 600
HEARTBEAT_SECONDS = 30

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
        "customer_contract",
        "customer_address",
        "customer_connection",
        "customer_contract_summary",
        "customer_alimentation",
        "customer_situation_contrat",
        "aucune donnée collectée",
        "OK,",
        "ligne(s)",
    )
    return any(marker in text for marker in markers)

# ── CELLULE 5 : Restauration initiale depuis OneLake ─────────────────────────
print("Restauration initiale depuis OneLake…")
onelake_to_local(f"{LAKEHOUSE_FILES}/scripts/enedis_to_powerbi.py",
                 f"{LOCAL_TMP}/enedis_to_powerbi.py")
with open(f"{LOCAL_TMP}/enedis_to_powerbi.py", "r", encoding="utf-8") as f:
    content = f.read()
_required_markers = [
    "SKIP_CUSTOMER_COLLECTION",
    "FORCE_CUSTOMER_COLLECTION",
    "ENABLE_DAILY_CONSUMPTION",
    "ENABLE_LOAD_CURVE",
]
_missing_markers = [marker for marker in _required_markers if marker not in content]
if _missing_markers:
    raise ValueError(
        "Le script OneLake enedis_to_powerbi.py est trop ancien. "
        f"Marqueurs absents : {_missing_markers}. "
        "Mettez à jour Files/scripts/enedis_to_powerbi.py avant de relancer le notebook."
    )
print("✅ Script OneLake validé")
onelake_to_local(f"{LAKEHOUSE_FILES}/state/processed_files.json",
                 f"{LOCAL_TMP}/state/processed_files.json")
onelake_to_local(f"{LAKEHOUSE_FILES}/config/prm_list.txt",
                 f"{LOCAL_TMP}/config/prm_list.txt")
onelake_to_local(f"{LAKEHOUSE_FILES}/config/enedis_request_template.json",
                 f"{LOCAL_TMP}/config/enedis_request_template.json")
# Restaurer les CSV customer existants pour permettre upsert (ajout nouveaux PRMs)
for _csv in ["enedis_contracts", "enedis_addresses", "enedis_connections", "enedis_contract_summary",
             "enedis_alimentation", "enedis_situation_contrat"]:
    onelake_to_local(f"{LAKEHOUSE_FILES}/output/{_csv}.csv",
                     f"{LOCAL_TMP}/output/{_csv}.csv")

# ── CELLULE 6 : Exécution collecte données client ─────────────────────────────
import subprocess, sys, queue, threading, time as _time

CUSTOMER_CSVS = [
    "enedis_contracts",
    "enedis_addresses",
    "enedis_connections",
    "enedis_contract_summary",
    "enedis_alimentation",
    "enedis_situation_contrat",
]

print("Lancement de la collecte données client (contrats, adresses, connexions, résumé contrats, alimentation, situation contrat)…\n")

iteration_log = f"{LOCAL_TMP}/logs/collect_customer_data.log"

env = os.environ.copy()
env.update({
    "ENABLE_LOAD_CURVE":            "false",
    "ENABLE_DAILY_CONSUMPTION":     "false",
    "ENABLE_MAX_POWER":             "false",
    "SKIP_CUSTOMER_COLLECTION":     "",        # NE PAS SKIPPER — c'est le but de ce notebook
    "FORCE_CUSTOMER_COLLECTION":    "true",    # Forcer la collecte même si CSV déjà existants
    "PYTHONUNBUFFERED":             "1",
    "ALERT_WEBHOOK_URL":            "",
    "PBI_TENANT_ID":               os.getenv("PBI_TENANT_ID",     "stub"),
    "PBI_CLIENT_ID":               os.getenv("PBI_CLIENT_ID",     "stub"),
    "PBI_CLIENT_SECRET":           os.getenv("PBI_CLIENT_SECRET", "stub"),
    "PBI_WORKSPACE_ID":            os.getenv("PBI_WORKSPACE_ID",  "stub"),
    "PBI_DATASET_ID":              os.getenv("PBI_DATASET_ID",    "stub"),
})

try:
    print(f"   Lancement subprocess ENEDIS (timeout silence {ITER_TIMEOUT}s, heartbeat {HEARTBEAT_SECONDS}s)...")

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
        _logf.write("=== Collecte customer data ===\n")

        while True:
            try:
                event_type, payload = output_queue.get(timeout=1)
                if event_type == "line":
                    last_output_at = _time.monotonic()
                    _logf.write(payload)
                    _logf.flush()
                    if _should_echo_subprocess_line(payload):
                        if suppressed_line_count:
                            print(f"… {suppressed_line_count} ligne(s) de détail masquées (voir log).", flush=True)
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
                hb = f"⏳ subprocess {state}, silence {int(silent_for)}s, masqués={suppressed_line_count}\n"
                print(hb, end="", flush=True)
                _logf.write(hb)
                _logf.flush()
                last_heartbeat_at = now_mono

            if proc.poll() is not None and reader_done and output_queue.empty():
                break

            if silent_for >= ITER_TIMEOUT and proc.poll() is None:
                killed_for_silence = True
                proc.kill()
                timeout_msg = f"⏱️  Subprocess interrompu après {int(silent_for)}s sans log.\n"
                print(timeout_msg, end="", flush=True)
                _logf.write(timeout_msg)
                _logf.flush()
                break

        proc.wait()
        reader_thread.join(timeout=5)
        if suppressed_line_count:
            print(f"… {suppressed_line_count} ligne(s) de détail masquées (voir log).", flush=True)

        if killed_for_silence:
            print("⚠️  Le subprocess a été arrêté pour silence prolongé.")
        elif proc.returncode not in (0, None):
            print(f"⚠️  Script terminé avec code={proc.returncode}")
        else:
            print("✅ Collecte customer terminée avec succès.")
        _logf.flush()
except Exception as exc:
    print(f"⚠️  Erreur lancement script : {exc}")

# ── Sauvegarde vers OneLake ──
print("\n→ Sauvegarde des CSV customer vers OneLake…")
for _csv in CUSTOMER_CSVS:
    local_to_onelake(f"{LOCAL_TMP}/output/{_csv}.csv",
                     f"{LAKEHOUSE_FILES}/output/{_csv}.csv", required=False)
local_to_onelake(f"{LOCAL_TMP}/state/processed_files.json",
                 f"{LAKEHOUSE_FILES}/state/processed_files.json", required=False)
local_to_onelake(iteration_log,
                 f"{LAKEHOUSE_FILES}/logs/collect_customer_data.log", required=False)

# ── CELLULE 7 : Chargement Delta tables ───────────────────────────────────────
# Tables petites (quelques centaines de lignes), colonnes dynamiques — inferSchema OK.
print("\nChargement des tables client dans le Lakehouse…")

loaded = 0
for name in CUSTOMER_CSVS:
    csv_path = f"{LAKEHOUSE_FILES}/output/{name}.csv"
    if mssparkutils.fs.exists(csv_path):
        df = spark.read.option("header", "true").option("inferSchema", "true").csv(csv_path)
        n = df.count()
        if n > 0:
            df.write.format("delta") \
                .mode("overwrite") \
                .option("overwriteSchema", "true") \
                .save(f"{LAKEHOUSE_TABLES}/{name}")
            print(f"  ✅ {name} : {n:,} lignes chargées.")
            loaded += 1
        else:
            print(f"  ⚠️  {name} : CSV vide, ignoré.")
    else:
        print(f"  ℹ️  {name} : aucun CSV livré — chargement ignoré.")

if loaded > 0:
    print(f"\n✅ {loaded} table(s) client chargée(s) dans ENEDIS_LAKEHOUSE/Tables/")
else:
    print("\n⚠️  Aucune table client chargée — vérifier les logs ci-dessus.")
