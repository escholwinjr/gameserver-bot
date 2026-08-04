import json
from pathlib import Path
from typing import Any, Dict, List, Optional

import aiohttp

from config import (
    PALWORLD_API_URL,
    PALWORLD_API_USER,
    PALWORLD_PASSWORD_FILE,
)


def read_palworld_password() -> str:
    password_file = Path(PALWORLD_PASSWORD_FILE)

    if not password_file.exists():
        raise FileNotFoundError(
            "Palworld password file not found: {}".format(
                password_file
            )
        )

    password = password_file.read_text(
        encoding="utf-8"
    ).strip()

    if not password:
        raise RuntimeError(
            "Palworld password file is empty."
        )

    return password


async def api_request(
    method: str,
    endpoint: str,
    json_body: Optional[Dict[str, Any]] = None,
) -> Any:
    password = read_palworld_password()

    base_url = PALWORLD_API_URL.rstrip("/")
    endpoint = endpoint.lstrip("/")
    url = "{}/{}".format(base_url, endpoint)

    timeout = aiohttp.ClientTimeout(total=15)

    auth = aiohttp.BasicAuth(
        PALWORLD_API_USER,
        password,
    )

    async with aiohttp.ClientSession(
        auth=auth,
        timeout=timeout,
    ) as session:
        async with session.request(
            method,
            url,
            json=json_body,
        ) as response:
            response_text = await response.text()

            if response.status >= 400:
                raise RuntimeError(
                    "Palworld API returned HTTP {}: {}".format(
                        response.status,
                        response_text,
                    )
                )

            if not response_text:
                return None

            try:
                return json.loads(response_text)
            except json.JSONDecodeError:
                return response_text


async def get_players() -> List[Dict[str, Any]]:
    data = await api_request(
        "GET",
        "players",
    )

    if not isinstance(data, dict):
        return []

    players = data.get("players", [])

    if not isinstance(players, list):
        return []

    return players


async def get_server_info() -> Dict[str, Any]:
    data = await api_request(
        "GET",
        "info",
    )

    if isinstance(data, dict):
        return data

    return {}


async def get_metrics() -> Dict[str, Any]:
    data = await api_request(
        "GET",
        "metrics",
    )

    if isinstance(data, dict):
        return data

    return {}


async def save_world() -> None:
    await api_request(
        "POST",
        "save",
    )


async def announce(message: str) -> None:
    await api_request(
        "POST",
        "announce",
        json_body={
            "message": message,
        },
    )
