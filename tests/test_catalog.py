from mcserverlib.catalog import VersionCatalog


class _FakeHttp:
    def __init__(self, json_map=None, text_map=None):
        self.json_map = json_map or {}
        self.text_map = text_map or {}

    def get_json(self, url):
        return self.json_map[url]

    def get_text(self, url):
        return self.text_map[url]


def test_vanilla_versions_filter_release():
    url = "https://piston-meta.mojang.com/mc/game/version_manifest_v2.json"
    http = _FakeHttp(
        json_map={
            url: {
                "versions": [
                    {"id": "1.21.11", "type": "release"},
                    {"id": "26w10a", "type": "snapshot"},
                ]
            }
        }
    )
    catalog = VersionCatalog(http_client=http)
    versions = catalog.list_minecraft_versions("vanilla", stable_only=True)
    assert versions == ["1.21.11"]


def test_forge_mc_version_extraction():
    metadata_url = (
        "https://maven.minecraftforge.net/net/minecraftforge/forge/maven-metadata.xml"
    )
    xml = """\
<metadata>
  <versioning>
    <versions>
      <version>1.21.11-61.1.1</version>
      <version>1.21.10-60.0.1</version>
    </versions>
  </versioning>
</metadata>
"""
    catalog = VersionCatalog(http_client=_FakeHttp(text_map={metadata_url: xml}))
    versions = catalog.list_minecraft_versions("forge")
    assert versions[0] == "1.21.11"
    assert "1.21.10" in versions


def test_neoforge_mc_version_mapping():
    metadata_url = (
        "https://maven.neoforged.net/releases/net/neoforged/neoforge/maven-metadata.xml"
    )
    xml = """\
<metadata>
  <versioning>
    <versions>
      <version>21.11.38-beta</version>
      <version>21.10.64</version>
      <version>21.1.219</version>
    </versions>
  </versioning>
</metadata>
"""
    catalog = VersionCatalog(http_client=_FakeHttp(text_map={metadata_url: xml}))
    versions = catalog.list_minecraft_versions("neoforge")
    assert versions[0] == "1.21.10"
    assert "1.21.1" in versions
    assert "1.21.11" not in versions
