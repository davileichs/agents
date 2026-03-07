from typing import Optional
from pydantic_settings import BaseSettings

class Settings(BaseSettings):
    api_key: str
    llm: str = "openai"
    llm_model: str = "gpt-4o-mini"
    llm_api_key: str
    llm_api_base: Optional[str] = None

    class Config:
        env_file = ".env"
        extra = "allow"

settings = Settings()
