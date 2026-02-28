from __future__ import annotations

import xml.etree.ElementTree as ET

from .http import HttpClient
from .minecraft import MOJANG_MANIFEST_URL
from .providers.fabric import FABRIC_META
from .providers.forge import FORGE_METADATA_URL
from .providers.neoforge import NEOFORGE_METADATA_URL
from .providers.paper_family import PAPER_API_BASE
from .providers.purpur import PURPUR_API
from .providers.quilt import QUILT_META
from .utils import is_stable_version, normalize_loader, version_key


class VersionCatalog:
    """Read-only metadata helper used by the launcher UI."""

    def __init__(self, http_client: HttpClient | None = None) -> None:
        self.http_client = http_client or HttpClient()

    def list_minecraft_versions(
        self, loader: str, stable_only: bool = True, limit: int = 200
    ) -> list[str]:
        loader_id = normalize_loader(loader)
        if loader_id == "vanilla":
            versions = self._vanilla_versions(stable_only=stable_only)
        elif loader_id in {"paper", "folia"}:
            versions = self._paper_family_versions(loader_id)
        elif loader_id == "purpur":
            versions = self._purpur_versions()
        elif loader_id == "fabric":
            versions = self._fabric_versions(stable_only=stable_only)
        elif loader_id == "quilt":
            versions = self._quilt_versions(stable_only=stable_only)
        elif loader_id == "forge":
            versions = self._forge_mc_versions(stable_only=stable_only)
        elif loader_id == "neoforge":
            versions = self._neoforge_mc_versions(stable_only=stable_only)
        else:
            versions = []
        return self._sorted_desc(versions)[:limit]

    def list_loader_versions(
        self, loader: str, minecraft_version: str, stable_only: bool = True, limit: int = 200
    ) -> list[str]:
        loader_id = normalize_loader(loader)
        if loader_id == "fabric":
            versions = self._fabric_loader_versions(
                minecraft_version=minecraft_version,
                stable_only=stable_only,
            )
        elif loader_id == "quilt":
            versions = self._quilt_loader_versions(
                minecraft_version=minecraft_version,
            )
        elif loader_id == "forge":
            versions = self._forge_versions_for_mc(
                minecraft_version=minecraft_version,
                stable_only=stable_only,
            )
        elif loader_id == "neoforge":
            versions = self._neoforge_versions_for_mc(
                minecraft_version=minecraft_version,
                stable_only=stable_only,
            )
        else:
            versions = []
        return self._sorted_desc(versions)[:limit]

    def _sorted_desc(self, values: list[str]) -> list[str]:
        unique = sorted({v for v in values if v}, key=version_key, reverse=True)
        return unique

    def _vanilla_versions(self, stable_only: bool) -> list[str]:
        data = self.http_client.get_json(MOJANG_MANIFEST_URL)
        versions: list[str] = []
        for entry in data.get("versions", []):
            version_id = str(entry.get("id", ""))
            if not version_id:
                continue
            if stable_only and entry.get("type") != "release":
                continue
            versions.append(version_id)
        return versions

    def _paper_family_versions(self, project: str) -> list[str]:
        data = self.http_client.get_json(f"{PAPER_API_BASE}/{project}")
        return [str(v) for v in data.get("versions", [])]

    def _purpur_versions(self) -> list[str]:
        data = self.http_client.get_json(PURPUR_API)
        return [str(v) for v in data.get("versions", [])]

    def _fabric_versions(self, stable_only: bool) -> list[str]:
        entries = self.http_client.get_json(f"{FABRIC_META}/game")
        versions: list[str] = []
        for entry in entries:
            version = str(entry.get("version", ""))
            if not version:
                continue
            if stable_only and not bool(entry.get("stable")):
                continue
            versions.append(version)
        return versions

    def _quilt_versions(self, stable_only: bool) -> list[str]:
        entries = self.http_client.get_json(f"{QUILT_META}/game")
        versions: list[str] = []
        for entry in entries:
            version = str(entry.get("version", ""))
            if not version:
                continue
            if stable_only and not bool(entry.get("stable")):
                continue
            versions.append(version)
        return versions

    def _forge_metadata_versions(self) -> list[str]:
        xml_text = self.http_client.get_text(FORGE_METADATA_URL)
        root = ET.fromstring(xml_text)
        return [
            item.text
            for item in root.findall("./versioning/versions/version")
            if item.text
        ]

    def _neoforge_metadata_versions(self) -> list[str]:
        xml_text = self.http_client.get_text(NEOFORGE_METADATA_URL)
        root = ET.fromstring(xml_text)
        return [
            item.text
            for item in root.findall("./versioning/versions/version")
            if item.text
        ]

    def _forge_mc_versions(self, stable_only: bool) -> list[str]:
        versions = self._forge_metadata_versions()
        mc_versions: list[str] = []
        for version in versions:
            if stable_only and not is_stable_version(version):
                continue
            if "-" not in version:
                continue
            mc_versions.append(version.split("-", 1)[0])
        return mc_versions

    def _neoforge_mc_versions(self, stable_only: bool) -> list[str]:
        versions = self._neoforge_metadata_versions()
        mc_versions: list[str] = []
        for version in versions:
            if stable_only and not is_stable_version(version):
                continue
            mapped = self._map_neoforge_to_mc(version)
            if mapped:
                mc_versions.append(mapped)
        return mc_versions

    def _fabric_loader_versions(self, minecraft_version: str, stable_only: bool) -> list[str]:
        entries = self.http_client.get_json(f"{FABRIC_META}/loader/{minecraft_version}")
        versions: list[str] = []
        for entry in entries:
            loader = entry.get("loader") or {}
            version = str(loader.get("version", ""))
            if not version:
                continue
            if stable_only and not bool(loader.get("stable")):
                continue
            versions.append(version)
        return versions

    def _quilt_loader_versions(self, minecraft_version: str) -> list[str]:
        entries = self.http_client.get_json(f"{QUILT_META}/loader/{minecraft_version}")
        versions: list[str] = []
        for entry in entries:
            loader = entry.get("loader") or {}
            version = str(loader.get("version", ""))
            if version:
                versions.append(version)
        return versions

    def _forge_versions_for_mc(self, minecraft_version: str, stable_only: bool) -> list[str]:
        prefix = f"{minecraft_version}-"
        versions = self._forge_metadata_versions()
        matches = [v for v in versions if v.startswith(prefix)]
        if stable_only:
            matches = [v for v in matches if is_stable_version(v)]
        return matches

    def _neoforge_versions_for_mc(self, minecraft_version: str, stable_only: bool) -> list[str]:
        versions = self._neoforge_metadata_versions()
        matches: list[str] = []
        for version in versions:
            if stable_only and not is_stable_version(version):
                continue
            mapped = self._map_neoforge_to_mc(version)
            if mapped == minecraft_version:
                matches.append(version)
        return matches

    def _map_neoforge_to_mc(self, neoforge_version: str) -> str | None:
        parts = neoforge_version.split(".")
        if len(parts) < 2:
            return None
        major = parts[0]
        minor = parts[1]
        if not major.isdigit() or not minor.isdigit():
            return None
        return f"1.{major}.{minor}"
