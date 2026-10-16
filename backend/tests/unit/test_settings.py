"""Production configuration must refuse unsafe settings at start-up."""

from __future__ import annotations

import pytest
from pydantic import ValidationError

from app.core.config import Settings

GOOD_PRODUCTION = {
    "app_env": "production",
    "secret_key": "q8Jx3vT0pLr7mW2nZ5bY1cK9hG4dF6sA0eR3tU8iO2wQ",
    "payment_provider": "razorpay",
    "razorpay_key_id": "rzp_test_abc123",
    "razorpay_key_secret": "s3cr3t-value-123",
    "razorpay_webhook_secret": "a-long-webhook-secret-value",
    "cookie_secure": True,
    "public_site_url": "https://shop.example.in",
    "allowed_origins": "https://shop.example.in",
    "email_backend": "smtp",
}


def make(**overrides: object) -> Settings:
    return Settings(_env_file=None, **{**GOOD_PRODUCTION, **overrides})  # type: ignore[arg-type]


def test_valid_production_settings_are_accepted() -> None:
    settings = make()
    assert settings.is_production
    assert settings.allowed_origins == ["https://shop.example.in"]


@pytest.mark.parametrize(
    ("override", "expected_message"),
    [
        ({"payment_provider": "simulator"}, "simulator is not allowed"),
        ({"secret_key": "short"}, "SECRET_KEY"),
        ({"secret_key": "change-me-change-me-change-me-change-me"}, "SECRET_KEY"),
        ({"cookie_secure": False}, "COOKIE_SECURE"),
        ({"public_site_url": "http://shop.example.in"}, "PUBLIC_SITE_URL"),
        ({"allowed_origins": "http://shop.example.in"}, "ALLOWED_ORIGINS"),
        ({"razorpay_webhook_secret": "short"}, "RAZORPAY_WEBHOOK_SECRET"),
        ({"email_backend": "file"}, "EMAIL_BACKEND"),
    ],
)
def test_unsafe_production_settings_are_rejected(
    override: dict[str, object], expected_message: str
) -> None:
    with pytest.raises(ValidationError, match=expected_message):
        make(**override)


def test_development_generates_a_secret_key_when_missing() -> None:
    settings = Settings(_env_file=None, app_env="development", secret_key="")  # type: ignore[call-arg]
    assert len(settings.secret_key.get_secret_value()) >= 32


def test_allowed_origins_parsed_from_comma_list() -> None:
    settings = Settings(  # type: ignore[call-arg]
        _env_file=None, allowed_origins="http://a.test, http://b.test/"
    )
    assert settings.allowed_origins == ["http://a.test", "http://b.test"]


def test_vercel_needs_object_storage_and_one_proxy_hop(monkeypatch: pytest.MonkeyPatch) -> None:
    on_vercel = {"storage_backend": "s3", "trusted_proxy_count": 1}
    assert make(**on_vercel).storage_backend == "s3"  # fine off Vercel too
    monkeypatch.setenv("VERCEL", "1")
    assert make(**on_vercel).trusted_proxy_count == 1
    with pytest.raises(ValidationError, match="STORAGE_BACKEND=s3 is required on Vercel"):
        make(storage_backend="local", trusted_proxy_count=1)
    with pytest.raises(ValidationError, match="TRUSTED_PROXY_COUNT must be 1 on Vercel"):
        make(storage_backend="s3", trusted_proxy_count=0)


def test_cron_secret_must_be_long_enough_when_set() -> None:
    assert make(cron_secret="").cron_secret.get_secret_value() == ""
    assert make(cron_secret="a-long-enough-cron-secret").cron_secret.get_secret_value()
    with pytest.raises(ValidationError, match="CRON_SECRET"):
        make(cron_secret="short")
