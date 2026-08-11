import logging

import discord
from discord.ext import commands

from config import REACTION_ROLE_CHANNEL_ID


logger = logging.getLogger(__name__)


class ReactionRoles(commands.Cog):
    def __init__(self, bot: commands.Bot) -> None:
        self.bot = bot

    def is_bot_reaction(
        self,
        payload: discord.RawReactionActionEvent,
    ) -> bool:
        return (
            self.bot.user is not None
            and payload.user_id == self.bot.user.id
        )

    @commands.Cog.listener()
    async def on_raw_reaction_add(
        self,
        payload: discord.RawReactionActionEvent,
    ) -> None:
        if self.is_bot_reaction(payload):
            return

        if payload.channel_id != REACTION_ROLE_CHANNEL_ID:
            return

        logger.info(
            "Reaction added: guild=%s channel=%s "
            "message=%s user=%s emoji=%s",
            payload.guild_id,
            payload.channel_id,
            payload.message_id,
            payload.user_id,
            payload.emoji,
        )

    @commands.Cog.listener()
    async def on_raw_reaction_remove(
        self,
        payload: discord.RawReactionActionEvent,
    ) -> None:
        if self.is_bot_reaction(payload):
            return

        if payload.channel_id != REACTION_ROLE_CHANNEL_ID:
            return

        logger.info(
            "Reaction removed: guild=%s channel=%s "
            "message=%s user=%s emoji=%s",
            payload.guild_id,
            payload.channel_id,
            payload.message_id,
            payload.user_id,
            payload.emoji,
        )


async def setup(bot: commands.Bot) -> None:
    await bot.add_cog(
        ReactionRoles(bot)
    )
