from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8")

    database_url: str = "postgresql+asyncpg://postgres:postgres@localhost:5432/worldcup"
    football_api_provider: str = "mock"
    environment: str = "development"
    allowed_origins: str = "http://localhost:5173"

    @property
    def database_url_clean(self) -> str:
        """URL with sslmode stripped — asyncpg takes SSL via connect_args."""
        url = self.database_url
        url = url.replace("?sslmode=require", "").replace("&sslmode=require", "")
        url = url.replace("?channel_binding=require&", "?").replace("&channel_binding=require", "").replace("?channel_binding=require", "")
        return url

    @property
    def database_connect_args(self) -> dict:
        return {"ssl": "require"} if "neon.tech" in self.database_url else {}

    @property
    def is_production(self) -> bool:
        return self.environment == "production"

    @property
    def origins_list(self) -> list[str]:
        return [o.strip() for o in self.allowed_origins.split(",")]


settings = Settings()
