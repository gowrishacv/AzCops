from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    """Application settings loaded from environment variables."""

    # Database
    database_url: str = "postgresql+asyncpg://azcops:azcops_dev_password@localhost:5432/azcops"

    # Azure Identity
    azure_tenant_id: str = ""
    azure_client_id: str = ""
    azure_client_secret: str = ""

    # Azure Key Vault
    azure_keyvault_uri: str = ""

    # Azure Data Lake (raw storage)
    azure_storage_account_name: str = ""
    azure_storage_container_name: str = "raw"

    # API
    log_level: str = "INFO"
    cors_origins: list[str] = ["http://localhost:3000"]
    api_prefix: str = "/api/v1"

    # Auth
    auth_enabled: bool = True
    auth_audience: str = ""
    auth_issuer: str = ""

    model_config = {"env_file": ".env", "env_file_encoding": "utf-8"}


settings = Settings()
