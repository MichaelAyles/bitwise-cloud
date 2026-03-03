from pydantic import model_validator
from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    database_url: str = "postgresql+asyncpg://bitwise:bitwise@localhost:5432/bitwise"
    sync_database_url: str = "postgresql://bitwise:bitwise@localhost:5432/bitwise"
    redis_url: str = "redis://localhost:6379/0"

    jwt_secret: str = "CHANGE_ME"
    jwt_algorithm: str = "HS256"
    access_token_expire_minutes: int = 15
    refresh_token_expire_days: int = 7

    upload_dir: str = "/data/uploads"
    index_dir: str = "/data/indices"
    max_upload_size_mb: int = 100

    embedding_model: str = "BAAI/bge-small-en-v1.5"
    public_host: str = "https://bitwise.your-tailscale.ts.net"

    rate_limit_search: str = "60/minute"
    rate_limit_upload: str = "10/hour"

    shoo_issuer: str = "https://shoo.dev"
    shoo_jwks_url: str = "https://shoo.dev/.well-known/jwks.json"

    model_config = {"env_file": ".env"}

    @model_validator(mode="after")
    def validate_jwt_secret(self) -> "Settings":
        if self.jwt_secret == "CHANGE_ME" or len(self.jwt_secret) < 32:
            raise ValueError(
                "jwt_secret must be at least 32 characters and not the default 'CHANGE_ME'. "
                "Set JWT_SECRET in your environment or .env file."
            )
        return self


settings = Settings()
