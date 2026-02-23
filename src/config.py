import logging
from typing import List, Optional
from pydantic_settings import BaseSettings, SettingsConfigDict

class Settings(BaseSettings):
    """
    Application settings loaded from .env file.
    """
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore"
    )

    bot_token: str
    gemini_api_key: str
    database_url: str = "sqlite+aiosqlite:///./db.sqlite3"
    
    allowed_telegram_ids_str: Optional[str] = ""

    bot_mode: str = "polling" # "polling" or "webhook"
    webhook_base_url: Optional[str] = None
    webhook_path: Optional[str] = None

    redis_host: str = "localhost"
    redis_port: int = 6379

    log_level: str = "INFO"

    @property
    def allowed_telegram_ids(self) -> List[int]:
        if not self.allowed_telegram_ids_str:
            return []
        try:
            return [int(user_id.strip()) for user_id in self.allowed_telegram_ids_str.split(",")]
        except ValueError:
            logging.error("Invalid format for ALLOWED_TELEGRAM_IDS. Should be comma-separated integers.")
            return []


# Load settings
settings = Settings()

# Configure logging
logging.basicConfig(
    level=settings.log_level,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)
