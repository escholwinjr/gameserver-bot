import asyncio
import logging
import subprocess

from discord.ext import commands, tasks
from api.palworld import get_players
from player_store import save_player
from config import (
    IDLE_SHUTDOWN_ENABLED,
    PLAYER_ACTIVITY_CHANNEL_ID,
    PLAYER_POLL_SECONDS,
    SYSTEMD_SERVICE,
)

logger = logging.getLogger(__name__)

def palworld_is_running() -> bool:
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

class PlayerActivityMonitor(commands.Cog):
    def __init__(self, bot: commands.Bot) -> None:
        self.bot = bot
        self.online_players = {}
        self.initialized = False
        self.poll.start()

    def cog_unload(self) -> None:
        self.poll.cancel()

    async def send_activity_message(
        self,
        message: str,
    ) -> None:
        channel = self.bot.get_channel(
            PLAYER_ACTIVITY_CHANNEL_ID
        )

        if channel is None:
            try:
                channel = await self.bot.fetch_channel(
                    PLAYER_ACTIVITY_CHANNEL_ID
                )
            except Exception:
                logger.exception(
                    "Unable to fetch player activity channel %s",
                    PLAYER_ACTIVITY_CHANNEL_ID,
                )
                return
        await channel.send(message)

    @tasks.loop(seconds=PLAYER_POLL_SECONDS)
    async def poll(self) -> None:
        server_running = await asyncio.to_thread(
            palworld_is_running
        )

        if not server_running:
            self.online_players = {}
            self.initialized = False
            return

        try:
            players = await get_players()
        except Exception as error:
            logger.info(
                "Palworld REST API is not ready yet: %s",
                error,
            )
            return

        current_players = {}

        for player in players:
            save_player(player)

            player_id = player.get("playerId")

            if not player_id:
                continue

            player_id = str(player_id).strip()

            if player_id.lower() == "none":
                continue

            current_players[player_id] = player

        if not self.initialized:
            self.online_players = current_players
            self.initialized = True

            if not IDLE_SHUTDOWN_ENABLED:
                logger.info(
                    "Idle shutdown is disabled by configuration."
                )
            elif not current_players:
                idle_shutdown = self.bot.get_cog(
                    "IdleShutdownService"
                )

                if idle_shutdown is None:
                    logger.error(
                        "IdleShutdownService is not loaded."
                    )
                else:
                    await idle_shutdown.server_became_empty()

            return

        joined_ids = (
            current_players.keys()
            - self.online_players.keys()
        )

        left_ids = (
            self.online_players.keys()
            - current_players.keys()
        )

        for player_id in joined_ids:
            player = current_players[player_id]

            logger.info(
                "Player joined: %s (%s)",
                player.get("name", "Unknown"),
                player_id,
            )

            await self.send_activity_message(
                "🟢 **{}** joined the server.".format(
                    player.get("name", "Unknown")
                )
            )

        for player_id in left_ids:
            player = self.online_players[player_id]

            logger.info(
                "Player left: %s (%s)",
                player.get("name", "Unknown"),
                player_id,
            )

            await self.send_activity_message(
                "🔴 **{}** left the server.".format(
                    player.get("name", "Unknown")
                )
            )

        idle_shutdown = self.bot.get_cog(
            "IdleShutdownService"
        )

        if idle_shutdown is None:
            logger.error(
                "IdleShutdownService is not loaded."
            )
        else:
            if joined_ids:
                await idle_shutdown.player_joined()

        if (
            IDLE_SHUTDOWN_ENABLED
            and self.online_players
            and not current_players
        ):
            await idle_shutdown.server_became_empty()

        self.online_players = current_players

    @poll.before_loop
    async def before_poll(self) -> None:
        await self.bot.wait_until_ready()


async def setup(bot: commands.Bot) -> None:
    await bot.add_cog(
        PlayerActivityMonitor(bot)
    )
