import asyncio
import logging
import re
import subprocess
from pathlib import Path

from discord.ext import commands, tasks

from config import (
    BOT_CHANNEL_ID,
    STEAM_UPDATE_CHECK_HOURS,
    UPDATE_COUNTDOWN_SECONDS,
)


logger = logging.getLogger(__name__)

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


class SteamUpdateMonitor(commands.Cog):
    def __init__(self, bot: commands.Bot) -> None:
        self.bot = bot
        self.last_announced_build = None
        self.update_task = None

        self.check_for_updates.start()

    def cog_unload(self) -> None:
        self.check_for_updates.cancel()

        if self.update_task is not None:
            self.update_task.cancel()

    async def send_update_message(
        self,
        message: str,
    ) -> None:
        channel = self.bot.get_channel(
            BOT_CHANNEL_ID
        )

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

    async def update_countdown(
        self,
        installed_build: str,
        latest_build: str,
    ) -> None:
        try:
            duration = format_duration(
                UPDATE_COUNTDOWN_SECONDS
            )

            logger.info(
                "Starting update countdown: "
                "duration=%s installed=%s latest=%s",
                duration,
                installed_build,
                latest_build,
            )

            await self.send_update_message(
                "⚠️ **Palworld update detected.**\n"
                "Installed build: **{}**\n"
                "Latest build: **{}**\n\n"
                "The server will shut down in **{}** "
                "to install the update.".format(
                    installed_build,
                    latest_build,
                    duration,
                )
            )

            await asyncio.sleep(
                UPDATE_COUNTDOWN_SECONDS
            )

            logger.info(
                "Update countdown completed for build %s.",
                latest_build,
            )

            await self.send_update_message(
                "🧪 **Update countdown completed.**\n"
                "No shutdown or update was performed."
            )

        except asyncio.CancelledError:
            logger.info(
                "Update countdown canceled for build %s.",
                latest_build,
            )
            raise

        finally:
            self.update_task = None

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

        if self.update_task is not None:
            logger.info(
                "An update countdown is already running."
            )
            return

        self.last_announced_build = latest_build

        logger.warning(
            "Steam update available: "
            "installed=%s latest=%s",
            installed_build,
            latest_build,
        )

        self.update_task = asyncio.create_task(
            self.update_countdown(
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
