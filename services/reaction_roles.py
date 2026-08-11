import asyncio
import logging

import discord
from discord.ext import commands

from config import REACTION_ROLE_CHANNEL_ID
from player_store import get_bot_state, save_bot_state


logger = logging.getLogger(__name__)

SELECTOR_MESSAGE_STATE_KEY = "reaction_role_selector_message_id"
PALWORLD_EMOJI_ID = 1536792461685563452
SELECTOR_MESSAGE_CONTENT = (
    "**Choose your game roles**\n\n"
    "React below to add or remove a game role.\n\n"
    "<:palworld:1536792461685563452> — Palworld Players"
)


class ReactionRoles(commands.Cog):
    def __init__(self, bot: commands.Bot) -> None:
        self.bot = bot
        self.selector_message_id = None
        self.initialization_task = asyncio.create_task(
            self.initialize_selector_message()
        )

    def cog_unload(self) -> None:
        self.initialization_task.cancel()

    def is_bot_reaction(
        self,
        payload: discord.RawReactionActionEvent,
    ) -> bool:
        return (
            self.bot.user is not None
            and payload.user_id == self.bot.user.id
        )

    async def initialize_selector_message(self) -> None:
        try:
            await self.bot.wait_until_ready()

            channel = self.bot.get_channel(
                REACTION_ROLE_CHANNEL_ID
            )

            if channel is None:
                try:
                    channel = await self.bot.fetch_channel(
                        REACTION_ROLE_CHANNEL_ID
                    )
                except Exception:
                    logger.exception(
                        "Unable to resolve reaction-role channel %s.",
                        REACTION_ROLE_CHANNEL_ID,
                    )
                    return

            if not isinstance(channel, discord.TextChannel):
                logger.error(
                    "Reaction-role channel %s is not a text channel.",
                    REACTION_ROLE_CHANNEL_ID,
                )
                return

            saved_message_id = await asyncio.to_thread(
                get_bot_state,
                SELECTOR_MESSAGE_STATE_KEY,
            )
            message = None

            if saved_message_id is not None:
                try:
                    message_id = int(saved_message_id)
                    message = await channel.fetch_message(
                        message_id
                    )
                except (TypeError, ValueError):
                    logger.error(
                        "Saved reaction-role message ID is invalid: %s",
                        saved_message_id,
                    )
                except discord.NotFound:
                    logger.warning(
                        "Saved reaction-role message %s no longer exists.",
                        saved_message_id,
                    )
                except Exception:
                    logger.exception(
                        "Unable to fetch reaction-role message %s.",
                        saved_message_id,
                    )
                    return

            if (
                message is not None
                and message.content != SELECTOR_MESSAGE_CONTENT
            ):
                try:
                    message = await message.edit(
                        content=SELECTOR_MESSAGE_CONTENT
                    )
                    logger.info(
                        "Updated reaction-role selector message %s "
                        "content.",
                        message.id,
                    )
                except Exception:
                    logger.exception(
                        "Unable to update reaction-role selector "
                        "message %s content.",
                        message.id,
                    )

            if message is None:
                try:
                    message = await channel.send(
                        SELECTOR_MESSAGE_CONTENT
                    )
                except Exception:
                    logger.exception(
                        "Unable to create reaction-role selector message."
                    )
                    return

                try:
                    await asyncio.to_thread(
                        save_bot_state,
                        SELECTOR_MESSAGE_STATE_KEY,
                        str(message.id),
                    )
                except Exception:
                    logger.exception(
                        "Unable to persist reaction-role message %s.",
                        message.id,
                    )
                    return

            self.selector_message_id = message.id

            emoji = discord.PartialEmoji(
                name="palworld",
                id=PALWORLD_EMOJI_ID,
            )

            has_reaction = any(
                getattr(reaction.emoji, "id", None)
                == PALWORLD_EMOJI_ID
                for reaction in message.reactions
            )

            if not has_reaction:
                try:
                    await message.add_reaction(emoji)
                except Exception:
                    logger.exception(
                        "Unable to add emoji %s to reaction-role "
                        "message %s.",
                        PALWORLD_EMOJI_ID,
                        message.id,
                    )

        except asyncio.CancelledError:
            raise
        except Exception:
            logger.exception(
                "Unable to initialize reaction-role selector message."
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

        if payload.message_id != self.selector_message_id:
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

        if payload.message_id != self.selector_message_id:
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
