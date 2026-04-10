from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    anthropic_api_key: str = ""
    database_url: str = "postgresql+asyncpg://daitaview:daitaview@db:5432/daitaview"
    secret_key: str = "change-me"
    access_token_expire_minutes: int = 480
    auth_mode: str = "local"  # local | oidc | saml
    sso_provider_url: str = ""
    sso_client_id: str = ""
    sso_client_secret: str = ""
    sso_redirect_uri: str = ""
    superadmin_email: str = "admin@example.com"
    superadmin_password: str = "change-me"
    execution_service_url: str = "http://execution:8001"
    vector_store_path: str = "/app/vector_store"
    uploads_path: str = "/app/uploads"
    knowledge_path: str = "/app/knowledge"
    execution_timeout_seconds: int = 30
    execution_memory_limit_mb: int = 512
    max_upload_size_mb: int = 500

    class Config:
        env_file = ".env"
        case_sensitive = False


settings = Settings()
