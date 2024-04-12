from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    POSTGRES_URL: str = ""
    OPENSEARCH_URL: str = ""
    OPENSEARCH_EVENT_INDEX: str = ""

    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8")


settings = Settings()
