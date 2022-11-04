from __future__ import annotations

import logging
import discord

from discord.ext import commands
from typing import TYPE_CHECKING, Literal, TypedDict

from utils.webhook import WebhookServer

if TYPE_CHECKING:
    from bot import SteveBot

_log = logging.getLogger(__name__)


class _UserAlertInvitePayload(TypedDict):
    username: str
    id: str
    avatar: str
    discriminator: str
    bot: bool


class AlertInvitePayload(TypedDict):
    user: _UserAlertInvitePayload
    invites: int
    guild_id: str
    type: Literal["reached"]


class Webhook(commands.Cog):
    """Alert invites webhook management"""

    def __init__(self, bot: SteveBot) -> None:
        self.bot = bot

    async def cog_load(self) -> None:
        self.server = WebhookServer(
            host=self.bot.configs.webhook_host,
            port=self.bot.configs.webhook_port,
            secret=self.bot.configs.webhook_secret,
        )
        self.server.add_endpoint(self.on_alert_invite)

        await self.server.start()
        _log.info(f"Started listening at {self.server.name}")

    async def cog_unload(self) -> None:
        await self.server.close()

    async def on_alert_invite(self, data: AlertInvitePayload):
        invites = data["invites"]
        guild_id = int(data["guild_id"])
        guild = self.bot.get_guild(guild_id)

        if guild is None:
            _log.warning("Unexpected guild, probably I am not member of %s", guild_id)
            return

        user_id = int(data["user"]["id"])
        member = guild.get_member(user_id)

        if member is None:
            _log.warning(
                f"User '%d' not found in guild %r, probably guild not chunked yet",
                user_id,
                guild,
            )
            return

        query = "SELECT * FROM rewards_roles WHERE guild_id = $1 AND requirement = $2"
        ret = await self.bot.pool.fetch(query, guild_id, invites)
        roles = [discord.Object(x.get("role_id")) for x in ret]

        if ret is not None:
            try:
                await member.add_roles(*roles)
            except discord.HTTPException as err:
                _log.warning(
                    "An error occured when trying to add reward role to %r: %s",
                    member,
                    err.text,
                )
            else:
                _log.info(
                    "Member %r reached reward role(s) %s that requires %i invites",
                    member,
                    ", ".join(str(x.id) for x in roles),
                    invites,
                )


async def setup(bot: SteveBot) -> None:
    await bot.add_cog(Webhook(bot))
