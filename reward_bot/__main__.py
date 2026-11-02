"""Entry point: ``python -m reward_bot``."""

from __future__ import annotations

import logging
import sys

import discord
from dotenv import load_dotenv

from .bot import RewardBot
from .config import Config, ConfigError


def main() -> None:
    load_dotenv()  # reads .env when present; real environment variables win
    try:
        config = Config.from_env()
    except (ConfigError, ValueError) as exc:
        sys.exit(f"Configuration error: {exc}")

    discord.utils.setup_logging(level=getattr(logging, config.log_level, logging.INFO))
    bot = RewardBot(config)
    try:
        bot.run(config.discord_token, log_handler=None)  # logging is already set up
    except discord.LoginFailure:
        sys.exit("Discord rejected DISCORD_TOKEN: copy the token from the Developer Portal (Bot tab).")


if __name__ == "__main__":
    main()
