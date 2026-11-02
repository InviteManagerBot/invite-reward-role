"""Discord client: the /rewards commands and the role granting."""

from __future__ import annotations

import logging

import discord
from aiohttp import web
from discord import app_commands

from .config import Config
from .db import RewardStore
from .webhook import InviteAlert, create_app

log = logging.getLogger(__name__)

# This bot never joins voice channels: silence the "voice not supported" warnings.
discord.VoiceClient.warn_nacl = False
discord.VoiceClient.warn_dave = False


class RewardBot(discord.Client):
    def __init__(self, config: Config) -> None:
        # Only the guilds intent is needed: members are fetched on demand, so
        # no privileged intent has to be enabled in the Developer Portal.
        super().__init__(intents=discord.Intents(guilds=True))
        self.config = config
        self.store = RewardStore(config.database_path)
        self.tree = app_commands.CommandTree(self)
        self.tree.add_command(RewardCommands(self.store))
        self._runner: web.AppRunner | None = None

    async def setup_hook(self) -> None:
        app = create_app(self.config.webhook_secret, self.handle_alert, path=self.config.webhook_path)
        self._runner = web.AppRunner(app, access_log=None)
        await self._runner.setup()
        await web.TCPSite(self._runner, self.config.webhook_host, self.config.webhook_port).start()
        log.info(
            "Listening for InviteCount alerts on http://%s:%s%s",
            self.config.webhook_host,
            self.config.webhook_port,
            self.config.webhook_path,
        )

        # Syncing on every start is fine for a small bot. A dev guild gets the
        # commands instantly; global commands can take a few minutes to show up.
        if self.config.dev_guild_id:
            guild = discord.Object(self.config.dev_guild_id)
            self.tree.copy_global_to(guild=guild)
            await self.tree.sync(guild=guild)
        else:
            await self.tree.sync()

    async def on_ready(self) -> None:
        log.info("Logged in as %s (%s) in %d server(s)", self.user, self.user and self.user.id, len(self.guilds))

    async def close(self) -> None:
        if self._runner is not None:
            await self._runner.cleanup()
        self.store.close()
        await super().close()

    async def handle_alert(self, alert: InviteAlert) -> None:
        """Give every reward role the member has earned and does not have yet."""
        if alert.is_test:
            log.info("Test alert received from InviteCount for guild %s: the webhook works", alert.guild_id)
            return
        if alert.is_bot:
            return

        guild = self.get_guild(alert.guild_id)
        if guild is None:
            log.warning("Alert for guild %s, but the bot is not in that server", alert.guild_id)
            return

        role_ids = self.store.roles_earned(guild.id, alert.invites)
        if not role_ids:
            log.info("%s reached %d invites: no reward configured up to that count", alert.username, alert.invites)
            return

        member = guild.get_member(alert.user_id)
        if member is None:
            try:
                member = await guild.fetch_member(alert.user_id)
            except discord.NotFound:
                log.info("%s reached %d invites but is no longer in %s", alert.username, alert.invites, guild)
                return

        # Idempotent: InviteCount alerts again if a member drops below a milestone
        # and reaches it a second time; roles the member already has are skipped.
        to_add: list[discord.Role] = []
        for role_id in role_ids:
            role = guild.get_role(role_id)
            if role is None:
                log.warning("Reward role %s no longer exists in %s; remove it with /rewards remove", role_id, guild)
            elif role in member.roles:
                continue
            elif not role.is_assignable():
                log.error("Cannot give %s in %s: move the bot's role above it (Server Settings > Roles)", role, guild)
            else:
                to_add.append(role)

        if not to_add:
            return
        try:
            await member.add_roles(*to_add, reason=f"InviteCount: reached {alert.invites} invites")
        except discord.Forbidden:
            log.error("Missing permission to give roles in %s: the bot needs Manage Roles", guild)
        except discord.HTTPException as exc:
            log.error("Discord refused to give roles to %s: %s", member, exc)
        else:
            names = ", ".join(role.name for role in to_add)
            log.info("Gave %s to %s (%d invites) in %s", names, member, alert.invites, guild)


@app_commands.guild_only()
@app_commands.default_permissions(administrator=True)
class RewardCommands(app_commands.Group, name="rewards", description="Roles given when members reach N invites"):
    def __init__(self, store: RewardStore) -> None:
        super().__init__()
        self.store = store

    @app_commands.command(name="add", description="Give a role when a member reaches a number of invites")
    @app_commands.describe(role="Role to give", invites="Invites needed (must also be an InviteCount alert)")
    async def add(
        self, interaction: discord.Interaction, role: discord.Role, invites: app_commands.Range[int, 1, 1_000_000]
    ) -> None:
        assert interaction.guild is not None
        if role.is_default() or role.managed:
            await interaction.response.send_message("This role cannot be given by a bot.", ephemeral=True)
            return
        if not role.is_assignable():
            await interaction.response.send_message(
                f"I cannot give {role.mention}: I need **Manage Roles** and my role must be above it.",
                ephemeral=True,
            )
            return

        self.store.set_reward(interaction.guild.id, role.id, invites)
        await interaction.response.send_message(
            f"{role.mention} will be given at **{invites}** invites.\n"
            f"Make sure InviteCount has the same alert: `/alert-invites add amount:{invites}`.",
            ephemeral=True,
            allowed_mentions=discord.AllowedMentions.none(),
        )

    @app_commands.command(name="remove", description="Stop giving a reward role")
    @app_commands.describe(role="Reward role to remove")
    async def remove(self, interaction: discord.Interaction, role: discord.Role) -> None:
        assert interaction.guild is not None
        removed = self.store.remove_reward(interaction.guild.id, role.id)
        message = f"{role.mention} is no longer a reward." if removed else f"{role.mention} is not a reward."
        await interaction.response.send_message(
            message, ephemeral=True, allowed_mentions=discord.AllowedMentions.none()
        )

    @app_commands.command(name="list", description="List the reward roles")
    async def list_rewards(self, interaction: discord.Interaction) -> None:
        assert interaction.guild is not None
        rewards = self.store.list_rewards(interaction.guild.id)
        if not rewards:
            text = "No reward yet. Add one with `/rewards add`."
        else:
            text = "\n".join(f"**{invites}** invites → <@&{role_id}>" for role_id, invites in rewards)
        await interaction.response.send_message(text, ephemeral=True, allowed_mentions=discord.AllowedMentions.none())
