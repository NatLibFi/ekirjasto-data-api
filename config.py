from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    POSTGRES_URL: str = ""
    OPENSEARCH_URL: str = ""
    OPENSEARCH_EVENT_INDEX: str = ""

    class Config:
        env_file = ".env"


settings = Settings()
