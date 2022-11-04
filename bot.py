from __future__ import annotations

import discord
import logging
import configs  # type: ignore

from discord.ext import commands
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from asyncpg import Pool

    from _types.context import GuildContext

_log = logging.getLogger(__name__)
cogs = ("cogs.management", "cogs.webhook", "cogs.admin")


class SteveBot(commands.Bot):
    user: discord.ClientUser
    pool: Pool

    def __init__(self) -> None:
        intents = discord.Intents(
            members=True,
            messages=True,
            guilds=True,
        )
        super().__init__(
            intents=intents,
            # Command prefix is only used for :command:`sync`
            command_prefix=commands.when_mentioned,
            owner_ids=configs.owner_ids,
            activity=discord.Game(name=configs.bot_status),
        )

    async def setup_hook(self) -> None:
        for cog in cogs:
            try:
                await self.load_extension(cog)
            except Exception:
                _log.exception("Failed to load extension %s", cog)

    async def on_ready(self):
        _log.info(
            f"Ready up: %s#%s",
            self.user.name,
            self.user.discriminator,
        )
        _log.info(
            "developer: MartimMartins @ martim13artins13@gmail.com",
        )
        _log.info(
            "copyright: InviteManager @ invite-manager.net",
        )
        _log.info(
            "licence: MIT",
        )

    async def start(self) -> None:
        await super().start(configs.token, reconnect=True)

    async def on_command_error(
        self, ctx: GuildContext, error: commands.CommandError
    ) -> None:
        if isinstance(error, commands.BadArgument):
            e = discord.Embed(color=discord.Color.red(), description=str(error))
            await ctx.send(embed=e)
        elif isinstance(error, commands.HybridCommandError):
            original = error.original
            raise original

    @property
    def configs(self):
        return __import__("configs")
