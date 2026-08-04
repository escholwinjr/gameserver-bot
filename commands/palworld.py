import asyncio
import re
from pathlib import Path
from typing import Any, Dict, Optional, Tuple

import discord
from discord import app_commands
from discord.ext import commands

from api.palworld import get_players, get_server_info
from checks import bot_channel_only
from config import (
    BOT_CHANNEL_ID,
    SERVER_NAME,
    STEAM_APP_ID,
    STEAM_INSTALL_DIR,
    SYSTEMD_SERVICE,
)

from player_store import get_player_by_name, save_player
from services.server_manager import ServerManager

async def run_command(*args: str) -> Tuple[int, str, str]:
    process = await asyncio.create_subprocess_exec(
        *args,
        stdout=asyncio.subprocess.PIPE,
        stderr=asyncio.subprocess.PIPE,
    )

    stdout_bytes, stderr_bytes = await process.communicate()

    stdout = stdout_bytes.decode(
        encoding="utf-8",
        errors="replace",
    ).strip()

    stderr = stderr_bytes.decode(
        encoding="utf-8",
        errors="replace",
    ).strip()

    return process.returncode, stdout, stderr


def get_manifest_path() -> Path:
    return (
        STEAM_INSTALL_DIR
        / "steamapps"
        / "appmanifest_{}.acf".format(STEAM_APP_ID)
    )


def read_build_id() -> str:
    manifest_path = get_manifest_path()

    if not manifest_path.exists():
        raise FileNotFoundError(
            "Steam manifest not found: {}".format(
                manifest_path
            )
        )

    manifest_text = manifest_path.read_text(
        encoding="utf-8",
        errors="replace",
    )

    match = re.search(
        r'"buildid"\s+"([^"]+)"',
        manifest_text,
    )

    if match is None:
        raise RuntimeError(
            "Could not locate build ID in {}".format(
                manifest_path
            )
        )

    return match.group(1)


def player_name(player: Dict[str, Any]) -> str:
    for key in (
        "name",
        "playerName",
        "player_name",
        "userName",
        "username",
    ):
        value = player.get(key)

        if value:
            return str(value)

    return "Unknown Player"


def player_id(
    player: Dict[str, Any],
) -> Optional[str]:
    for key in (
        "playerId",
        "player_id",
        "userId",
        "user_id",
        "steamId",
        "steam_id",
    ):
        value = player.get(key)

        if value:
            return str(value)

    return None


