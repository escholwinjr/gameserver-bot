import re
import subprocess
import asyncio
import logging
from pathlib import Path

from discord.ext import commands, tasks
from config import (
    BOT_CHANNEL_ID,
    STEAM_UPDATE_CHECK_HOURS,
)

logger = logging.getLogger(__name__)

STEAMCMD = "/home/palworld/steamcmd/steamcmd.sh"
APPMANIFEST = Path(
    "/home/palworld/server/steamapps/appmanifest_2394010.acf"
)

def get_installed_build() -> str:
    manifest_text = APPMANIFEST.read_text(
        encoding="utf-8",
        errors="replace",
    )

    match = re.search(
        r'"buildid"\s+"([^"]+)"',
        manifest_text,
    )

    if match is None:
        raise RuntimeError(
            "Could not find build ID in {}".format(
                APPMANIFEST
            )
        )

    return match.group(1)

def get_latest_build() -> str:
    result = subprocess.run(
        [
            "sudo",
            "-n",
            "/usr/local/sbin/palworld-steam-build",
        ],
        capture_output=True,
        text=True,
        check=True,
    )

    match = re.search(
        r'"buildid"\s+"([^"]+)"',
        result.stdout,
    )

    if match is None:
        raise RuntimeError(
            "Could not find latest Steam build ID."
        )

    return match.group(1)

class SteamUpdateMonitor(commands.Cog):
    def __init__(self, bot: commands.Bot) -> None:
        self.bot = bot
        self.last_announced_build = None
        self.check_for_updates.start()

    def cog_unload(self) -> None:
        self.check_for_updates.cancel()

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

    @tasks.loop(
        hours=STEAM_UPDATE_CHECK_HOURS
    )

    async def check_for_updates(self) -> None:
        installed_build = await asyncio.to_thread(
            get_installed_build
        )

        latest_build = await asyncio.to_thread(
            get_latest_build
        )

        logger.info(
            "Steam build check: installed=%s latest=%s",
            installed_build,
            latest_build,
        )

        if installed_build == latest_build:
            self.last_announced_build = None
            return

        if self.last_announced_build == latest_build:
            return

        self.last_announced_build = latest_build

        logger.warning(
            "Steam update available: installed=%s latest=%s",
            installed_build,
            latest_build,
        )

        await self.send_update_message(
            "⚠️ **Palworld update available!**\n"
            "Installed build: **{}**\n"
            "Latest build: **{}**".format(
                installed_build,
                latest_build,
            )
        )

    @check_for_updates.before_loop
    async def before_check_for_updates(self) -> None:
        await self.bot.wait_until_ready()


async def setup(bot: commands.Bot) -> None:
    await bot.add_cog(
        SteamUpdateMonitor(bot)
    )
