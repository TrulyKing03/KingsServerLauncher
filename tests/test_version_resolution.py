from mcserverlib.providers.forge import ForgeProvider
from mcserverlib.providers.neoforge import NeoForgeProvider
from mcserverlib.providers.paper_family import PaperProvider


def test_forge_version_resolution_by_mc_version():
    provider = ForgeProvider()
    versions = ["1.21.1-52.0.1", "1.21.1-52.0.2", "1.21.2-53.0.1"]

    class _Req:
        loader_version = None
        minecraft_version = "1.21.1"

    resolved = provider._resolve_forge_version(_Req(), versions, release_version=None)
    assert resolved == "1.21.1-52.0.2"


def test_neoforge_prefers_stable():
    provider = NeoForgeProvider()
    versions = ["21.11.30-beta", "21.1.218", "21.1.219", "26.1.0.0-alpha.12+snapshot-7"]

    class _Req:
        loader_version = None
        minecraft_version = "latest"

    resolved = provider._resolve_neoforge_version(_Req(), versions)
    assert resolved == "21.1.219"


def test_paper_build_selection_prefers_default_channel():
    provider = PaperProvider()
    builds = [
        {"build": 10, "channel": "experimental"},
        {"build": 12, "channel": "default"},
        {"build": 11, "channel": "default"},
    ]

    class _Req:
        build = None

    selected = provider._resolve_build("1.21.11", _Req(), _FakeHttp(builds))
    assert selected["build"] == 12


class _FakeHttp:
    def __init__(self, builds):
        self.builds = builds

    def get_json(self, url):
        return {"builds": self.builds}
