from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    postgres_host: str = "localhost"
    postgres_port: int = 5432
    postgres_user: str = "selflearn"
    postgres_password: str = "selflearn_dev"
    postgres_db: str = "selflearn"
    redis_url: str = "redis://localhost:6379/0"
    qdrant_url: str = "http://localhost:6333"
    minio_endpoint: str = "localhost:9000"
    minio_access_key: str = "selflearn"
    minio_secret_key: str = "selflearn_dev"
    minio_bucket: str = "selflearn"
    rabbitmq_url: str = "amqp://guest:guest@localhost:5672/"
    otel_service_name: str = "selflearn"
    otel_exporter_otlp_endpoint: str = "http://localhost:4317"
    llm_default_provider: str = "mock"
    llm_openai_compat_base_url: str = "https://api.deepseek.com/v1"
    llm_openai_compat_api_key: str = ""
    llm_openai_compat_model: str = "deepseek-chat"
    gateway_host: str = "0.0.0.0"
    gateway_port: int = 8000
    log_level: str = "INFO"
    # Stage 4: AOP /debug/state 路由挂载开关（spec § 10.7 + plan T1）
    debug: bool = False

    @property
    def postgres_dsn(self) -> str:
        return (f"postgresql+asyncpg://{self.postgres_user}:{self.postgres_password}"
                f"@{self.postgres_host}:{self.postgres_port}/{self.postgres_db}")


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    return Settings()