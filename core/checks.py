import discord
from discord import app_commands

from config import BOT_CHANNEL_ID


def bot_channel_only(
    interaction: discord.Interaction,
) -> bool:
    if interaction.channel_id != BOT_CHANNEL_ID:
        raise app_commands.CheckFailure(
            "This command can only be used in the designated "
            "game-server channel."
        )

    return True
