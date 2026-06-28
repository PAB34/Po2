"""
Stockage utilisateur minimal (sqlite, stdlib).

Accès strictement privé : un seul compte, créé au démarrage depuis les variables
d'environnement PRONO_ADMIN_EMAIL / PRONO_ADMIN_PASSWORD. Aucune inscription
publique. C'est l'équivalent « privé pour moi uniquement ».
"""
import sqlite3

from app.config import settings
from app.security import get_password_hash

_conn = None


def _connect():
    global _conn
    if _conn is None:
        _conn = sqlite3.connect(settings.db_path, check_same_thread=False)
        _conn.row_factory = sqlite3.Row
        _conn.execute(
            "CREATE TABLE IF NOT EXISTS users ("
            "id INTEGER PRIMARY KEY AUTOINCREMENT,"
            "email TEXT UNIQUE NOT NULL,"
            "password_hash TEXT NOT NULL,"
            "is_active INTEGER NOT NULL DEFAULT 1)"
        )
        _conn.commit()
    return _conn


def init_db_and_seed():
    """Crée la base et le compte admin unique si absent."""
    conn = _connect()
    email = (settings.admin_email or "").strip().lower()
    if not email or not settings.admin_password:
        return  # rien à seeder (à configurer via .env)
    row = conn.execute("SELECT id FROM users WHERE email=?", (email,)).fetchone()
    if row is None:
        conn.execute(
            "INSERT INTO users(email, password_hash, is_active) VALUES (?,?,1)",
            (email, get_password_hash(settings.admin_password)),
        )
        conn.commit()


def get_user_by_email(email: str):
    return _connect().execute(
        "SELECT * FROM users WHERE email=?", ((email or "").strip().lower(),)).fetchone()


def get_user_by_id(user_id: int):
    return _connect().execute("SELECT * FROM users WHERE id=?", (user_id,)).fetchone()
