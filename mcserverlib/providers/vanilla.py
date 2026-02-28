from __future__ import annotations

from pathlib import Path

from ..http import HttpClient
from ..minecraft import resolve_mojang_version
from ..models import InstallRequest, ServerManifest, StartCommands
from .base import LoaderProvider, ProviderInstallResult


class VanillaProvider(LoaderProvider):
    loader_id = "vanilla"

    def install(self, request: InstallRequest, http_client: HttpClient) -> ProviderInstallResult:
        resolved_mc_version, version_data = resolve_mojang_version(
            http_client=http_client,
            requested_version=request.minecraft_version,
        )

        server_download = version_data.get("downloads", {}).get("server")
        if not server_download:
            raise RuntimeError(
                f"Minecraft version {resolved_mc_version} does not publish a server download."
            )

        server_jar = request.instance_dir / "server.jar"
        http_client.download(
            url=server_download["url"],
            destination=server_jar,
            expected_hash=server_download.get("sha1"),
            hash_algorithm="sha1",
        )

        manifest = ServerManifest(
            loader=self.loader_id,
            minecraft_version=resolved_mc_version,
            java_required=version_data.get("javaVersion", {}).get("majorVersion"),
            start=StartCommands(default=["{java}", "-jar", "server.jar", "nogui"]),
            downloaded_urls=[server_download["url"]],
        )

        return ProviderInstallResult(manifest=manifest, server_jar=Path(server_jar))
