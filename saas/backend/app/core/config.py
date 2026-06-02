from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", case_sensitive=False)

    app_name: str = "PatrimoineOp API"
    app_version: str = "0.1.0"
    database_url: str = "postgresql+psycopg://patrimoineop:patrimoineop@db:5432/patrimoineop"
    backend_cors_origins: str = "http://localhost:5173,http://127.0.0.1:5173"
    dgfip_majic_file_path: str = ""
    energie_dir: str = "/workspace/saas/energie/output"
    invoice_storage_dir: str = "/app/storage/invoices"
    secret_key: str = "change-this-secret-key-in-production"
    algorithm: str = "HS256"
    access_token_expire_minutes: int = 1440
    jwt_token_prefix: str = "Bearer"
    jwt_header_name: str = "Authorization"

    # Jeu de pronostics Coupe du Monde
    football_data_token: str = ""
    football_data_base_url: str = "https://api.football-data.org/v4"
    football_data_competition: str = "WC"
    football_data_season: int = 2026
    pronostics_score_sync_enabled: bool = True
    pronostics_score_sync_interval_hours: int = 6
    pronostics_app_url: str = "https://patrimoineaucarre.com/pronostics"
    pronostics_reset_expire_minutes: int = 30
    smtp_host: str = ""
    smtp_port: int = 587
    smtp_username: str = ""
    smtp_password: str = ""
    smtp_from_email: str = ""
    smtp_starttls: bool = True

    # ENEDIS API
    enedis_auth_url: str = "https://ext.prod.api.enedis.fr/oauth2/v3/token"
    enedis_base_url: str = "https://gw.ext.prod.api.enedis.fr"
    enedis_sync_url: str = "https://gw.ext.prod.api.enedis.fr/mesures/v2/metering_data/daily_consumption"
    enedis_max_power_url: str = "https://gw.ext.prod.api.enedis.fr/mesures/v2/metering_data/daily_consumption_max_power"
    enedis_load_curve_url: str = "https://gw.ext.prod.api.enedis.fr/mesures/v2/metering_data/consumption_load_curve"
    enedis_perimeter_url: str = "https://gw.ext.prod.api.enedis.fr/usage_point_id_perimeter/v1/usage_point_id"
    enedis_load_curve_start: str = "2026-01-01"  # date de début historique courbe de charge
    enedis_client_id: str = ""
    enedis_client_secret: str = ""
    enedis_history_days: int = 1095  # 3 ans — limite API 36 mois
    enedis_customer_sync_enabled: bool = True
    enedis_customer_sync_interval_hours: int = 168  # hebdomadaire

    # ENEDIS Async (commanderPublicationPonctuelle)
    enedis_async_url: str = (
        "https://gw.ext.prod.api.enedis.fr/publication_mesures/v1/commanderPublicationPonctuelle"
    )
    enedis_canal_contact_id: str = ""  # ID du canal de contact (ex: "506350699")
    enedis_decryption_key: str = ""  # clé hex AES-256 (64 chars)
    enedis_async_max_prms_per_request: int = 1000
    enedis_async_cdc_max_days: int = 730  # ENEDIS : CDC profondeur max 2 ans
    enedis_async_energie_max_days: int = 1095  # ENEDIS : ENERGIE profondeur max 3 ans
    enedis_async_poll_interval_minutes: int = 5

    # ENGIE API (Entreprises & Collectivités) — Azure APIM
    engie_base_url: str = "https://api.entreprises-collectivites.engie.fr/ec/v1"
    engie_subscription_key: str = ""  # Ocp-Apim-Subscription-Key

    # FTP — serveur de réception des publications ENEDIS (canal de contact)
    ftp_host: str = ""
    ftp_port: int = 21
    ftp_user: str = ""
    ftp_password: str = ""
    ftp_remote_dir: str = "/upload"
    ftp_passive_mode: bool = True
    ftp_local_incoming_dir: str = "/tmp/enedis_async/incoming"

    @property
    def cors_origins(self) -> list[str]:
        return [origin.strip() for origin in self.backend_cors_origins.split(",") if origin.strip()]


@lru_cache
def get_settings() -> Settings:
    return Settings()


settings = get_settings()
