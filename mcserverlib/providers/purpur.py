from __future__ import annotations

from pathlib import Path

from ..exceptions import VersionResolutionError
from ..http import HttpClient
from ..minecraft import minecraft_java_requirement
from ..models import InstallRequest, ServerManifest, StartCommands
from ..utils import pick_latest_version
from .base import LoaderProvider, ProviderInstallResult

PURPUR_API = "https://api.purpurmc.org/v2/purpur"


class PurpurProvider(LoaderProvider):
    loader_id = "purpur"

    def _resolve_mc_version(self, request: InstallRequest, http_client: HttpClient) -> str:
        versions_data = http_client.get_json(PURPUR_API)
        versions = [str(v) for v in versions_data.get("versions", [])]
        if not versions:
            raise VersionResolutionError("Purpur API returned no versions.")
        if request.minecraft_version == "latest":
            return pick_latest_version(versions, stable_only=True)
        if request.minecraft_version not in versions:
            raise VersionResolutionError(
                f"Purpur version {request.minecraft_version} was not found."
            )
        return request.minecraft_version

    def install(self, request: InstallRequest, http_client: HttpClient) -> ProviderInstallResult:
        mc_version = self._resolve_mc_version(request=request, http_client=http_client)
        version_info = http_client.get_json(f"{PURPUR_API}/{mc_version}")

        if request.build is not None:
            build = str(request.build)
        else:
            build = str(version_info.get("builds", {}).get("latest", ""))
            if not build:
                raise VersionResolutionError(f"Purpur has no build for {mc_version}.")

        build_info = http_client.get_json(f"{PURPUR_API}/{mc_version}/{build}")
        md5 = build_info.get("md5")

        download_url = f"{PURPUR_API}/{mc_version}/{build}/download"
        server_jar = request.instance_dir / "server.jar"
        http_client.download(
            url=download_url,
            destination=server_jar,
            expected_hash=md5,
            hash_algorithm="md5",
        )

        manifest = ServerManifest(
            loader=self.loader_id,
            minecraft_version=mc_version,
            build=build,
            java_required=minecraft_java_requirement(http_client, mc_version),
            start=StartCommands(default=["{java}", "-jar", "server.jar", "nogui"]),
            downloaded_urls=[download_url],
        )
        return ProviderInstallResult(manifest=manifest, server_jar=Path(server_jar))
