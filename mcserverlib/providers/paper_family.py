from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from ..exceptions import VersionResolutionError
from ..http import HttpClient
from ..minecraft import minecraft_java_requirement
from ..models import InstallRequest, ServerManifest, StartCommands
from ..utils import pick_latest_version
from .base import LoaderProvider, ProviderInstallResult

PAPER_API_BASE = "https://api.papermc.io/v2/projects"


@dataclass(slots=True)
class PaperFamilyProvider(LoaderProvider):
    loader_id: str
    project: str

    def _resolve_mc_version(self, request: InstallRequest, http_client: HttpClient) -> str:
        data = http_client.get_json(f"{PAPER_API_BASE}/{self.project}")
        versions = [str(v) for v in data.get("versions", [])]
        if not versions:
            raise VersionResolutionError(f"No {self.project} versions were returned by API.")
        if request.minecraft_version == "latest":
            return pick_latest_version(versions, stable_only=True)
        if request.minecraft_version not in versions:
            raise VersionResolutionError(
                f"{self.project} does not have Minecraft version {request.minecraft_version}."
            )
        return request.minecraft_version

    def _resolve_build(
        self, mc_version: str, request: InstallRequest, http_client: HttpClient
    ) -> dict:
        builds_data = http_client.get_json(
            f"{PAPER_API_BASE}/{self.project}/versions/{mc_version}/builds"
        )
        builds = list(builds_data.get("builds", []))
        if not builds:
            raise VersionResolutionError(
                f"No builds found for {self.project} {mc_version}."
            )

        if request.build is not None:
            build_str = str(request.build)
            for build in builds:
                if str(build.get("build")) == build_str:
                    return build
            raise VersionResolutionError(
                f"{self.project} build {build_str} not found for {mc_version}."
            )

        default_builds = [b for b in builds if b.get("channel") == "default"]
        chosen = max(default_builds or builds, key=lambda b: int(b["build"]))
        return chosen

    def install(self, request: InstallRequest, http_client: HttpClient) -> ProviderInstallResult:
        mc_version = self._resolve_mc_version(request=request, http_client=http_client)
        build = self._resolve_build(
            mc_version=mc_version, request=request, http_client=http_client
        )
        build_no = str(build["build"])

        app = build.get("downloads", {}).get("application") or {}
        artifact_name = app.get("name")
        if not artifact_name:
            raise RuntimeError(f"{self.project} build metadata did not include application name.")

        download_url = (
            f"{PAPER_API_BASE}/{self.project}/versions/{mc_version}/builds/"
            f"{build_no}/downloads/{artifact_name}"
        )
        server_jar = request.instance_dir / "server.jar"
        http_client.download(
            url=download_url,
            destination=server_jar,
            expected_hash=app.get("sha256"),
            hash_algorithm="sha256",
        )

        manifest = ServerManifest(
            loader=self.loader_id,
            minecraft_version=mc_version,
            build=build_no,
            java_required=minecraft_java_requirement(http_client, mc_version),
            start=StartCommands(default=["{java}", "-jar", "server.jar", "nogui"]),
            downloaded_urls=[download_url],
        )
        return ProviderInstallResult(manifest=manifest, server_jar=Path(server_jar))


class PaperProvider(PaperFamilyProvider):
    def __init__(self) -> None:
        super().__init__(loader_id="paper", project="paper")


class FoliaProvider(PaperFamilyProvider):
    def __init__(self) -> None:
        super().__init__(loader_id="folia", project="folia")
