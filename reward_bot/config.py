"""Configuration read from environment variables (see ``.env.example``)."""

from __future__ import annotations

import os
from dataclasses import dataclass


class ConfigError(RuntimeError):
    pass


def _required(name: str) -> str:
    value = os.environ.get(name, "").strip()
    if not value:
        raise ConfigError(f"{name} is not set (copy .env.example to .env and fill it in)")
    return value


@dataclass(frozen=True, slots=True)
class Config:
    discord_token: str
    webhook_secret: str
    webhook_host: str
    webhook_port: int
    webhook_path: str
    database_path: str
    dev_guild_id: int | None
    log_level: str

    @classmethod
    def from_env(cls) -> Config:
        dev_guild = os.environ.get("DEV_GUILD_ID", "").strip()
        return cls(
            discord_token=_required("DISCORD_TOKEN"),
            webhook_secret=_required("WEBHOOK_SECRET"),
            webhook_host=os.environ.get("WEBHOOK_HOST", "0.0.0.0"),
            webhook_port=int(os.environ.get("WEBHOOK_PORT", "8080")),
            webhook_path=os.environ.get("WEBHOOK_PATH", "/webhook"),
            database_path=os.environ.get("DATABASE_PATH", "data/rewards.db"),
            dev_guild_id=int(dev_guild) if dev_guild else None,
            log_level=os.environ.get("LOG_LEVEL", "INFO").upper(),
        )
