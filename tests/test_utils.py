from mcserverlib.models import ServerManifest, StartCommands
from mcserverlib.utils import pick_latest_version


def test_pick_latest_version_prefers_stable_values():
    values = ["1.21.10", "1.21.11-rc1", "1.21.11"]
    assert pick_latest_version(values, stable_only=True) == "1.21.11"


def test_manifest_round_trip():
    manifest = ServerManifest(
        loader="paper",
        minecraft_version="1.21.11",
        loader_version="x",
        build="7",
        java_required=21,
        start=StartCommands(default=["{java}", "-jar", "server.jar", "nogui"]),
        downloaded_urls=["https://example.invalid/server.jar"],
    )
    payload = manifest.to_dict()
    loaded = ServerManifest.from_dict(payload)
    assert loaded.loader == "paper"
    assert loaded.minecraft_version == "1.21.11"
    assert loaded.loader_version == "x"
    assert loaded.build == "7"
    assert loaded.start.default == ["{java}", "-jar", "server.jar", "nogui"]
