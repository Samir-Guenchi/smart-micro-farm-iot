"""API settings, all from environment variables (see .env.example)."""

import os
import secrets
from dataclasses import dataclass, field


def _list(name, default):
    return [x.strip() for x in os.environ.get(name, default).split(",") if x.strip()]


@dataclass
class Settings:
    database_url: str = field(default_factory=lambda: os.environ.get("DATABASE_URL", "postgresql://greenloop:greenloop@localhost/greenloop"))
    mqtt_host: str = field(default_factory=lambda: os.environ.get("MQTT_HOST", "localhost"))
    mqtt_port: int = field(default_factory=lambda: int(os.environ.get("MQTT_PORT", "1883")))
    mqtt_user: str | None = field(default_factory=lambda: os.environ.get("MQTT_USER"))
    mqtt_password: str | None = field(default_factory=lambda: os.environ.get("MQTT_PASSWORD"))
    # TLS is needed for hosted brokers (HiveMQ Cloud, EMQX); on by default for port 8883.
    mqtt_tls: bool = field(default_factory=lambda: os.environ.get("MQTT_TLS", "").lower() in ("1", "true", "yes") or os.environ.get("MQTT_PORT") == "8883")
    admin_user: str = field(default_factory=lambda: os.environ.get("API_ADMIN_USER", "admin"))
    admin_password: str = field(default_factory=lambda: os.environ.get("API_ADMIN_PASSWORD", ""))
    # Signs login tokens. If unset, a random key is used and tokens stop working on restart.
    secret_key: str = field(default_factory=lambda: os.environ.get("API_SECRET_KEY") or secrets.token_hex(32))
    token_hours: float = field(default_factory=lambda: float(os.environ.get("API_TOKEN_HOURS", "720")))
    # Long-lived token for services (alerts bot, assistant) that can't log in.
    service_token: str | None = field(default_factory=lambda: os.environ.get("API_SERVICE_TOKEN"))
    max_pump_s: int = field(default_factory=lambda: int(os.environ.get("MAX_PUMP_S", "900")))
    pump_nodes: list = field(default_factory=lambda: _list("PUMP_NODES", "irrigation-1"))
    offline_after_s: int = field(default_factory=lambda: int(os.environ.get("OFFLINE_AFTER_S", "600")))
    cors_origins: list = field(default_factory=lambda: _list("CORS_ORIGINS", "http://localhost:5173"))
