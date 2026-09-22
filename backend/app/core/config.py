from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    anthropic_api_key: str = ""
    anthropic_model: str = "claude-opus-5"
    ai_max_tool_calls: int = 5
    database_url: str = "sqlite:///./app.db"
    upload_dir: str = "./uploads"
    cors_origins: str = "http://localhost:5173"

    @property
    def ai_available(self) -> bool:
        return bool(self.anthropic_api_key.strip())

    @property
    def cors_origin_list(self) -> list[str]:
        return [o.strip() for o in self.cors_origins.split(",") if o.strip()]


settings = Settings()
