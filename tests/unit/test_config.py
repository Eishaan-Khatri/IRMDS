"""
Unit tests for the configuration system.

Tests cover:
    - Default values load correctly
    - Environment variable overrides work
    - CORS parsing helper
    - Sanitized config (hides secrets)
"""

from __future__ import annotations

import os

from core.config import IRMDSConfig, get_config


class TestConfigDefaults:
    """Verify sensible default values."""

    def test_default_api_port(self):
        config = IRMDSConfig()
        assert config.api_port == 8000

    def test_default_visual_confidence(self):
        config = IRMDSConfig()
        assert config.visual_confidence == 0.4

    def test_default_database_is_sqlite(self):
        config = IRMDSConfig()
        assert "sqlite" in config.database_url

    def test_default_alert_cooldown(self):
        config = IRMDSConfig()
        assert config.alert_cooldown_seconds == 10

    def test_default_notifications_disabled(self):
        """Notification URLs should be empty by default (not-configured)."""
        config = IRMDSConfig()
        assert config.slack_webhook_url == ""
        assert config.discord_webhook_url == ""


class TestConfigOverrides:
    """Environment variable overrides."""

    def test_env_var_overrides_default(self, monkeypatch):
        """Setting IRMDS_API_PORT should override the default."""
        monkeypatch.setenv("IRMDS_API_PORT", "9999")
        config = IRMDSConfig()
        assert config.api_port == 9999

    def test_env_prefix_is_required(self, monkeypatch):
        """Variables without IRMDS_ prefix should not be loaded."""
        monkeypatch.setenv("API_PORT", "7777")
        config = IRMDSConfig()
        assert config.api_port == 8000  # Should still be default


class TestCORSParsing:
    """CORS origins parsing helper."""

    def test_wildcard_cors(self):
        config = IRMDSConfig(cors_origins="*")
        assert config.get_cors_origins_list() == ["*"]

    def test_comma_separated_cors(self):
        config = IRMDSConfig(cors_origins="http://localhost:3000, https://example.com")
        origins = config.get_cors_origins_list()
        assert len(origins) == 2
        assert "http://localhost:3000" in origins
        assert "https://example.com" in origins


class TestSanitizedConfig:
    """Config sanitization for safe API exposure."""

    def test_passwords_are_masked(self):
        config = IRMDSConfig(email_password="supersecret123")
        sanitized = config.get_sanitized()
        assert sanitized["email_password"] == "***"

    def test_webhook_urls_are_masked(self):
        config = IRMDSConfig(slack_webhook_url="https://hooks.slack.com/xxx")
        sanitized = config.get_sanitized()
        assert sanitized["slack_webhook_url"] == "***"

    def test_non_sensitive_fields_are_visible(self):
        config = IRMDSConfig()
        sanitized = config.get_sanitized()
        assert sanitized["api_port"] == 8000
        assert sanitized["visual_confidence"] == 0.4


class TestConfigSingleton:
    """Singleton behavior via get_config()."""

    def test_get_config_returns_same_instance(self):
        """Consecutive calls should return the cached singleton."""
        get_config.cache_clear()
        c1 = get_config()
        c2 = get_config()
        assert c1 is c2
