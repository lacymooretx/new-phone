from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    model_config = {"env_prefix": "NP_"}

    # Database
    db_host: str = "localhost"
    db_port: int = 5432
    db_name: str = "new_phone"
    db_admin_user: str = "new_phone_admin"
    db_admin_password: str = "change_me_admin"
    db_app_user: str = "new_phone_app"
    db_app_password: str = "change_me_app"

    # Redis
    redis_url: str = "redis://localhost:6379/0"

    # JWT
    jwt_secret_key: str = "change-me-to-a-random-64-char-string"
    jwt_algorithm: str = "HS256"
    jwt_access_token_expire_minutes: int = 15
    jwt_refresh_token_expire_days: int = 7

    # FreeSWITCH
    freeswitch_host: str = "localhost"
    freeswitch_esl_port: int = 8021
    freeswitch_esl_password: str = "ClueCon"
    freeswitch_wss_port: int = 7443
    freeswitch_wss_host: str = "localhost"  # FreeSWITCH container hostname (internal)
    freeswitch_wss_url: str = ""  # Browser-accessible WSS URL (e.g. wss://ucc.aspendora.com/wss). If empty, uses /wss relative path.

    # API
    api_host: str = "0.0.0.0"
    api_port: int = 8000
    debug: bool = False
    log_level: str = "INFO"

    # MFA
    mfa_issuer: str = "NewPhone"

    # Auth
    max_failed_login_attempts: int = 5
    lockout_duration_minutes: int = 15

    # Rate limiting
    rate_limit_default: str = "100/minute"
    rate_limit_auth: str = "10/minute"

    # CORS
    cors_allowed_origins: str = ""

    # Metrics
    metrics_token: str = ""

    # SIP Trunk encryption (Fernet key — generate with Fernet.generate_key())
    trunk_encryption_key: str = "change-me-generate-with-fernet"

    # Phone Provisioning
    provisioning_sip_server: str = "pbx.example.com"
    provisioning_ntp_server: str = "pool.ntp.org"
    provisioning_timezone: str = "America/New_York"

    # MinIO (object storage for recordings, voicemail, fax)
    minio_endpoint: str = "localhost:9000"
    minio_access_key: str = "minioadmin"
    minio_secret_key: str = "minioadmin"
    minio_bucket: str = "recordings"
    minio_archive_bucket: str = "recordings-archive"
    minio_secure: bool = False

    # SSO
    sso_callback_url: str = "http://localhost:8000/api/v1/auth/sso/callback"
    sso_frontend_url: str = "http://localhost:5173"
    sso_state_ttl_seconds: int = 600

    # AI Engine
    ai_engine_url: str = "http://localhost:8091"

    # Telephony Providers
    clearlyip_keycode: str = ""
    twilio_account_sid: str = ""
    twilio_auth_token: str = ""

    # SMTP (voicemail-to-email)
    smtp_host: str = "localhost"
    smtp_port: int = 1025
    smtp_user: str = ""
    smtp_password: str = ""
    smtp_from_address: str = "voicemail@newphone.local"
    smtp_attach_audio: bool = True

    @property
    def admin_database_url(self) -> str:
        return (
            f"postgresql+asyncpg://{self.db_admin_user}:{self.db_admin_password}"
            f"@{self.db_host}:{self.db_port}/{self.db_name}"
        )

    @property
    def app_database_url(self) -> str:
        return (
            f"postgresql+asyncpg://{self.db_app_user}:{self.db_app_password}"
            f"@{self.db_host}:{self.db_port}/{self.db_name}"
        )


settings = Settings()
