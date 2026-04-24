from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", case_sensitive=False)

    app_name: str = "PatrimoineOp API"
    app_version: str = "0.1.0"
    database_url: str = "postgresql+psycopg://patrimoineop:patrimoineop@db:5432/patrimoineop"
    backend_cors_origins: str = "http://localhost:5173,http://127.0.0.1:5173"
    dgfip_majic_file_path: str = ""
    secret_key: str = "change-this-secret-key-in-production"
    algorithm: str = "HS256"
    access_token_expire_minutes: int = 1440
    jwt_token_prefix: str = "Bearer"
    jwt_header_name: str = "Authorization"

    @property
    def cors_origins(self) -> list[str]:
        return [origin.strip() for origin in self.backend_cors_origins.split(",") if origin.strip()]


@lru_cache
def get_settings() -> Settings:
    return Settings()


settings = get_settings()
