"""
Centralized configuration for the entire IRMDS system.

Uses Pydantic Settings to load values from three sources, in priority order:
    1. Environment variables    (highest — ideal for Docker / CI)
    2. .env file                (development convenience)
    3. Field defaults           (lowest — sensible fallbacks)

Every configurable threshold, path, and connection parameter lives here.
Modules access config via `get_config()`, which returns a cached singleton.

Design decision: One flat config object rather than per-module configs.
This keeps the system simple and avoids circular imports. Modules only
read the fields they need — the config object is lightweight (no I/O
after initial load).
"""

from __future__ import annotations

from functools import lru_cache

from pydantic_settings import BaseSettings


class IRMDSConfig(BaseSettings):
    """System-wide configuration with validated, typed fields.

    All fields use the IRMDS_ prefix in environment variables.
    Example: `IRMDS_API_PORT=8080` maps to `api_port`.
    """

    # ── Database ──────────────────────────────────────────
    # SQLite for development, PostgreSQL for production.
    # Swap with a single env var change — SQLAlchemy handles both.
    database_url: str = "sqlite:///data/irmds.db"

    # ── Visual Module ─────────────────────────────────────
    visual_model_path: str = "models/yolov8n.pt"
    visual_confidence: float = 0.4      # YOLO detection confidence threshold
    visual_iou_threshold: float = 0.3   # IoU threshold for tracker association
    visual_max_disappeared: int = 20    # Frames before a lost track is pruned
    visual_loiter_seconds: int = 4      # Seconds in zone before loitering alert
    visual_crowd_threshold: int = 3     # People in zone to trigger crowd alert
    visual_speed_alert_ms: float = 2.2  # Speed (m/s) above which = "running"
    visual_human_height_m: float = 1.7  # Anthropometric constant for calibration
    visual_source: str = "0"            # Webcam index, file path, or RTSP URL
    visual_frame_width: int = 640       # Processing resolution width
    visual_frame_height: int = 480      # Processing resolution height
    visual_frame_skip: int = 1          # Process every Nth frame (1 = all)

    # ── Network Module ────────────────────────────────────
    network_window_seconds: float = 1.0     # Aggregation window for features
    network_baseline_windows: int = 60      # Windows to collect before training
    network_anomaly_contamination: float = 0.05  # Isolation Forest contamination
    network_zscore_threshold: float = 3.0   # Z-score threshold for flagging
    network_ddos_pps: int = 10000           # Packets/sec to suspect DDoS
    network_scan_ports: int = 100           # Unique ports to suspect port scan

    # ── Finance Module ────────────────────────────────────
    finance_data_path: str = "data/sample_stock.csv"
    finance_volatility_window: int = 20     # Rolling volatility lookback
    finance_rsi_period: int = 14            # RSI calculation period
    finance_bollinger_window: int = 20      # Bollinger Band SMA window
    finance_momentum_window: int = 10       # Rate-of-change lookback
    finance_baseline_ticks: int = 200       # Ticks before Isolation Forest trains
    finance_flash_crash_sigma: float = 3.0  # Return threshold for flash crash
    finance_volume_zscore_threshold: float = 2.0  # Volume spike threshold
    finance_cusum_threshold_sigma: float = 5.0    # CUSUM trigger threshold
    finance_replay_speed: float = 5.0       # Replay multiplier (5x = 5× real-time)

    # ── Infrastructure Module ─────────────────────────────
    infra_poll_interval: float = 2.0   # Seconds between metric polls
    infra_cpu_critical: float = 95.0   # CPU % to trigger CRITICAL
    infra_cpu_spike_delta: float = 40.0  # CPU % jump between polls = anomaly
    infra_ram_warning: float = 85.0    # RAM % for WARNING
    infra_ram_critical: float = 95.0   # RAM % for CRITICAL
    infra_disk_critical: float = 95.0  # Disk % for CRITICAL
    infra_baseline_polls: int = 30     # Polls before Isolation Forest trains
    infra_log_path: str = "data/sample_syslog.log"

    # ── Alert Manager ─────────────────────────────────────
    alert_cooldown_seconds: int = 10    # Min seconds between same alert type
    alert_max_history: int = 1000       # Max alerts kept in memory
    alert_escalation_window: int = 60   # Seconds to watch for escalation
    alert_escalation_count: int = 3     # WARNINGs in window → auto-CRITICAL

    # ── Notifications ─────────────────────────────────────
    slack_webhook_url: str = ""         # Slack incoming webhook URL
    discord_webhook_url: str = ""       # Discord webhook URL
    email_smtp_host: str = ""           # SMTP server hostname
    email_smtp_port: int = 587          # SMTP port (587 = TLS)
    email_from: str = ""                # Sender email address
    email_password: str = ""            # SMTP password / app password
    email_to: str = ""                  # Recipient email address
    notify_on_severity: str = "CRITICAL"  # Minimum severity for webhook fire

    # ── API Server ────────────────────────────────────────
    api_host: str = "0.0.0.0"
    api_port: int = 8000
    cors_origins: str = "*"             # Comma-separated allowed origins

    model_config = {
        "env_prefix": "IRMDS_",         # All env vars prefixed: IRMDS_API_PORT
        "env_file": ".env",             # Load from .env in project root
        "env_file_encoding": "utf-8",
        "case_sensitive": False,        # IRMDS_API_PORT = irmds_api_port
        "extra": "ignore",             # Don't fail on unknown env vars
    }

    def get_cors_origins_list(self) -> list[str]:
        """Parse comma-separated CORS origins into a list.

        Returns ["*"] for wildcard, or a list of specific origins.
        """
        if self.cors_origins.strip() == "*":
            return ["*"]
        return [origin.strip() for origin in self.cors_origins.split(",")]

    def get_sanitized(self) -> dict:
        """Return config as a dict with sensitive values masked.

        Safe to expose via the /config API endpoint — passwords,
        webhook URLs, and API keys are replaced with '***'.
        """
        sensitive_fields = {
            "email_password",
            "slack_webhook_url",
            "discord_webhook_url",
        }
        data = self.model_dump()
        for field in sensitive_fields:
            if data.get(field):
                data[field] = "***"
        return data


@lru_cache(maxsize=1)
def get_config() -> IRMDSConfig:
    """Return the global configuration singleton.

    Uses lru_cache to ensure the config is loaded exactly once from
    environment variables / .env file, then reused across the entire
    application lifecycle.

    To override in tests:
        get_config.cache_clear()
        monkeypatch.setenv("IRMDS_API_PORT", "9999")
    """
    return IRMDSConfig()
