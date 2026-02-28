from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Mapping
import os


@dataclass(slots=True)
class StartCommands:
    default: list[str]
    windows: list[str] | None = None
    posix: list[str] | None = None

    def for_platform(self) -> list[str]:
        if os.name == "nt" and self.windows:
            return list(self.windows)
        if os.name != "nt" and self.posix:
            return list(self.posix)
        return list(self.default)

    def to_dict(self) -> dict[str, Any]:
        return {
            "default": list(self.default),
            "windows": list(self.windows) if self.windows else None,
            "posix": list(self.posix) if self.posix else None,
        }

    @classmethod
    def from_dict(cls, data: Mapping[str, Any]) -> StartCommands:
        return cls(
            default=list(data["default"]),
            windows=list(data["windows"]) if data.get("windows") else None,
            posix=list(data["posix"]) if data.get("posix") else None,
        )


@dataclass(slots=True)
class InstallRequest:
    loader: str
    instance_dir: Path
    minecraft_version: str = "latest"
    loader_version: str | None = None
    build: str | int | None = None
    java_path: str = "java"
    accept_eula: bool = False
    overwrite: bool = True
    server_properties: Mapping[str, str] | None = None


@dataclass(slots=True)
class ServerManifest:
    loader: str
    minecraft_version: str
    start: StartCommands
    loader_version: str | None = None
    build: str | None = None
    java_required: int | None = None
    downloaded_urls: list[str] = field(default_factory=list)
    schema_version: int = 1
    installed_at_utc: str = field(
        default_factory=lambda: datetime.now(timezone.utc).isoformat()
    )

    def to_dict(self) -> dict[str, Any]:
        return {
            "schema_version": self.schema_version,
            "loader": self.loader,
            "minecraft_version": self.minecraft_version,
            "loader_version": self.loader_version,
            "build": self.build,
            "java_required": self.java_required,
            "start": self.start.to_dict(),
            "downloaded_urls": list(self.downloaded_urls),
            "installed_at_utc": self.installed_at_utc,
        }

    @classmethod
    def from_dict(cls, data: Mapping[str, Any]) -> ServerManifest:
        return cls(
            schema_version=int(data.get("schema_version", 1)),
            loader=str(data["loader"]),
            minecraft_version=str(data["minecraft_version"]),
            loader_version=str(data["loader_version"])
            if data.get("loader_version") is not None
            else None,
            build=str(data["build"]) if data.get("build") is not None else None,
            java_required=int(data["java_required"])
            if data.get("java_required") is not None
            else None,
            start=StartCommands.from_dict(data["start"]),
            downloaded_urls=[str(url) for url in data.get("downloaded_urls", [])],
            installed_at_utc=str(data.get("installed_at_utc", "")),
        )


@dataclass(slots=True)
class InstallResult:
    instance_dir: Path
    manifest_path: Path
    manifest: ServerManifest
    server_jar: Path | None = None
    notes: list[str] = field(default_factory=list)
