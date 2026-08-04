import asyncio
import logging
from typing import Optional

from discord.ext import commands

from config import (
    IDLE_SHUTDOWN_SECONDS,
    BOT_CHANNEL_ID,
)

logger = logging.getLogger(__name__)


class IdleShutdownService(commands.Cog):
    def __init__(self, bot: commands.Bot) -> None:
        self.bot = bot
        self.shutdown_task: Optional[asyncio.Task] = None

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

    async def server_became_empty(self) -> None:
        if self.shutdown_task is not None:
            return

        logger.info(
            "Server became empty. Starting idle shutdown timer."
        )

        minutes = IDLE_SHUTDOWN_SECONDS // 60

        await self.send_update_message(
            "⚠️ **Palworld is currently empty.**\n"
            "The server will shut down in **{} minute{}** "
            "unless someone joins.".format(
                minutes,
                "" if minutes == 1 else "s",
            )
        )

        self.shutdown_task = asyncio.create_task(
            self.shutdown_countdown()
        )

    async def player_joined(self) -> None:
        if self.shutdown_task is None:
            return

        logger.info(
            "Player joined. Canceling idle shutdown."
        )

        await self.send_update_message(
            "✅ **Idle shutdown canceled.** "
            "A player joined the Palworld server."
        )

        self.shutdown_task.cancel()
        self.shutdown_task = None

    async def shutdown_countdown(self) -> None:
        try:
            await asyncio.sleep(IDLE_SHUTDOWN_SECONDS)

            logger.info(
                "Idle timeout reached. Stopping Palworld."
            )

            await self.send_update_message(
                "🌙 **Palworld is shutting down.**\n"
                "The server has been empty for **{} minute{}**.".format(
                    IDLE_SHUTDOWN_SECONDS // 60,
                    "" if IDLE_SHUTDOWN_SECONDS // 60 == 1 else "s",
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
                    "Unable to stop Palworld after idle timeout."
                )

                await self.send_update_message(
                    "❌ **Palworld failed to shut down.**\n"
                    "An administrator needs to check the server."
                )
                return

            logger.info(
                "Palworld stopped successfully after idle timeout."
            )

        except asyncio.CancelledError:
            logger.info(
                "Idle shutdown canceled."
            )

        finally:
            self.shutdown_task = None

async def setup(bot: commands.Bot) -> None:
    await bot.add_cog(
        IdleShutdownService(bot)
    )
