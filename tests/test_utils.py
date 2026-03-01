from mcserverlib.models import ServerManifest, StartCommands
from mcserverlib.utils import parse_properties_file, pick_latest_version, read_server_endpoint


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


def test_parse_properties_file_ignores_comments_and_blank_lines(tmp_path):
    props_path = tmp_path / "server.properties"
    props_path.write_text(
        "# comment\n"
        "server-ip=play.example.com\n"
        "server-port=25570\n"
        "\n"
        "! ignored comment\n"
        "motd=Hello world\n",
        encoding="utf-8",
    )

    props = parse_properties_file(props_path)

    assert props["server-ip"] == "play.example.com"
    assert props["server-port"] == "25570"
    assert props["motd"] == "Hello world"


def test_read_server_endpoint_defaults_when_missing_or_invalid_port(tmp_path):
    assert read_server_endpoint(tmp_path) == ("", 25565)

    props_path = tmp_path / "server.properties"
    props_path.write_text("server-ip=mc.example.com\nserver-port=abc\n", encoding="utf-8")
    assert read_server_endpoint(tmp_path) == ("mc.example.com", 25565)
