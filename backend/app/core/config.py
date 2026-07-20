"""App settings, loaded from environment variables.

Why environment variables? The same code runs on your Mac and on AWS.
The *environment* supplies what differs (DB password, API keys), so
secrets never live in the code or in git.
"""

from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    # pydantic-settings reads each field from an env var with the same name,
    # e.g. DATABASE_URL. The value below is only a fallback for local use.
    database_url: str = "postgresql+psycopg://kitchenlab:kitchenlab_dev@localhost:5432/kitchenlab"

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
