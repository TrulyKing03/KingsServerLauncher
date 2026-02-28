from __future__ import annotations

from pathlib import Path
import tempfile

from ..exceptions import InstallError, VersionResolutionError
from ..http import HttpClient
from ..minecraft import minecraft_java_requirement
from ..models import InstallRequest, ServerManifest, StartCommands
from ..subprocess_utils import run_checked
from .base import LoaderProvider, ProviderInstallResult

QUILT_META = "https://meta.quiltmc.org/v3/versions"


class QuiltProvider(LoaderProvider):
    loader_id = "quilt"

    def _resolve_mc_version(self, request: InstallRequest, http_client: HttpClient) -> str:
        versions = http_client.get_json(f"{QUILT_META}/game")
        stable = [v["version"] for v in versions if v.get("stable")]
        if request.minecraft_version == "latest":
            if not stable:
                raise VersionResolutionError("Quilt returned no stable game versions.")
            return str(stable[0])
        valid = {v["version"] for v in versions}
        if request.minecraft_version not in valid:
            raise VersionResolutionError(
                f"Quilt does not publish Minecraft version {request.minecraft_version}."
            )
        return request.minecraft_version

    def _resolve_loader_version(
        self, request: InstallRequest, http_client: HttpClient, mc_version: str
    ) -> str:
        versions = http_client.get_json(f"{QUILT_META}/loader/{mc_version}")
        if request.loader_version:
            for item in versions:
                loader = item.get("loader") or {}
                if loader.get("version") == request.loader_version:
                    return request.loader_version
            raise VersionResolutionError(
                f"Quilt loader version {request.loader_version} not found for {mc_version}."
            )
        if not versions:
            raise VersionResolutionError(f"No Quilt loader versions found for {mc_version}.")
        return str(versions[0]["loader"]["version"])

    def _resolve_installer(self, http_client: HttpClient) -> tuple[str, str]:
        installers = http_client.get_json(f"{QUILT_META}/installer")
        if not installers:
            raise VersionResolutionError("Quilt returned no installer versions.")
        latest = installers[0]
        return str(latest["version"]), str(latest["url"])

    def install(self, request: InstallRequest, http_client: HttpClient) -> ProviderInstallResult:
        mc_version = self._resolve_mc_version(request=request, http_client=http_client)
        loader_version = self._resolve_loader_version(
            request=request,
            http_client=http_client,
            mc_version=mc_version,
        )
        installer_version, installer_url = self._resolve_installer(http_client=http_client)

        with tempfile.TemporaryDirectory() as tmp_dir:
            installer_jar = Path(tmp_dir) / "quilt-installer.jar"
            http_client.download(installer_url, installer_jar)
            run_checked(
                [
                    request.java_path,
                    "-jar",
                    str(installer_jar),
                    "install",
                    "server",
                    mc_version,
                    loader_version,
                    f"--install-dir={request.instance_dir}",
                    "--download-server",
                ],
                cwd=request.instance_dir,
            )

        launch_jar = request.instance_dir / "quilt-server-launch.jar"
        if not launch_jar.exists():
            raise InstallError(
                "Quilt install completed but quilt-server-launch.jar was not found."
            )

        manifest = ServerManifest(
            loader=self.loader_id,
            minecraft_version=mc_version,
            loader_version=loader_version,
            build=installer_version,
            java_required=minecraft_java_requirement(http_client, mc_version),
            start=StartCommands(default=["{java}", "-jar", "quilt-server-launch.jar", "nogui"]),
            downloaded_urls=[installer_url],
        )
        notes = ["Quilt installer was used to generate launcher and dependencies."]
        return ProviderInstallResult(
            manifest=manifest,
            server_jar=launch_jar,
            notes=notes,
        )
