"""Paramètres du backend PRONO (via variables d'environnement)."""
import os


class Settings:
    app_name = "PRONO Ligue 1 API"
    app_version = "1.0.0"

    # Auth (même schéma que le backend saas : JWT HS256 + bcrypt)
    secret_key = os.environ.get("PRONO_SECRET_KEY", "change-me-in-prod")
    algorithm = "HS256"
    access_token_expire_minutes = int(os.environ.get("PRONO_TOKEN_MINUTES", "1440"))

    # Compte privé unique (seul utilisateur autorisé). Pas d'inscription publique.
    admin_email = os.environ.get("PRONO_ADMIN_EMAIL", "")
    admin_password = os.environ.get("PRONO_ADMIN_PASSWORD", "")

    # Base utilisateurs (sqlite) dans le volume de données.
    from app.ligue1.config import DATA_DIR
    db_path = os.path.join(DATA_DIR, "users.db")

    # CORS (origines autorisées, séparées par des virgules)
    cors_origins = [o.strip() for o in os.environ.get(
        "PRONO_CORS_ORIGINS", "http://localhost:5000,http://127.0.0.1:5000").split(",") if o.strip()]


settings = Settings()
