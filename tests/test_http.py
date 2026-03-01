import io

import pytest

from mcserverlib.exceptions import DownloadError
from mcserverlib.http import HttpClient


class _FakeResponse:
    def __init__(self, payload: bytes, headers: dict[str, str] | None = None) -> None:
        self._stream = io.BytesIO(payload)
        self.headers = headers or {}

    def read(self, size: int = -1) -> bytes:
        return self._stream.read(size)

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc, tb) -> bool:
        return False


def test_http_client_blocks_non_https_urls():
    client = HttpClient()
    with pytest.raises(DownloadError):
        client.get_text("http://example.com/test.txt")


def test_http_client_blocks_private_ip_hosts():
    client = HttpClient()
    with pytest.raises(DownloadError):
        client.get_text("https://127.0.0.1/internal")


def test_http_client_limits_text_response_size(monkeypatch):
    client = HttpClient(max_text_response_bytes=5)

    def _fake_open(request, timeout=0):
        return _FakeResponse(b"too-large-response")

    monkeypatch.setattr("urllib.request.urlopen", _fake_open)
    with pytest.raises(DownloadError):
        client.get_text("https://example.com/test.txt")

