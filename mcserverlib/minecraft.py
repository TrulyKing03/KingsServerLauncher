from __future__ import annotations

from typing import Any

from .exceptions import VersionResolutionError
from .http import HttpClient

MOJANG_MANIFEST_URL = "https://piston-meta.mojang.com/mc/game/version_manifest_v2.json"


def resolve_mojang_version(
    http_client: HttpClient, requested_version: str
) -> tuple[str, dict[str, Any]]:
    manifest = http_client.get_json(MOJANG_MANIFEST_URL)
    if requested_version == "latest":
        requested_version = manifest["latest"]["release"]

    version_url = None
    for version in manifest["versions"]:
        if version["id"] == requested_version:
            version_url = version["url"]
            break
    if version_url is None:
        raise VersionResolutionError(
            f"Minecraft version '{requested_version}' was not found in Mojang metadata."
        )

    version_data = http_client.get_json(version_url)
    return requested_version, version_data


def minecraft_java_requirement(http_client: HttpClient, minecraft_version: str) -> int | None:
    resolved, metadata = resolve_mojang_version(http_client, minecraft_version)
    _ = resolved
    java = metadata.get("javaVersion") or {}
    major = java.get("majorVersion")
    if major is None:
        return None
    return int(major)
