from __future__ import annotations

import discord

from typing import TYPE_CHECKING
from discord.ext import commands

if TYPE_CHECKING:
    from bot import SteveBot


class GuildInteraction(discord.Interaction):
    guild_id: int
    channel_id: int
    guild: discord.Guild
    client: SteveBot
    user: discord.Member
    message: discord.Message


class GuildContext(commands.Context):
    author: discord.Member
    guild: discord.Guild
    channel: discord.TextChannel | discord.VoiceChannel | discord.Thread
    me: discord.Member
    interaction: GuildInteraction
