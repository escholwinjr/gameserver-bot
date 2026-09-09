import asyncio
import logging
import subprocess

from discord.ext import commands, tasks

from config import (
    BOT_CHANNEL_ID,
    SERVER_NAME,
    SERVER_STATE_POLL_SECONDS,
    SERVER_START_WRAPPER,
    SERVER_STOP_WRAPPER,
    SERVER_UPDATE_WRAPPER,
    SYSTEMD_SERVICE,
)


logger = logging.getLogger(__name__)


def service_is_running() -> bool:
    result = subprocess.run(
        [
            "systemctl",
            "is-active",
            "--quiet",
            "{}.service".format(SYSTEMD_SERVICE),
        ],
        check=False,
    )

    return result.returncode == 0


class ServerManager(commands.Cog):
    def __init__(self, bot: commands.Bot) -> None:
        self.bot = bot
        self.previous_running = None
        self.monitor_server_state.start()

    def cog_unload(self) -> None:
        self.monitor_server_state.cancel()

    async def is_running(self) -> bool:
        return await asyncio.to_thread(
            service_is_running
        )

    async def send_lifecycle_announcement(
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
                    "Unable to fetch lifecycle channel %s",
                    BOT_CHANNEL_ID,
                )
                return

        try:
            await channel.send(message)
        except Exception:
            logger.exception(
                "Unable to send lifecycle announcement "
                "to channel %s",
                BOT_CHANNEL_ID,
            )
            return

    async def announce_starting(self) -> None:
        await self.send_lifecycle_announcement(
            "🚀 **{}** is starting.".format(
                SERVER_NAME,
            )
        )

    async def announce_stopped(self) -> None:
        await self.send_lifecycle_announcement(
            "🔴 **{}** has stopped.".format(
                SERVER_NAME,
            )
        )

    @tasks.loop(seconds=SERVER_STATE_POLL_SECONDS)
    async def monitor_server_state(self) -> None:
        try:
            running = await self.is_running()
        except Exception:
            logger.exception(
                "Unable to check %s service state.",
                SYSTEMD_SERVICE,
            )
            return

        if self.previous_running is None:
            self.previous_running = running
            logger.info(
                "Initialized %s service state as %s.",
                SYSTEMD_SERVICE,
                "online" if running else "offline",
            )
            return

        if running == self.previous_running:
            return

        was_running = self.previous_running
        self.previous_running = running

        logger.info(
            "%s service transitioned from %s to %s.",
            SYSTEMD_SERVICE,
            "online" if was_running else "offline",
            "online" if running else "offline",
        )

        try:
            if running:
                await self.announce_starting()
            else:
                await self.announce_stopped()
        except Exception:
            logger.exception(
                "Unable to announce %s service transition.",
                SYSTEMD_SERVICE,
            )

    @monitor_server_state.before_loop
    async def before_monitor_server_state(self) -> None:
        await self.bot.wait_until_ready()

    async def start(self) -> None:
        if await self.is_running():
            logger.info(
                "%s is already running.",
                SYSTEMD_SERVICE,
            )
            return

        logger.info(
            "Starting %s through privileged wrapper.",
            SYSTEMD_SERVICE,
        )

        await asyncio.to_thread(
            subprocess.run,
            [
                "sudo",
                "-n",
                SERVER_START_WRAPPER,
            ],
            check=True,
            capture_output=True,
            text=True,
        )

        logger.info(
            "%s start command completed successfully.",
            SYSTEMD_SERVICE,
        )

    async def stop(self) -> None:
        logger.info(
            "Stopping %s through privileged wrapper.",
            SYSTEMD_SERVICE,
        )

        await asyncio.to_thread(
            subprocess.run,
            [
                "sudo",
                "-n",
                SERVER_STOP_WRAPPER,
            ],
            check=True,
            capture_output=True,
            text=True,
        )

        logger.info(
            "%s stopped successfully.",
            SYSTEMD_SERVICE,
        )

    async def update(self) -> None:
        logger.info(
            "Updating %s through privileged wrapper.",
            SYSTEMD_SERVICE,
        )

        await asyncio.to_thread(
            subprocess.run,
            [
                "sudo",
                "-n",
                SERVER_UPDATE_WRAPPER,
            ],
            check=True,
            capture_output=True,
            text=True,
        )

        logger.info(
            "%s update completed successfully.",
            SYSTEMD_SERVICE,
        )

async def setup(bot: commands.Bot) -> None:
    await bot.add_cog(
        ServerManager(bot)
    )
