from __future__ import annotations

from pathlib import Path
import tempfile
import xml.etree.ElementTree as ET

from ..exceptions import InstallError, VersionResolutionError
from ..http import HttpClient
from ..minecraft import minecraft_java_requirement
from ..models import InstallRequest, ServerManifest, StartCommands
from ..subprocess_utils import run_checked
from ..utils import is_stable_version, pick_latest_version
from .base import LoaderProvider, ProviderInstallResult

FORGE_METADATA_URL = (
    "https://maven.minecraftforge.net/net/minecraftforge/forge/maven-metadata.xml"
)


class ForgeProvider(LoaderProvider):
    loader_id = "forge"

    def _metadata(self, http_client: HttpClient) -> tuple[list[str], str | None]:
        xml_text = http_client.get_text(FORGE_METADATA_URL)
        root = ET.fromstring(xml_text)
        versions = [
            item.text
            for item in root.findall("./versioning/versions/version")
            if item.text
        ]
        if not versions:
            raise VersionResolutionError("Forge metadata returned no versions.")
        release = root.findtext("./versioning/release")
        return versions, release

    def _resolve_forge_version(
        self,
        request: InstallRequest,
        versions: list[str],
        release_version: str | None,
    ) -> str:
        if request.loader_version:
            if request.loader_version not in versions:
                raise VersionResolutionError(
                    f"Forge version {request.loader_version} was not found."
                )
            return request.loader_version

        if request.minecraft_version == "latest":
            if release_version and is_stable_version(release_version):
                return release_version
            stable = [v for v in versions if is_stable_version(v)]
            return pick_latest_version(stable, stable_only=False)

        prefix = f"{request.minecraft_version}-"
        candidates = [v for v in versions if v.startswith(prefix)]
        if not candidates:
            raise VersionResolutionError(
                f"No Forge versions found for Minecraft {request.minecraft_version}."
            )
        stable = [v for v in candidates if is_stable_version(v)]
        return pick_latest_version(stable or candidates, stable_only=False)

    def install(self, request: InstallRequest, http_client: HttpClient) -> ProviderInstallResult:
        versions, release_version = self._metadata(http_client=http_client)
        forge_version = self._resolve_forge_version(
            request=request,
            versions=versions,
            release_version=release_version,
        )

        installer_url = (
            "https://maven.minecraftforge.net/net/minecraftforge/forge/"
            f"{forge_version}/forge-{forge_version}-installer.jar"
        )
        with tempfile.TemporaryDirectory() as tmp_dir:
            installer_jar = Path(tmp_dir) / "forge-installer.jar"
            http_client.download(installer_url, installer_jar)
            run_checked(
                [
                    request.java_path,
                    "-jar",
                    str(installer_jar),
                    "--installServer",
                    str(request.instance_dir),
                ],
                cwd=request.instance_dir,
            )

        run_bat = request.instance_dir / "run.bat"
        run_sh = request.instance_dir / "run.sh"
        if not run_bat.exists() and not run_sh.exists():
            raise InstallError("Forge install completed but run scripts were not found.")

        minecraft_version = forge_version.split("-", 1)[0]
        java_required = None
        try:
            java_required = minecraft_java_requirement(http_client, minecraft_version)
        except Exception:
            java_required = None

        manifest = ServerManifest(
            loader=self.loader_id,
            minecraft_version=minecraft_version,
            loader_version=forge_version,
            java_required=java_required,
            start=StartCommands(
                default=[
                    "{java}",
                    "@user_jvm_args.txt",
                    f"@libraries/net/minecraftforge/forge/{forge_version}/unix_args.txt",
                    "nogui",
                ],
                windows=[
                    "{java}",
                    "@user_jvm_args.txt",
                    f"@libraries/net/minecraftforge/forge/{forge_version}/win_args.txt",
                    "nogui",
                ],
                posix=[
                    "{java}",
                    "@user_jvm_args.txt",
                    f"@libraries/net/minecraftforge/forge/{forge_version}/unix_args.txt",
                    "nogui",
                ],
            ),
            downloaded_urls=[installer_url],
        )
        notes = [
            "Forge installer artifacts installed. Startup uses Java argfiles directly (not run.bat).",
        ]
        return ProviderInstallResult(
            manifest=manifest,
            server_jar=None,
            notes=notes,
        )
