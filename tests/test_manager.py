import pytest

from mcserverlib.exceptions import ManifestError
from mcserverlib.manager import ServerManager
from mcserverlib.models import InstallRequest, ServerManifest, StartCommands
from mcserverlib.providers.base import ProviderInstallResult
from mcserverlib.utils import parse_properties_file


class _DummyProvider:
    def __init__(self, loader_id: str) -> None:
        self.loader_id = loader_id

    def install(self, request, http_client) -> ProviderInstallResult:  # noqa: ANN001
        manifest = ServerManifest(
            loader=self.loader_id,
            minecraft_version="1.21.11",
            start=StartCommands(default=["{java}", "-jar", "server.jar", "nogui"]),
        )
        return ProviderInstallResult(manifest=manifest)


def test_build_start_command_injects_memory_and_jvm_args():
    manager = ServerManager()
    manifest = ServerManifest(
        loader="vanilla",
        minecraft_version="1.21.11",
        java_required=21,
        start=StartCommands(default=["{java}", "-jar", "server.jar", "nogui"]),
    )
    command = manager.build_start_command(
        manifest=manifest,
        java_path="C:/java/bin/java.exe",
        xms="2G",
        xmx="4G",
        jvm_args=["-Dcom.mojang.eula.agree=true"],
    )
    assert command == [
        "C:/java/bin/java.exe",
        "-Xms2G",
        "-Xmx4G",
        "-Dcom.mojang.eula.agree=true",
        "-jar",
        "server.jar",
        "nogui",
    ]


def test_build_start_command_uses_platform_override(monkeypatch):
    manager = ServerManager()
    manifest = ServerManifest(
        loader="forge",
        minecraft_version="1.21.11",
        start=StartCommands(
            default=["{java}", "-jar", "server.jar", "nogui"],
            windows=["{java}", "@user_jvm_args.txt", "@libraries/forge/win_args.txt", "nogui"],
        ),
    )
    class _DummyOs:
        name = "nt"

    monkeypatch.setattr("mcserverlib.models.os", _DummyOs)
    command = manager.build_start_command(manifest, java_path="java")
    assert command == ["java", "@user_jvm_args.txt", "@libraries/forge/win_args.txt", "nogui"]


def test_build_start_command_rejects_non_java_entrypoint():
    manager = ServerManager()
    manifest = ServerManifest(
        loader="forge",
        minecraft_version="1.21.11",
        start=StartCommands(default=["cmd", "/c", "run.bat"]),
    )
    with pytest.raises(ManifestError):
        manager.build_start_command(manifest, java_path="java")


def test_resolve_under_instance_dir_blocks_traversal(tmp_path):
    manager = ServerManager()
    with pytest.raises(ManifestError):
        manager._resolve_under_instance_dir("../outside.jar", tmp_path)


def test_install_writes_whitelist_enabled_by_default(tmp_path):
    manager = ServerManager()
    manager._providers["paper"] = _DummyProvider("paper")
    request = InstallRequest(
        loader="paper",
        instance_dir=tmp_path,
        accept_eula=True,
    )

    manager.install(request)
    properties = parse_properties_file(tmp_path / "server.properties")

    assert properties.get("whitelist") == "true"


def test_install_preserves_existing_saved_whitelist(tmp_path):
    manager = ServerManager()
    manager._providers["paper"] = _DummyProvider("paper")
    (tmp_path / "server.properties").write_text(
        "whitelist=false\nmotd=Private world\n",
        encoding="utf-8",
    )
    request = InstallRequest(
        loader="paper",
        instance_dir=tmp_path,
        accept_eula=True,
    )

    manager.install(request)
    properties = parse_properties_file(tmp_path / "server.properties")

    assert properties.get("whitelist") == "false"
    assert properties.get("motd") == "Private world"
