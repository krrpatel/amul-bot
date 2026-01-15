"""Application configuration and logging setup."""

from __future__ import annotations

import logging
import os
from typing import Dict, Optional

from dotenv import load_dotenv

load_dotenv()

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s",
    handlers=[logging.StreamHandler()],
)


class Config:
    """Configuration values sourced from the environment."""
    
    # Telegram Bot Configuration
    TELEGRAM_BOT_TOKEN: Optional[str] = os.getenv("TELEGRAM_BOT_TOKEN")
    TELEGRAM_CHANNEL_ID: Optional[str] = os.getenv("TELEGRAM_CHANNEL_ID")
    
    # Default location settings (can be overridden per user)
    PINCODE: Optional[str] = os.getenv("PINCODE", "110001")
    DEFAULT_STORE: str = os.getenv("DEFAULT_STORE", "delhi")
    
    # API and request settings
    REQUEST_TIMEOUT: int | float = float(os.getenv("REQUEST_TIMEOUT", "10"))
    
    # Notification settings
    FORCE_NOTIFY: bool = os.getenv("FORCE_NOTIFY", "False").lower() == "true"
    
    # Redis configuration for user state management
    REDIS_HOST: str = os.getenv("REDIS_HOST", "localhost")
    REDIS_PORT: int = int(os.getenv("REDIS_PORT", "6379"))
    REDIS_DB: int = int(os.getenv("REDIS_DB", "0"))
    REDIS_PASSWORD: Optional[str] = os.getenv("REDIS_PASSWORD")
    REDIS_SSL: bool = os.getenv("REDIS_SSL", "False").lower() == "true"
    REDIS_KEY_PREFIX: str = os.getenv("REDIS_KEY_PREFIX", "amul:")
    
    # Performance settings
    MAX_WORKERS: int = int(os.getenv("MAX_WORKERS", "8"))
    
    # Background checker settings
    CHECK_INTERVAL: int = int(os.getenv("CHECK_INTERVAL", "300"))  # 5 minutes default
    NOTIFICATION_COOLDOWN_HOURS: int = int(os.getenv("NOTIFICATION_COOLDOWN_HOURS", "24"))
    
    # Chrome/Selenium settings
    CHROME_BINARY: str = os.getenv("CHROME_BINARY", "/usr/bin/chromium")
    CHROMEDRIVER_PATH: str = os.getenv("CHROMEDRIVER_PATH", "/usr/bin/chromedriver")
    CHROME_NO_SANDBOX: bool = os.getenv("CHROME_NO_SANDBOX", "true").lower() in ("true", "1", "yes")
    CHROME_DISABLE_GPU: bool = os.getenv("CHROME_DISABLE_GPU", "true").lower() in ("true", "1", "yes")
    
    # Logging
    LOG_LEVEL: str = os.getenv("LOG_LEVEL", "INFO").upper()
    
    @classmethod
    def validate(cls) -> None:
        """Validate required configuration."""
        errors = []
        
        if not cls.TELEGRAM_BOT_TOKEN:
            errors.append("TELEGRAM_BOT_TOKEN environment variable must be set")
        
        if errors:
            raise ValueError("\n".join(errors))
    
    @classmethod
    def display(cls) -> None:
        """Display current configuration (for debugging)."""
        print("\n" + "="*60)
        print("CONFIGURATION")
        print("="*60)
        print(f"Telegram Bot: {'✓' if cls.TELEGRAM_BOT_TOKEN else '✗'}")
        print(f"Default Pincode: {cls.PINCODE}")
        print(f"Default Store: {cls.DEFAULT_STORE}")
        print(f"Max Workers: {cls.MAX_WORKERS}")
        print(f"Check Interval: {cls.CHECK_INTERVAL}s")
        print(f"Redis Host: {cls.REDIS_HOST}:{cls.REDIS_PORT}")
        print(f"Redis SSL: {cls.REDIS_SSL}")
        print(f"Log Level: {cls.LOG_LEVEL}")
        print(f"Chrome Binary: {cls.CHROME_BINARY}")
        print(f"ChromeDriver: {cls.CHROMEDRIVER_PATH}")
        print("="*60 + "\n")


# HTTP Headers for API requests
HEADERS: Dict[str, str] = {
    "Accept": "application/json, text/plain, */*",
    "Content-Type": "application/json",
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
        "(KHTML, like Gecko) Chrome/127.0.0.0 Safari/537.36"
    ),
    "Origin": "https://shop.amul.com",
    "Referer": "https://shop.amul.com/",
}
