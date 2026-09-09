import asyncio
import shutil
import time

import discord
import psutil
from discord import app_commands
from discord.ext import commands

from core.checks import bot_channel_only


class GeneralCommands(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot

    @app_commands.command(
        name="ping",
        description="Check the Discord bot's response time.",
    )
    @app_commands.check(bot_channel_only)
    async def ping(
        self,
        interaction: discord.Interaction,
    ) -> None:
        latency_ms = round(self.bot.latency * 1000)

        await interaction.response.send_message(
            f"🏓 Bot latency: `{latency_ms} ms`"
        )

    @app_commands.command(
        name="resources",
        description="Show host resource usage.",
    )
    @app_commands.check(bot_channel_only)
    async def resources(
        self,
        interaction: discord.Interaction,
    ) -> None:
        await interaction.response.defer(thinking=True)

        cpu_percent = await asyncio.to_thread(
            psutil.cpu_percent,
            1,
        )

        memory = psutil.virtual_memory()
        disk = shutil.disk_usage("/")

        embed = discord.Embed(
            title="Server Resources",
            timestamp=discord.utils.utcnow(),
        )

        embed.add_field(
            name="CPU",
            value=f"`{cpu_percent:.1f}%`",
            inline=True,
        )

        embed.add_field(
            name="Memory",
            value=(
                f"`{memory.percent:.1f}%`\n"
                f"{memory.used / 1024**3:.1f} GB / "
                f"{memory.total / 1024**3:.1f} GB"
            ),
            inline=True,
        )

        embed.add_field(
            name="Disk",
            value=(
                f"`{disk.used / disk.total * 100:.1f}%`\n"
                f"{disk.used / 1024**3:.1f} GB / "
                f"{disk.total / 1024**3:.1f} GB"
            ),
            inline=True,
        )

        await interaction.followup.send(embed=embed)


async def setup(bot: commands.Bot) -> None:
    await bot.add_cog(GeneralCommands(bot))