class PalworldCommands(commands.Cog):
    def __init__(self, bot: commands.Bot) -> None:
        self.bot = bot

    @app_commands.command(
        name="start",
        description="Start the Palworld server.",
    )
    @app_commands.check(bot_channel_only)
    async def start(
        self,
        interaction: discord.Interaction,
    ) -> None:
        await interaction.response.defer(
            thinking=True
        )

        server_manager = self.bot.get_cog(
            "ServerManager"
        )

        if server_manager is None:
            await interaction.followup.send(
                "❌ ServerManager is unavailable.",
                ephemeral=True,
            )
            return

        if await server_manager.is_running():
            await interaction.followup.send(
                "🟢 **{}** is already running.".format(
                    SERVER_NAME,
                )
            )
            return

        try:
            await server_manager.start()
        except Exception as error:
            await interaction.followup.send(
                (
                    "❌ Failed to start the server.\n"
                    "`{}: {}`"
                ).format(
                    type(error).__name__,
                    error,
                ),
                ephemeral=True,
            )
            return

        await interaction.followup.send(
            "🚀 **{}** is starting...".format(
                SERVER_NAME,
            )
        )

    @app_commands.command(
        name="status",
        description="Show the Palworld server status.",
    )
    @app_commands.check(bot_channel_only)
    async def status(
        self,
        interaction: discord.Interaction,
    ) -> None:
        await interaction.response.defer(thinking=True)

        return_code, stdout, stderr = await run_command(
            "systemctl",
            "is-active",
            SYSTEMD_SERVICE,
        )

        service_active = (
            return_code == 0
            and stdout == "active"
        )

        embed = discord.Embed(
            title="{} Status".format(SERVER_NAME),
            timestamp=discord.utils.utcnow(),
        )

        if service_active:
            embed.colour = discord.Colour.green()
            embed.add_field(
                name="Service",
                value="🟢 Online",
                inline=True,
            )
        else:
            embed.colour = discord.Colour.red()

            status_text = stdout or stderr or "unknown"

            embed.add_field(
                name="Service",
                value="🔴 {}".format(
                    status_text.title()
                ),
                inline=True,
            )

        try:
            players = await get_players()

            embed.add_field(
                name="Players",
                value=str(len(players)),
                inline=True,
            )
        except Exception:
            embed.add_field(
                name="Players",
                value="Unavailable",
                inline=True,
            )

        try:
            server_info = await get_server_info()

            version = (
                server_info.get("version")
                or server_info.get("serverVersion")
                or server_info.get("server_version")
            )

            if version:
                embed.add_field(
                    name="Game Version",
                    value="`{}`".format(version),
                    inline=True,
                )
        except Exception:
            pass

        await interaction.followup.send(
            embed=embed
        )

    @app_commands.command(
        name="players",
        description="Show players currently connected to Palworld.",
    )
    @app_commands.check(bot_channel_only)
    async def players(
        self,
        interaction: discord.Interaction,
    ) -> None:
        await interaction.response.defer(thinking=True)

        try:
            players = await get_players()
        except Exception as error:
            await interaction.followup.send(
                (
                    "I could not retrieve the Palworld player list.\n"
                    "`{}: {}`".format(
                        type(error).__name__,
                        error,
                    )
                ),
                ephemeral=True,
            )
            return

        embed = discord.Embed(
            title="{} Players".format(SERVER_NAME),
            timestamp=discord.utils.utcnow(),
        )

        if not players:
            embed.description = (
                "No players are currently online."
            )
            embed.colour = discord.Colour.greyple()

            await interaction.followup.send(
                embed=embed
            )
            return

        embed.colour = discord.Colour.green()

        suffix = "" if len(players) == 1 else "s"

        embed.description = (
            "**{} player{} online**".format(
                len(players),
                suffix,
            )
        )

        player_lines = []

        for player in players:
            save_player(player)
            name = player_name(player)
            identifier = player_id(player)

            if identifier:
                player_lines.append(
                    "• **{}**".format(
                        name,
                        identifier,
                    )
                )
            else:
                player_lines.append(
                    "• **{}**".format(name)
                )

        player_text = "\n".join(player_lines)

        if len(player_text) <= 1024:
            embed.add_field(
                name="Connected Players",
                value=player_text,
                inline=False,
            )
        else:
            embed.description += (
                "\n\n" + player_text[:3800]
            )

        await interaction.followup.send(
            embed=embed
        )

    @app_commands.command(
        name="player",
        description="Look up a Palworld player by character name.",
    )
    @app_commands.describe(
        name="The player's Palworld character name.",
    )
    @app_commands.check(bot_channel_only)
    async def player(
        self,
        interaction: discord.Interaction,
        name: str,
    ) -> None:
        await interaction.response.defer(thinking=True)

        player = await asyncio.to_thread(
            get_player_by_name,
            name,
        )

        if player is None:
            await interaction.followup.send(
                "No player named `{}` was found.".format(name),
                ephemeral=True,
            )
            return

        embed = discord.Embed(
            title="Player: {}".format(player["name"]),
            colour=discord.Colour.blue(),
            timestamp=discord.utils.utcnow(),
        )

        embed.add_field(
            name="Account Name",
            value=player["account_name"] or "Unknown",
            inline=True,
        )

        embed.add_field(
            name="Level",
            value=str(player["level"] or "Unknown"),
            inline=True,
        )

        embed.add_field(
            name="Last Seen",
            value="`{}`".format(player["last_seen"]),
            inline=False,
        )

        embed.add_field(
            name="Steam User ID",
            value="`{}`".format(player["user_id"] or "Unknown"),
            inline=False,
        )

        embed.add_field(
            name="Player ID",
            value="`{}`".format(player["player_id"]),
            inline=False,
        )

        await interaction.followup.send(embed=embed)

    @app_commands.command(
        name="version",
        description="Show the installed Palworld server version.",
    )
    @app_commands.check(bot_channel_only)
    async def version(
        self,
        interaction: discord.Interaction,
    ) -> None:
        await interaction.response.defer(thinking=True)

        embed = discord.Embed(
            title="{} Version".format(SERVER_NAME),
            timestamp=discord.utils.utcnow(),
        )

        had_error = False

        try:
            build_id = await asyncio.to_thread(
                read_build_id
            )

            embed.add_field(
                name="Steam Build ID",
                value="`{}`".format(build_id),
                inline=False,
            )
        except Exception as error:
            had_error = True

            embed.add_field(
                name="Steam Build ID",
                value=(
                    "Unable to read the Steam manifest.\n"
                    "`{}: {}`".format(
                        type(error).__name__,
                        error,
                    )
                ),
                inline=False,
            )

        try:
            server_info = await get_server_info()

            game_version = (
                server_info.get("version")
                or server_info.get("serverVersion")
                or server_info.get("server_version")
            )

            if game_version:
                embed.add_field(
                    name="Palworld Version",
                    value="`{}`".format(
                        game_version
                    ),
                    inline=False,
                )
        except Exception:
            pass

        if had_error:
            embed.colour = discord.Colour.red()
        else:
            embed.colour = discord.Colour.blue()

        await interaction.followup.send(
            embed=embed
        )


async def setup(bot: commands.Bot) -> None:
    await bot.add_cog(
        PalworldCommands(bot)
    )
