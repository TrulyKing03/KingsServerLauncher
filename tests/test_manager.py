from mcserverlib.manager import ServerManager
from mcserverlib.models import ServerManifest, StartCommands


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
            windows=["cmd", "/c", "run.bat"],
        ),
    )
    class _DummyOs:
        name = "nt"

    monkeypatch.setattr("mcserverlib.models.os", _DummyOs)
    command = manager.build_start_command(manifest, java_path="java")
    assert command == ["cmd", "/c", "run.bat"]
