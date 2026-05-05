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

    # ENEDIS API
    enedis_auth_url: str = "https://ext.prod.api.enedis.fr/oauth2/v3/token"
    enedis_base_url: str = "https://gw.ext.prod.api.enedis.fr"
    enedis_sync_url: str = "https://gw.ext.prod.api.enedis.fr/mesures/v2/metering_data/daily_consumption"
    enedis_max_power_url: str = "https://gw.ext.prod.api.enedis.fr/mesures/v2/metering_data/daily_consumption_max_power"
    enedis_load_curve_url: str = "https://gw.ext.prod.api.enedis.fr/mesures/v2/metering_data/consumption_load_curve"
    enedis_load_curve_start: str = "2026-01-01"  # date de début historique courbe de charge
    enedis_client_id: str = ""
    enedis_client_secret: str = ""
    enedis_history_days: int = 1095  # 3 ans — limite API 36 mois

    @property
    def cors_origins(self) -> list[str]:
        return [origin.strip() for origin in self.backend_cors_origins.split(",") if origin.strip()]


@lru_cache
def get_settings() -> Settings:
    return Settings()


settings = get_settings()
