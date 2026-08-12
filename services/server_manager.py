import asyncio
import logging
import subprocess

from discord.ext import commands

from config import (
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

    async def is_running(self) -> bool:
        return await asyncio.to_thread(
            service_is_running
        )

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
