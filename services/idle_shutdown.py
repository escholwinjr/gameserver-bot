import asyncio
import logging
from typing import Optional

from discord.ext import commands

from config import (
    BOT_CHANNEL_ID,
    IDLE_SHUTDOWN_ENABLED,
    IDLE_SHUTDOWN_GRACE_SECONDS,
    IDLE_SHUTDOWN_SECONDS,
)


logger = logging.getLogger(__name__)


def format_duration(seconds: int) -> str:
    if seconds % 3600 == 0:
        hours = seconds // 3600

        return "{} hour{}".format(
            hours,
            "" if hours == 1 else "s",
        )

    if seconds % 60 == 0:
        minutes = seconds // 60

        return "{} minute{}".format(
            minutes,
            "" if minutes == 1 else "s",
        )

    return "{} second{}".format(
        seconds,
        "" if seconds == 1 else "s",
    )


class IdleShutdownService(commands.Cog):
    def __init__(self, bot: commands.Bot) -> None:
        self.bot = bot
        self.shutdown_task: Optional[asyncio.Task] = None
        self.countdown_announced = False

    async def send_update_message(
        self,
        message: str,
    ) -> None:
        channel = self.bot.get_channel(BOT_CHANNEL_ID)

        if channel is None:
            try:
                channel = await self.bot.fetch_channel(
                    BOT_CHANNEL_ID
                )
            except Exception:
                logger.exception(
                    "Unable to fetch update channel %s",
                    BOT_CHANNEL_ID,
                )
                return

        await channel.send(message)

    async def server_became_empty(
        self,
        reason: str,
    ) -> None:
        if not IDLE_SHUTDOWN_ENABLED:
            logger.info(
                "Idle shutdown is disabled."
            )
            return

        if self.shutdown_task is not None:
            return

        if reason == "startup":
            logger.info(
                "Server started with no players. "
                "Starting %s idle grace period.",
                format_duration(
                    IDLE_SHUTDOWN_GRACE_SECONDS
                ),
            )
        elif reason == "players_left":
            logger.info(
                "Last player left the server. "
                "Starting %s idle grace period.",
                format_duration(
                    IDLE_SHUTDOWN_GRACE_SECONDS
                ),
            )
        else:
            logger.info(
                "Server is empty. Starting %s idle grace period.",
                format_duration(
                    IDLE_SHUTDOWN_GRACE_SECONDS
                ),
            )

        self.countdown_announced = False

        self.shutdown_task = asyncio.create_task(
            self.shutdown_sequence()
        )

    async def player_joined(self) -> None:
        if self.shutdown_task is None:
            return

        logger.info(
            "Player joined. Canceling pending idle shutdown."
        )

        self.shutdown_task.cancel()
        self.shutdown_task = None

        if self.countdown_announced:
            await self.send_update_message(
                "✅ **Idle shutdown canceled.** "
                "A player joined the Palworld server."
            )

        self.countdown_announced = False

    async def shutdown_sequence(self) -> None:
        try:
            await asyncio.sleep(
                IDLE_SHUTDOWN_GRACE_SECONDS
            )

            if not IDLE_SHUTDOWN_ENABLED:
                logger.info(
                    "Idle shutdown was disabled during "
                    "the grace period."
                )
                return

            shutdown_duration = format_duration(
                IDLE_SHUTDOWN_SECONDS
            )

            logger.info(
                "Idle grace period completed. Starting "
                "%s shutdown countdown.",
                shutdown_duration,
            )

            self.countdown_announced = True

            await self.send_update_message(
                "⚠️ **Palworld is currently empty.**\n"
                "The server will shut down in **{}** "
                "unless someone joins.".format(
                    shutdown_duration
                )
            )

            await asyncio.sleep(
                IDLE_SHUTDOWN_SECONDS
            )

            if not IDLE_SHUTDOWN_ENABLED:
                logger.info(
                    "Idle shutdown was disabled during "
                    "the shutdown countdown."
                )
                return

            logger.info(
                "Idle timeout reached. Stopping Palworld."
            )

            total_idle = (
                IDLE_SHUTDOWN_GRACE_SECONDS
                + IDLE_SHUTDOWN_SECONDS
            )

            await self.send_update_message(
                "🌙 **Palworld is shutting down.**\n\n"
                "The server has been empty for **{}**.\n\n"
                "Good night! 😴".format(
                    format_duration(
                        total_idle
                    )
                )
            )

            server_manager = self.bot.get_cog(
                "ServerManager"
            )

            if server_manager is None:
                logger.error(
                    "ServerManager is not loaded."
                )

                await self.send_update_message(
                    "❌ **Palworld failed to shut down.**\n"
                    "The server manager is unavailable."
                )
                return

            try:
                await server_manager.stop()
            except Exception:
                logger.exception(
                    "Unable to stop Palworld after "
                    "idle timeout."
                )

                await self.send_update_message(
                    "❌ **Palworld failed to shut down.**\n"
                    "An administrator needs to check "
                    "the server."
                )
                return

            logger.info(
                "Palworld stopped successfully after "
                "idle timeout."
            )

        except asyncio.CancelledError:
            logger.info(
                "Pending idle shutdown canceled."
            )
            raise

        finally:
            self.shutdown_task = None
            self.countdown_announced = False


async def setup(bot: commands.Bot) -> None:
    await bot.add_cog(
        IdleShutdownService(bot)
    )
