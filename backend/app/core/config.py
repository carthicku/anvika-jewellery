"""Application settings, read from environment variables (and backend/.env in development).

Every variable is documented in docs/development/ENVIRONMENT_VARIABLES.md.
`Settings.validate_for_environment` refuses unsafe production configurations at start-up.
"""

from __future__ import annotations

import os
import secrets
from functools import lru_cache
from pathlib import Path
from typing import Annotated, Literal

from pydantic import Field, SecretStr, field_validator, model_validator
from pydantic_settings import BaseSettings, NoDecode, SettingsConfigDict

BACKEND_DIR = Path(__file__).resolve().parent.parent.parent

# Values copied from .env.example that must never reach production.
_EXAMPLE_MARKERS = ("change-me", "example", "xxxxxxxx", "replace")


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=BACKEND_DIR / ".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    app_env: Literal["development", "test", "production"] = "development"
    secret_key: SecretStr = SecretStr("")

    database_url: str = "postgresql+psycopg://postgres:postgres@127.0.0.1:54329/anvika_dev"
    test_database_url: str = "postgresql+psycopg://postgres:postgres@127.0.0.1:54329/anvika_test"
    db_pool_size: int = 5
    db_max_overflow: int = 5
    # Set false behind a transaction-mode pooler (Supabase port 6543 / pgbouncer), which cannot
    # keep server-side prepared statements between requests. Serverless hosts should also use a
    # small pool (DB_POOL_SIZE=1, DB_MAX_OVERFLOW=0).
    db_prepare_statements: bool = True

    public_site_url: str = "http://localhost:5180"
    # Off until the owner decides the live site may appear in search results (robots.txt).
    allow_search_indexing: bool = False
    allowed_origins: Annotated[list[str], NoDecode] = ["http://localhost:5180"]
    cookie_secure: bool = False
    cookie_domain: str | None = None
    trusted_proxy_count: int = Field(default=0, ge=0, le=5)

    access_token_ttl_minutes: int = Field(default=15, ge=1, le=60)
    refresh_token_ttl_days: int = Field(default=30, ge=1, le=90)
    email_verification_required: bool = False

    store_name: str = "Anvika"
    order_reference_prefix: str = Field(default="ANV", pattern=r"^[A-Z]{2,5}$")

    payment_provider: Literal["razorpay", "simulator"] = "simulator"
    razorpay_key_id: str = ""
    razorpay_key_secret: SecretStr = SecretStr("")
    razorpay_webhook_secret: SecretStr = SecretStr("")
    razorpay_api_base: str = "https://api.razorpay.com/v1"
    simulator_secret: SecretStr = Field(
        default_factory=lambda: SecretStr(secrets.token_urlsafe(32))
    )
    payment_window_minutes: int = Field(default=30, ge=5, le=240)

    email_backend: Literal["file", "console", "smtp", "memory"] = "file"
    email_from: str = "Anvika <no-reply@example.com>"
    email_file_dir: str = "var/mail"
    smtp_host: str = ""
    smtp_port: int = 587
    smtp_username: str = ""
    smtp_password: SecretStr = SecretStr("")
    smtp_starttls: bool = True

    storage_backend: Literal["local", "s3"] = "local"
    media_root: str = "var/media"
    s3_endpoint_url: str = ""
    s3_region: str = ""
    s3_bucket: str = ""
    s3_access_key_id: str = ""
    s3_secret_access_key: SecretStr = SecretStr("")
    s3_public_base_url: str = ""

    background_jobs_enabled: bool = True
    # Secret for the scheduled-job endpoints (/api/v1/internal/cron/*, used with Vercel Cron).
    # Empty = those endpoints are switched off.
    cron_secret: SecretStr = SecretStr("")
    rate_limit_enabled: bool = True
    log_level: str = "INFO"
    log_format: Literal["text", "json"] = "text"

    @field_validator("allowed_origins", mode="before")
    @classmethod
    def _split_origins(cls, value: object) -> object:
        if isinstance(value, str):
            return [origin.strip().rstrip("/") for origin in value.split(",") if origin.strip()]
        return value

    @model_validator(mode="after")
    def allow_vercel_preview_origins(self) -> Settings:
        """Every Vercel preview deployment has its own URL, so a fixed ALLOWED_ORIGINS can't list
        it. Vercel provides the deployment's own host names (VERCEL_URL, VERCEL_BRANCH_URL); on
        previews only, those are added so the origin check accepts requests from the preview site
        itself (and nothing else)."""
        if os.environ.get("VERCEL_ENV") == "preview":
            for name in ("VERCEL_URL", "VERCEL_BRANCH_URL"):
                host = os.environ.get(name, "").strip()
                origin = f"https://{host}" if host else ""
                if origin and origin not in self.allowed_origins:
                    self.allowed_origins = [*self.allowed_origins, origin]
        return self

    @model_validator(mode="after")
    def validate_for_environment(self) -> Settings:
        if self.app_env != "production":
            if not self.secret_key.get_secret_value():
                # Dev/test convenience: a random key per process (sessions reset on restart).
                self.secret_key = SecretStr(secrets.token_urlsafe(48))
            return self

        problems: list[str] = []
        key = self.secret_key.get_secret_value()
        if len(key) < 32 or any(marker in key.lower() for marker in _EXAMPLE_MARKERS):
            problems.append("SECRET_KEY must be a random value of at least 32 characters")
        if self.payment_provider == "simulator":
            problems.append("PAYMENT_PROVIDER=simulator is not allowed in production")
        if self.payment_provider == "razorpay":
            if not self.razorpay_key_id.startswith(("rzp_live_", "rzp_test_")):
                problems.append("RAZORPAY_KEY_ID is missing or malformed")
            if len(self.razorpay_key_secret.get_secret_value()) < 8:
                problems.append("RAZORPAY_KEY_SECRET is missing")
            if len(self.razorpay_webhook_secret.get_secret_value()) < 16:
                problems.append("RAZORPAY_WEBHOOK_SECRET must be at least 16 characters")
        if not self.cookie_secure:
            problems.append("COOKIE_SECURE must be true in production")
        if not self.public_site_url.startswith("https://"):
            problems.append("PUBLIC_SITE_URL must use https:// in production")
        if not self.allowed_origins or any(
            not o.startswith("https://") for o in self.allowed_origins
        ):
            problems.append("ALLOWED_ORIGINS must list only https:// origins in production")
        if self.email_backend in ("file", "memory"):
            problems.append("EMAIL_BACKEND must be smtp (or console while testing) in production")
        cron = self.cron_secret.get_secret_value()
        if cron and len(cron) < 16:
            problems.append("CRON_SECRET must be at least 16 characters")
        if os.environ.get("VERCEL"):
            # Vercel functions have a read-only disk, and every request arrives through exactly one
            # Vercel proxy hop (needed for per-IP rate limits and audit logs to see real visitors).
            if self.storage_backend == "local":
                problems.append("STORAGE_BACKEND=s3 is required on Vercel (its disk is read-only)")
            if self.trusted_proxy_count != 1:
                problems.append("TRUSTED_PROXY_COUNT must be 1 on Vercel")
        if problems:
            raise ValueError("Unsafe production configuration: " + "; ".join(problems))
        return self

    @property
    def is_production(self) -> bool:
        return self.app_env == "production"

    def resolve_path(self, value: str) -> Path:
        """Resolve a path setting relative to the backend directory."""
        path = Path(value)
        return path if path.is_absolute() else BACKEND_DIR / path


@lru_cache
def get_settings() -> Settings:
    return Settings()
