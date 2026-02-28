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

NEOFORGE_METADATA_URL = (
    "https://maven.neoforged.net/releases/net/neoforged/neoforge/maven-metadata.xml"
)


class NeoForgeProvider(LoaderProvider):
    loader_id = "neoforge"

    def _all_versions(self, http_client: HttpClient) -> list[str]:
        xml_text = http_client.get_text(NEOFORGE_METADATA_URL)
        root = ET.fromstring(xml_text)
        versions = [
            item.text
            for item in root.findall("./versioning/versions/version")
            if item.text
        ]
        if not versions:
            raise VersionResolutionError("NeoForge metadata returned no versions.")
        return versions

    def _resolve_neoforge_version(self, request: InstallRequest, versions: list[str]) -> str:
        if request.loader_version:
            if request.loader_version not in versions:
                raise VersionResolutionError(
                    f"NeoForge version {request.loader_version} was not found."
                )
            return request.loader_version

        stable_versions = [v for v in versions if is_stable_version(v)]
        if request.minecraft_version == "latest":
            pool = stable_versions or versions
            return pick_latest_version(pool, stable_only=False)

        mc = request.minecraft_version
        if mc.startswith("1."):
            mc = mc[2:]
        prefix = f"{mc}."
        matching = [v for v in versions if v.startswith(prefix) or v == mc]
        if not matching:
            raise VersionResolutionError(
                f"No NeoForge versions found for Minecraft {request.minecraft_version}."
            )
        stable_matching = [v for v in matching if is_stable_version(v)]
        return pick_latest_version(stable_matching or matching, stable_only=False)

    def _guess_mc_version(self, request: InstallRequest, neoforge_version: str) -> str | None:
        if request.minecraft_version != "latest":
            return request.minecraft_version
        parts = neoforge_version.split(".")
        if len(parts) >= 2 and parts[0].isdigit() and parts[1].isdigit():
            return f"1.{parts[0]}.{parts[1]}"
        return None

    def install(self, request: InstallRequest, http_client: HttpClient) -> ProviderInstallResult:
        versions = self._all_versions(http_client=http_client)
        neoforge_version = self._resolve_neoforge_version(
            request=request,
            versions=versions,
        )

        installer_url = (
            "https://maven.neoforged.net/releases/net/neoforged/neoforge/"
            f"{neoforge_version}/neoforge-{neoforge_version}-installer.jar"
        )
        with tempfile.TemporaryDirectory() as tmp_dir:
            installer_jar = Path(tmp_dir) / "neoforge-installer.jar"
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
            raise InstallError("NeoForge install completed but run scripts were not found.")

        java_required = None
        guessed_mc = self._guess_mc_version(request=request, neoforge_version=neoforge_version)
        if guessed_mc:
            try:
                java_required = minecraft_java_requirement(http_client, guessed_mc)
            except Exception:
                java_required = None

        manifest = ServerManifest(
            loader=self.loader_id,
            minecraft_version=guessed_mc or request.minecraft_version,
            loader_version=neoforge_version,
            java_required=java_required,
            start=StartCommands(
                default=[
                    "{java}",
                    "@user_jvm_args.txt",
                    f"@libraries/net/neoforged/neoforge/{neoforge_version}/unix_args.txt",
                    "nogui",
                ],
                windows=[
                    "{java}",
                    "@user_jvm_args.txt",
                    f"@libraries/net/neoforged/neoforge/{neoforge_version}/win_args.txt",
                    "nogui",
                ],
                posix=[
                    "{java}",
                    "@user_jvm_args.txt",
                    f"@libraries/net/neoforged/neoforge/{neoforge_version}/unix_args.txt",
                    "nogui",
                ],
            ),
            downloaded_urls=[installer_url],
        )
        notes = [
            "NeoForge installer artifacts installed. Startup uses Java argfiles directly (not run.bat).",
        ]
        return ProviderInstallResult(
            manifest=manifest,
            server_jar=None,
            notes=notes,
        )
