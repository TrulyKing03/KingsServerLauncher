from __future__ import annotations

from pathlib import Path
import tempfile

from ..exceptions import InstallError, VersionResolutionError
from ..http import HttpClient
from ..minecraft import minecraft_java_requirement
from ..models import InstallRequest, ServerManifest, StartCommands
from ..subprocess_utils import run_checked
from .base import LoaderProvider, ProviderInstallResult

FABRIC_META = "https://meta.fabricmc.net/v2/versions"


class FabricProvider(LoaderProvider):
    loader_id = "fabric"

    def _resolve_mc_version(self, request: InstallRequest, http_client: HttpClient) -> str:
        game_versions = http_client.get_json(f"{FABRIC_META}/game")
        stable_game_versions = [v["version"] for v in game_versions if v.get("stable")]
        if request.minecraft_version == "latest":
            if not stable_game_versions:
                raise VersionResolutionError("Fabric returned no stable game versions.")
            return str(stable_game_versions[0])
        valid = {v["version"] for v in game_versions}
        if request.minecraft_version not in valid:
            raise VersionResolutionError(
                f"Fabric does not publish Minecraft version {request.minecraft_version}."
            )
        return request.minecraft_version

    def _resolve_loader_version(
        self, request: InstallRequest, http_client: HttpClient, mc_version: str
    ) -> str:
        versions = http_client.get_json(f"{FABRIC_META}/loader/{mc_version}")
        if request.loader_version:
            for entry in versions:
                loader = entry.get("loader") or {}
                if loader.get("version") == request.loader_version:
                    return request.loader_version
            raise VersionResolutionError(
                f"Fabric loader version {request.loader_version} not found for {mc_version}."
            )
        stable = [entry["loader"]["version"] for entry in versions if entry["loader"]["stable"]]
        if stable:
            return str(stable[0])
        if versions:
            return str(versions[0]["loader"]["version"])
        raise VersionResolutionError(f"No Fabric loader versions found for {mc_version}.")

    def _resolve_installer(self, http_client: HttpClient) -> tuple[str, str]:
        installers = http_client.get_json(f"{FABRIC_META}/installer")
        if not installers:
            raise VersionResolutionError("Fabric returned no installer versions.")
        stable = [entry for entry in installers if entry.get("stable")]
        chosen = stable[0] if stable else installers[0]
        return str(chosen["version"]), str(chosen["url"])

    def install(self, request: InstallRequest, http_client: HttpClient) -> ProviderInstallResult:
        mc_version = self._resolve_mc_version(request=request, http_client=http_client)
        loader_version = self._resolve_loader_version(
            request=request, http_client=http_client, mc_version=mc_version
        )
        installer_version, installer_url = self._resolve_installer(http_client=http_client)

        with tempfile.TemporaryDirectory() as tmp_dir:
            installer_jar = Path(tmp_dir) / "fabric-installer.jar"
            http_client.download(installer_url, installer_jar)
            run_checked(
                [
                    request.java_path,
                    "-jar",
                    str(installer_jar),
                    "server",
                    "-dir",
                    str(request.instance_dir),
                    "-mcversion",
                    mc_version,
                    "-loader",
                    loader_version,
                    "-downloadMinecraft",
                ],
                cwd=request.instance_dir,
            )

        launch_jar = request.instance_dir / "fabric-server-launch.jar"
        if not launch_jar.exists():
            raise InstallError(
                "Fabric install completed but fabric-server-launch.jar was not found."
            )

        manifest = ServerManifest(
            loader=self.loader_id,
            minecraft_version=mc_version,
            loader_version=loader_version,
            build=installer_version,
            java_required=minecraft_java_requirement(http_client, mc_version),
            start=StartCommands(default=["{java}", "-jar", "fabric-server-launch.jar", "nogui"]),
            downloaded_urls=[installer_url],
        )
        notes = ["Fabric installer was used to generate launcher and dependencies."]
        return ProviderInstallResult(
            manifest=manifest,
            server_jar=launch_jar,
            notes=notes,
        )
