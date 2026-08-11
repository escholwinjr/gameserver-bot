import asyncio
import logging

import discord
from discord.ext import commands

from config import (
    PALWORLD_ROLE_ID,
    REACTION_ROLE_CHANNEL_ID,
    VALHEIM_ROLE_ID,
    WOW_ROLE_ID,
)
from player_store import get_bot_state, save_bot_state


logger = logging.getLogger(__name__)

SELECTOR_MESSAGE_STATE_KEY = "reaction_role_selector_message_id"
REACTION_ROLES = {
    1536792461685563452: {
        "name": "palworld",
        "role_id": PALWORLD_ROLE_ID,
        "label": "Palworld Players",
    },
    1536793141171200070: {
        "name": "Valheim",
        "role_id": VALHEIM_ROLE_ID,
        "label": "Valheim",
    },
    1536793173509275810: {
        "name": "wow",
        "role_id": WOW_ROLE_ID,
        "label": "WoW",
    },
}
SELECTOR_MESSAGE_CONTENT = (
    "**Choose your game roles**\n\n"
    "React below to add or remove a game role.\n\n"
    + "\n".join(
        "<:{}:{}> — {}".format(
            role_config["name"],
            emoji_id,
            role_config["label"],
        )
        for emoji_id, role_config in REACTION_ROLES.items()
    )
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

            for emoji_id, role_config in REACTION_ROLES.items():
                bot_has_reaction = any(
                    getattr(reaction.emoji, "id", None)
                    == emoji_id
                    and reaction.me
                    for reaction in message.reactions
                )

                if bot_has_reaction:
                    continue

                emoji = discord.PartialEmoji(
                    name=role_config["name"],
                    id=emoji_id,
                )

                try:
                    await message.add_reaction(emoji)
                except Exception:
                    logger.exception(
                        "Unable to add emoji %s to reaction-role "
                        "message %s.",
                        emoji_id,
                        message.id,
                    )

        except asyncio.CancelledError:
            raise
        except Exception:
            logger.exception(
                "Unable to initialize reaction-role selector message."
            )

    async def resolve_member(
        self,
        guild: discord.Guild,
        user_id: int,
    ):
        member = guild.get_member(user_id)

        if member is not None:
            return member

        try:
            return await guild.fetch_member(user_id)
        except discord.NotFound:
            logger.warning(
                "Unable to resolve reaction-role member %s "
                "in guild %s.",
                user_id,
                guild.id,
            )
        except discord.HTTPException:
            logger.exception(
                "Unable to fetch reaction-role member %s "
                "in guild %s.",
                user_id,
                guild.id,
            )

        return None

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

        if payload.guild_id is None:
            return

        role_config = REACTION_ROLES.get(payload.emoji.id)

        if role_config is None:
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

        guild = self.bot.get_guild(payload.guild_id)

        if guild is None:
            logger.error(
                "Unable to add reaction role: guild %s "
                "could not be resolved.",
                payload.guild_id,
            )
            return

        member = await self.resolve_member(
            guild,
            payload.user_id,
        )

        if member is None:
            return

        role = guild.get_role(role_config["role_id"])

        if role is None:
            logger.error(
                "Unable to add reaction role: role %s "
                "could not be resolved in guild %s.",
                role_config["role_id"],
                guild.id,
            )
            return

        if role in member.roles:
            return

        try:
            await member.add_roles(role)
            logger.info(
                "Assigned reaction role %s to member %s "
                "in guild %s.",
                role.id,
                member.id,
                guild.id,
            )
        except discord.HTTPException:
            logger.exception(
                "Unable to add reaction role %s to member %s "
                "in guild %s.",
                role.id,
                member.id,
                guild.id,
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

        if payload.guild_id is None:
            return

        role_config = REACTION_ROLES.get(payload.emoji.id)

        if role_config is None:
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

        guild = self.bot.get_guild(payload.guild_id)

        if guild is None:
            logger.error(
                "Unable to remove reaction role: guild %s "
                "could not be resolved.",
                payload.guild_id,
            )
            return

        member = await self.resolve_member(
            guild,
            payload.user_id,
        )

        if member is None:
            return

        role = guild.get_role(role_config["role_id"])

        if role is None:
            logger.error(
                "Unable to remove reaction role: role %s "
                "could not be resolved in guild %s.",
                role_config["role_id"],
                guild.id,
            )
            return

        if role not in member.roles:
            return

        try:
            await member.remove_roles(role)
            logger.info(
                "Removed reaction role %s from member %s "
                "in guild %s.",
                role.id,
                member.id,
                guild.id,
            )
        except discord.HTTPException:
            logger.exception(
                "Unable to remove reaction role %s from member %s "
                "in guild %s.",
                role.id,
                member.id,
                guild.id,
            )


async def setup(bot: commands.Bot) -> None:
    await bot.add_cog(
        ReactionRoles(bot)
    )
