from __future__ import annotations

import discord
import asyncpg

from discord.ext import commands
from discord import app_commands
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from bot import SteveBot
    from _types import GuildContext, GuildInteraction


class RoleAssignable(app_commands.Transformer):
    async def transform(
        self, interaction: GuildInteraction, role: discord.Role
    ) -> discord.Role:
        if not role.is_assignable():
            raise commands.BadArgument(
                f"I don't seem to have permissions to assign or remove {role.mention} role."
            )
        return role

    @property
    def type(self) -> discord.AppCommandOptionType:
        return discord.AppCommandOptionType.role


class Management(commands.Cog):
    def __init__(self, bot: SteveBot) -> None:
        self.bot = bot

    @commands.hybrid_group()
    @app_commands.guild_only()
    async def reward(self, ctx):
        pass

    @reward.command(name="add")
    @commands.has_permissions(manage_roles=True)
    async def reward_add(
        self,
        ctx: GuildContext,
        role: app_commands.Transform[discord.Role, RoleAssignable],
        requirement: commands.Range[int, 1, None],
    ):
        """Set up a new reward role by invites."""

        query = "INSERT INTO rewards_roles (guild_id, role_id, requirement) VALUES ($1, $2, $3)"
        try:
            await self.bot.pool.execute(query, ctx.guild.id, role.id, requirement)
        except asyncpg.exceptions.UniqueViolationError:
            await ctx.send(
                f"{role.mention} is already set as reward role, you cannot set it again."
            )
            return

        e = discord.Embed(
            title="Done!",
            description=f"You have successfully added reward role **{role.mention}** in **{requirement}** invites!",
            color=discord.Color.green(),
        )
        await ctx.send(embed=e)

    @reward.command(name="remove")
    @commands.has_permissions(manage_roles=True)
    async def reward_remove(
        self,
        ctx: GuildContext,
        role: app_commands.Transform[discord.Role, RoleAssignable],
    ):
        """Remove an existing invite reward role."""

        query = (
            "DELETE FROM rewards_roles WHERE guild_id = $1 AND role_id = $2 RETURNING *"
        )
        ret = await self.bot.pool.fetchrow(query, ctx.guild.id, role.id)

        if ret is None:
            await ctx.send(
                f"No reward role has been found that rewards role {role.mention}."
            )
            return

        e = discord.Embed(
            title="Done!",
            description=f"You have successfully removed reward role **{role.mention}** in **{ret.get('requirement')}** invites!",
            color=discord.Color.green(),
        )
        await ctx.send(embed=e)

    @reward.command(name="list")
    @commands.has_permissions(manage_roles=True)
    async def reward_list(
        self,
        ctx: GuildContext,
    ):
        """List all the reward roles configured on your server."""

        query = "SELECT * FROM rewards_roles WHERE guild_id = $1"
        ret = await self.bot.pool.fetch(query, ctx.guild.id)

        if ret:
            fmt = "\n".join(
                f"> <@&{x.get('role_id')}>: Reward role on **{x.get('requirement')}** invite(s)"
                for x in ret
            )
        else:
            fmt = "Nothing was found here..."

        e = discord.Embed(
            description=f"You have a total of {len(ret)} reward roles set up on your server.\n\n{fmt}",
            color=discord.Color.blurple(),
        )
        await ctx.send(embed=e)


async def setup(bot: SteveBot) -> None:
    await bot.add_cog(Management(bot))
