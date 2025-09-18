"""
Core application configuration using Pydantic Settings.
"""

from typing import Optional
from pydantic_settings import BaseSettings
from pydantic import Field
import secrets


class Settings(BaseSettings):
    """Application settings with environment variable support."""

    # Application
    app_name: str = Field("Jannah SMS Admin", env="APP_NAME")
    company_name: str = Field("Jannah Property Management", env="COMPANY_NAME")
    debug: bool = Field(False, env="DEBUG")
    secret_key: str = Field(secrets.token_urlsafe(32), env="SECRET_KEY")

    # Database
    database_url: str = Field("sqlite:///./data/jannah_sms.db", env="DATABASE_URL")

    # SMS API Settings
    sms_api_key: str = Field("", env="SMS_API_KEY")
    sms_api_base: str = Field("https://textbelt.com/text", env="SMS_API_BASE")

    # Security
    jwt_algorithm: str = Field("HS256", env="JWT_ALGORITHM")
    access_token_expire_minutes: int = Field(60, env="ACCESS_TOKEN_EXPIRE_MINUTES")

    # Admin User Credentials
    admin_username: str = Field("admin", env="ADMIN_USERNAME")
    admin_password: str = Field("admin", env="ADMIN_PASSWORD")

    # UI Configuration for elderly users
    ui_large_fonts: bool = Field(True, env="UI_LARGE_FONTS")
    ui_high_contrast: bool = Field(True, env="UI_HIGH_CONTRAST")
    ui_simple_navigation: bool = Field(True, env="UI_SIMPLE_NAVIGATION")

    # Logging
    log_level: str = Field("INFO", env="LOG_LEVEL")
    log_file: str = Field("logs/jannah-sms.log", env="LOG_FILE")

    # CORS
    cors_origins: str = Field(
        "http://localhost:3000,http://127.0.0.1:3000", env="CORS_ORIGINS"
    )

    # Rate Limiting
    rate_limit_per_minute: int = Field(60, env="RATE_LIMIT_PER_MINUTE")

    # Backup
    backup_enabled: bool = Field(True, env="BACKUP_ENABLED")
    backup_interval_minutes: int = Field(
        1440, env="BACKUP_INTERVAL_MINUTES"
    )  # Daily backups
    backup_retention_days: int = Field(
        30, env="BACKUP_RETENTION_DAYS"
    )  # Keep backups for 30 days

    # Performance Settings
    uvicorn_workers: int = Field(1, env="UVICORN_WORKERS")
    uvicorn_host: str = Field("0.0.0.0", env="UVICORN_HOST")
    uvicorn_port: int = Field(8000, env="UVICORN_PORT")

    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"
        case_sensitive = False

    @property
    def formatted_footer(self) -> str:
        """Get formatted footer message with company name."""
        return self.footer_message.format(company_name=self.company_name)

    @property
    def onedrive_configured(self) -> bool:
        """Check if OneDrive credentials are properly configured."""
        return all(
            [
                self.microsoft_client_id,
                self.microsoft_client_secret,
                self.microsoft_tenant_id,
            ]
        )


# Global settings instance
settings = Settings()
