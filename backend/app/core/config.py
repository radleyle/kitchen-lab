"""App settings, loaded from environment variables.

Why environment variables? The same code runs on your Mac and in the cloud.
The *environment* supplies what differs (DB password, API keys), so
secrets never live in the code or in git.
"""

from pydantic import field_validator
from pydantic_settings import BaseSettings

# Hosts that don't need SSL: local dev and the Compose network.
_LOCAL_DB_HOSTS = ("localhost", "127.0.0.1", "db")


def normalize_database_url(url: str) -> str:
    """Make pasted Postgres URLs (e.g. from Neon) work with SQLAlchemy.

    Two fixes:
    1. Driver: hosted dashboards hand out "postgresql://..." but SQLAlchemy
       needs "postgresql+psycopg://..." to pick the psycopg 3 driver.
    2. SSL: hosted Postgres (Neon, Supabase, ...) requires an encrypted
       connection. If the host isn't local and no sslmode is set, we add
       sslmode=require so the connection isn't rejected.
    """
    if url.startswith("postgres://"):
        # Legacy Heroku-style scheme some dashboards still emit.
        url = "postgresql://" + url[len("postgres://"):]
    if url.startswith("postgresql://"):
        url = "postgresql+psycopg://" + url[len("postgresql://"):]

    if "sslmode=" not in url:
        # Everything between "@" and the next "/" is host[:port].
        try:
            host_port = url.split("@", 1)[1].split("/", 1)[0]
            host = host_port.rsplit(":", 1)[0]
        except IndexError:
            host = ""
        if host and host not in _LOCAL_DB_HOSTS:
            url += ("&" if "?" in url else "?") + "sslmode=require"
    return url


class Settings(BaseSettings):
    # pydantic-settings reads each field from an env var with the same name,
    # e.g. DATABASE_URL. The value below is only a fallback for local use.
    database_url: str = "postgresql+psycopg://kitchenlab:kitchenlab_dev@localhost:5432/kitchenlab"

    @field_validator("database_url")
    @classmethod
    def _normalize_database_url(cls, v: str) -> str:
        return normalize_database_url(v)

    app_name: str = "KitchenLab"

    # Signs JWTs. The dev fallback below is fine locally; in production this
    # MUST come from the SECRET_KEY env var (a long random string) -- anyone
    # who knows it can forge login tokens.
    secret_key: str = "dev-only-secret-change-in-production"
    access_token_expire_minutes: int = 60 * 24 * 7  # one week

    # From the OPENAI_API_KEY env var (never committed to git).
    openai_api_key: str = ""
    embedding_model: str = "text-embedding-3-small"
    chat_model: str = "gpt-4o-mini"

    # Unsplash Access Key for recipe cover photos (optional — stock fallback if empty).
    unsplash_access_key: str = ""

    # Photo storage: "local" (Compose) or "s3" (ECS).
    storage_backend: str = "local"
    media_root: str = "media"
    s3_bucket: str = ""
    aws_region: str = "us-west-2"

    # Comma-separated browser origins allowed to call the API in production.
    # Example: https://app.example.com,https://www.example.com
    cors_origins: str = "http://localhost:3000,http://localhost:3001"


settings = Settings()
