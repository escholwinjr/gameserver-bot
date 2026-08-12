import logging

import discord
from discord import app_commands
from discord.ext import commands

from config import (
    DISCORD_GUILD_ID,
    DISCORD_TOKEN,
)

from player_store import initialize_database

logging.basicConfig(
    level=logging.INFO,
    format=(
        "%(asctime)s "
        "%(levelname)s "
        "%(name)s: "
        "%(message)s"
    ),
)

logger = logging.getLogger("gameserver-bot")


class GameServerBot(commands.Bot):
    def __init__(self) -> None:
        intents = discord.Intents.none()
        intents.guilds = True
        intents.reactions = True
        intents.members = True

        super().__init__(
            command_prefix="!",
            intents=intents,
        )

    async def setup_hook(self) -> None:
        await self.load_extension(
            "commands.general"
        )

        await self.load_extension(
            "commands.palworld"
        )

        await self.load_extension(
            "services.server_manager"
        )

        await self.load_extension(
            "services.idle_shutdown"
        )

        await self.load_extension(
            "services.reaction_roles"
        )

        await self.load_extension(
            "monitors.player_activity"
        )

        await self.load_extension(
            "monitors.steam_updates"
        )

        guild = discord.Object(
            id=DISCORD_GUILD_ID
        )

        self.tree.copy_global_to(
            guild=guild
        )

        synced = await self.tree.sync(
            guild=guild
        )

        logger.info(
            "Synced %s commands to guild %s",
            len(synced),
            DISCORD_GUILD_ID,
        )

    async def on_ready(self) -> None:
        if self.user is None:
            return

        logger.info(
            "Logged in as %s (ID: %s)",
            self.user,
            self.user.id,
        )

initialize_database()

bot = GameServerBot()

@bot.tree.error
async def handle_app_command_error(
    interaction: discord.Interaction,
    error: app_commands.AppCommandError,
) -> None:
    if isinstance(
        error,
        app_commands.MissingRole,
    ):
        message = (
            "You do not have permission "
            "to use this command."
        )

        if interaction.response.is_done():
            await interaction.followup.send(
                message,
                ephemeral=True,
            )
        else:
            await interaction.response.send_message(
                message,
                ephemeral=True,
            )

        return

    if isinstance(
        error,
        app_commands.CheckFailure,
    ):
        message = (
            "Please use the designated "
            "game-server channel."
        )

        if interaction.response.is_done():
            await interaction.followup.send(
                message,
                ephemeral=True,
            )
        else:
            await interaction.response.send_message(
                message,
                ephemeral=True,
            )

        return

    logger.exception(
        "Unhandled application command error",
        exc_info=error,
    )

    if interaction.response.is_done():
        await interaction.followup.send(
            "An unexpected error occurred.",
            ephemeral=True,
        )
    else:
        await interaction.response.send_message(
            "An unexpected error occurred.",
            ephemeral=True,
        )

bot.run(
    DISCORD_TOKEN,
    log_handler=None,
)
