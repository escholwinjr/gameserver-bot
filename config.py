import os
from pathlib import Path

from dotenv import load_dotenv


ENV_FILE = Path("/etc/gameserver-bot/bot.env")

load_dotenv(ENV_FILE)


def required_setting(name: str) -> str:
    value = os.getenv(name)

    if value is None or not value.strip():
        raise RuntimeError(f"Required setting {name} is missing.")

    return value.strip()


def optional_setting(name: str, default: str = "") -> str:
    value = os.getenv(name)

    if value is None:
        return default

    return value.strip()

def optional_bool(
    name: str,
    default: bool = False,
) -> bool:
    value = optional_setting(
        name,
        "true" if default else "false",
    ).lower()

    return value in (
        "1",
        "true",
        "yes",
        "on",
    )

DISCORD_TOKEN = required_setting("DISCORD_TOKEN")
DISCORD_GUILD_ID = int(required_setting("DISCORD_GUILD_ID"))

BOT_CHANNEL_ID = int(required_setting("BOT_CHANNEL_ID"))
REACTION_ROLE_CHANNEL_ID = int(
    required_setting("REACTION_ROLE_CHANNEL_ID")
)
PALWORLD_ROLE_ID = int(
    required_setting("PALWORLD_ROLE_ID")
)
VALHEIM_ROLE_ID = int(
    required_setting("VALHEIM_ROLE_ID")
)
WOW_ROLE_ID = int(
    required_setting("WOW_ROLE_ID")
)

ADMIN_ROLE = int(
    os.getenv("ADMIN_ROLE", "0")
)

PLAYER_ACTIVITY_CHANNEL_ID = int(
    optional_setting(
        "PLAYER_ACTIVITY_CHANNEL_ID",
        str(BOT_CHANNEL_ID),
    )
)

PALWORLD_API_URL = required_setting("PALWORLD_API_URL")
PALWORLD_API_USER = required_setting("PALWORLD_API_USER")
PALWORLD_PASSWORD_FILE = Path(
    required_setting("PALWORLD_PASSWORD_FILE")
)

IDLE_SHUTDOWN_ENABLED = optional_bool(
    "IDLE_SHUTDOWN_ENABLED",
    True,
)

SYSTEMD_SERVICE = optional_setting(
    "SYSTEMD_SERVICE",
    "palworld",
)

SERVER_START_WRAPPER = optional_setting(
    "SERVER_START_WRAPPER",
    "/usr/local/sbin/palworld-start",
)

SERVER_STOP_WRAPPER = optional_setting(
    "SERVER_STOP_WRAPPER",
    "/usr/local/sbin/palworld-stop",
)

STEAM_APP_ID = optional_setting(
    "STEAM_APP_ID",
    "2394010",
)

STEAM_INSTALL_DIR = Path(
    optional_setting(
        "STEAM_INSTALL_DIR",
        "/home/palworld/server",
    )
)

SERVER_NAME = optional_setting(
    "SERVER_NAME",
    "Palworld Server",
)

PLAYER_POLL_SECONDS = int(
    optional_setting(
        "PLAYER_POLL_SECONDS",
        "5",
    )
)

IDLE_SHUTDOWN_SECONDS = int(
    optional_setting(
        "IDLE_SHUTDOWN_SECONDS",
        "600",
    )
)

IDLE_SHUTDOWN_GRACE_SECONDS = int(
    optional_setting(
        "IDLE_SHUTDOWN_GRACE_SECONDS",
        "300",
    )
)

SERVER_STARTUP_TIMEOUT = int(
    optional_setting(
        "SERVER_STARTUP_TIMEOUT",
        "180",
    )
)

SERVER_SHUTDOWN_TIMEOUT = int(
    optional_setting(
        "SERVER_SHUTDOWN_TIMEOUT",
        "60",
    )
)

BACKUP_RETENTION_DAYS = int(
    optional_setting(
        "BACKUP_RETENTION_DAYS",
        "14",
    )
)

STEAM_UPDATE_CHECK_HOURS = int(
    optional_setting(
        "STEAM_UPDATE_CHECK_HOURS",
        "1",
    )
)
