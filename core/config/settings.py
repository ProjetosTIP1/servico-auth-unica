import os
from dotenv import load_dotenv
from urllib.parse import quote_plus
from pydantic_settings import BaseSettings, SettingsConfigDict

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
ENV_PATH = os.path.join(BASE_DIR, ".env")

if os.path.exists(ENV_PATH):
    load_dotenv(ENV_PATH)
else:
    print(f".env file not found at {ENV_PATH}, proceeding without it.")

class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=ENV_PATH, env_file_encoding="utf-8")
    
    DEVELOPMENT_ENV: bool = os.getenv("DEVELOPMENT_ENV", "False").lower() in ("true", "1", "yes")
    DEBUG: bool = os.getenv("DEBUG", "False").lower() in ("true", "1", "yes")

settings = Settings()