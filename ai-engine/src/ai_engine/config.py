from pydantic_settings import BaseSettings


class AIEngineSettings(BaseSettings):
    model_config = {"env_prefix": "NP_AI_"}

    ws_host: str = "0.0.0.0"
    ws_port: int = 8090
    api_host: str = "0.0.0.0"
    api_port: int = 8091
    db_host: str = "postgres"
    db_port: int = 5432
    db_name: str = "new_phone"
    db_admin_user: str = "new_phone_admin"
    db_admin_password: str = "change_me_admin"
    redis_url: str = "redis://redis:6379/0"
    encryption_key: str = ""
    api_base_url: str = "http://api:8000"
    audio_format: str = "ulaw"
    sample_rate: int = 8000
    chunk_ms: int = 20
    log_level: str = "INFO"

    @property
    def database_url(self) -> str:
        return (
            f"postgresql+asyncpg://{self.db_admin_user}:{self.db_admin_password}"
            f"@{self.db_host}:{self.db_port}/{self.db_name}"
        )


settings = AIEngineSettings()
