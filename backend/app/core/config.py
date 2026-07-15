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


settings = Settings()
