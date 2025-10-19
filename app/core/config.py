"""
Core application configuration using Pydantic Settings.
"""

import secrets

from pydantic import Field
from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    """Application settings with environment variable support."""

    # Application Theming
    app_name: str = Field("Jannah SMS Admin", env="APP_NAME")
    company_name: str = Field("Jannah Property Management", env="COMPANY_NAME")
    app_version: str = Field("v2.0", env="APP_VERSION")
    app_tagline: str = Field(
        "Modern SMS scheduling system for property management", env="APP_TAGLINE"
    )
    app_icon: str = Field("📱", env="APP_ICON")
    primary_color: str = Field("#3b82f6", env="PRIMARY_COLOR")
    secondary_color: str = Field("#6b7280", env="SECONDARY_COLOR")

    # Application
    debug: bool = Field(False, env="DEBUG")
    secret_key: str = Field(secrets.token_urlsafe(32), env="SECRET_KEY")

    # Database
    database_url: str = Field("sqlite:///./jannah_sms.db", env="DATABASE_URL")

    # SMS API Settings
    sms_api_key: str = Field("", env="SMS_API_KEY")
    sms_api_base: str = Field("https://textbelt.com/text", env="SMS_API_BASE")


    # Security
    jwt_algorithm: str = Field("HS256", env="JWT_ALGORITHM")
    access_token_expire_minutes: int = Field(60, env="ACCESS_TOKEN_EXPIRE_MINUTES")
    session_cookie_name: str = Field("jannah_session", env="SESSION_COOKIE_NAME")
    session_cookie_max_age: int = Field(86400, env="SESSION_COOKIE_MAX_AGE")  # 24 hours

    # Admin User Credentials (for initial setup)
    admin_username: str = Field("admin", env="ADMIN_USERNAME")
    admin_password: str = Field("changeme", env="ADMIN_PASSWORD")
    admin_email: str = Field("admin@jannah-sms.com", env="ADMIN_EMAIL")

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
    def is_production(self) -> bool:
        """Check if running in production mode."""
        return not self.debug and self.database_url.startswith("postgresql")

    @property
    def theme_context(self) -> dict:
        """Get theming context for templates."""
        return {
            "app_name": self.app_name,
            "company_name": self.company_name,
            "app_version": self.app_version,
            "app_tagline": self.app_tagline,
            "app_icon": self.app_icon,
            "primary_color": self.primary_color,
            "secondary_color": self.secondary_color,
            "powered_by": f"Powered by {self.app_name} {self.app_version}",
        }


# Global settings instance
settings = Settings()
