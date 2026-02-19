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
    API_URL: str = os.getenv("API_URL", "http://localhost:8000")
    AUTH_TOKEN: str = os.getenv("AUTH_TOKEN", "your_auth_token_here")
    TASK_POLL_INTERVAL: int = int(os.getenv("TASK_POLL_INTERVAL", "10"))
    MAX_CONCURRENT_REQUESTS: int = int(os.getenv("MAX_CONCURRENT_REQUESTS", "5"))
    IMAGES_UPLOAD_DIR: str = os.getenv("IMAGES_UPLOAD_DIR", "images")
    MAX_CONCURRENT_REQUESTS: int = int(os.getenv("MAX_CONCURRENT_REQUESTS", "5"))
    TASK_POLL_INTERVAL: int = int(os.getenv("TASK_POLL_INTERVAL", "10"))
    ACCESS_TOKEN_EXPIRE_MINUTES: int = int(os.getenv("ACCESS_TOKEN_EXPIRE_MINUTES", "30"))
    
    MARIADB_HOST: str = os.getenv("MARIADB_HOST", "your_mariadb_host")
    MARIADB_PORT: int = int(os.getenv("MARIADB_PORT", "3306"))
    MARIADB_USER: str = os.getenv("MARIADB_USER", "your_mariadb_user")
    MARIADB_PASSWORD: str = os.getenv("MARIADB_PASSWORD", "your_mariadb_password")
    MARIADB_DB: str = os.getenv("MARIADB_DB", "your_mariadb_db")
    SQLSERVER_USER: str = os.getenv("SQLSERVER_USER", "your_sqlserver_user")
    SQLSERVER_PASSWORD: str = os.getenv("SQLSERVER_PASSWORD", "your_sqlserver_password")
    SQLSERVER_DB: str = os.getenv("SQLSERVER_DB", "your_sqlserver_db")
    SQLSERVER_HOST: str = os.getenv("SQLSERVER_HOST", "your_sqlserver_host")
    SQLSERVER_PORT: int = int(os.getenv("SQLSERVER_PORT", "1433"))
    SQLSERVER_DRIVER: str = os.getenv("SQLSERVER_DRIVER", "your_sqlserver_driver")
    SQLSERVER_TRUST_SERVER_CERTIFICATE: str = os.getenv("SQLSERVER_TRUST_SERVER_CERTIFICATE", "yes")
    SQLSERVER_ENCRYPT: str = os.getenv("SQLSERVER_ENCRYPT", "yes")
    REDIS_HOST: str = os.getenv("REDIS_HOST", "your_redis_host")
    REDIS_PORT: int = int(os.getenv("REDIS_PORT", "6379"))
    REDIS_DB: int = int(os.getenv("REDIS_DB", "0"))
    REDIS_PASSWORD: str = os.getenv("REDIS_PASSWORD", "your_redis_password")

    WHATSAPP_API_URL: str = os.getenv("WHATSAPP_API_URL", "your_whatsapp_api_url")
    WHATSAPP_API_TOKEN: str = os.getenv("WHATSAPP_API_TOKEN", "your_whatsapp_api_token")
    
    @property
    def database_url(self) -> str:
        """MariaDB connection URL with properly encoded credentials."""
        user = quote_plus(self.MARIADB_USER)
        password = quote_plus(self.MARIADB_PASSWORD)
        return (
            f"mariadb+mariadbconnector://{user}:{password}"
            f"@{self.MARIADB_HOST}:{self.MARIADB_PORT}/{self.MARIADB_DB}"
        )
    
    @property
    def redis_url(self) -> str:
        """Redis connection URL with properly encoded password."""
        password = quote_plus(self.REDIS_PASSWORD)
        return f"redis://:{password}@{self.REDIS_HOST}:{self.REDIS_PORT}/{self.REDIS_DB}"
    
    @property
    def sqlserver_url(self) -> str:
        """SQL Server ODBC connection string (no URL encoding needed for ODBC)."""
        return (
            f"DRIVER={{{self.SQLSERVER_DRIVER}}};"
            f"SERVER={self.SQLSERVER_HOST};"
            f"DATABASE={self.SQLSERVER_DB};"
            f"UID={self.SQLSERVER_USER};"
            f"PWD={self.SQLSERVER_PASSWORD};"
            f"Encrypt={self.SQLSERVER_ENCRYPT};"
            f"TrustServerCertificate={self.SQLSERVER_TRUST_SERVER_CERTIFICATE}"
        )

settings = Settings()