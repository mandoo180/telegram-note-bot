"""Configuration management."""

import os
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()


class Config:
    """Application configuration."""

    # Telegram Bot Token
    TELEGRAM_BOT_TOKEN = os.getenv('TELEGRAM_BOT_TOKEN')

    # Database
    DATABASE_PATH = os.getenv('DATABASE_PATH', 'telegram_note.db')

    # Web App
    WEBAPP_BASE_URL = os.getenv('WEBAPP_BASE_URL', 'http://localhost:8000')
    WEBAPP_PORT = int(os.getenv('WEBAPP_PORT', '8000'))

    @classmethod
    def validate(cls):
        """Validate required configuration.

        Raises:
            ValueError: If required configuration is missing
        """
        if not cls.TELEGRAM_BOT_TOKEN:
            raise ValueError(
                "TELEGRAM_BOT_TOKEN is required. "
                "Please set it in .env file or environment variable."
            )
