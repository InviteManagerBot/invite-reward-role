from __future__ import annotations

import discord

from discord.ext import commands
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from bot import SteveBot
    from _types import GuildContext


class Admin(commands.Cog):
    """Admin-only commands."""

    def __init__(self, bot: SteveBot) -> None:
        self.bot = bot

    @commands.command()
    @commands.is_owner()
    @commands.guild_only()
    async def sync(
        self,
        ctx: GuildContext,
        guild_id: int | None = None,
    ):
        """Syncs all slash commands with the given guild or globally."""

        if guild_id:
            guild = discord.Object(id=guild_id)
        else:
            guild = None

        commands = await self.bot.tree.sync(guild=guild)
        await ctx.send(f"Successfully synced **{len(commands)}** slash commands")


async def setup(bot: SteveBot) -> None:
    await bot.add_cog(Admin(bot))
