from __future__ import annotations

from pathlib import Path
from typing import Any
import ipaddress
import json
import tempfile
import urllib.error
import urllib.parse
import urllib.request

from .exceptions import DownloadError
from .utils import hash_file


MAX_TEXT_RESPONSE_BYTES = 16 * 1024 * 1024
MAX_DOWNLOAD_BYTES = 512 * 1024 * 1024


class HttpClient:
    def __init__(
        self,
        timeout_seconds: int = 30,
        max_text_response_bytes: int = MAX_TEXT_RESPONSE_BYTES,
        max_download_bytes: int = MAX_DOWNLOAD_BYTES,
    ) -> None:
        self.timeout_seconds = timeout_seconds
        self.max_text_response_bytes = max_text_response_bytes
        self.max_download_bytes = max_download_bytes
        self.user_agent = "mcserverlib/0.1 (+https://github.com/)"

    def _request(self, url: str) -> urllib.request.Request:
        self._validate_url(url)
        return urllib.request.Request(url, headers={"User-Agent": self.user_agent})

    def get_json(self, url: str) -> Any:
        try:
            with urllib.request.urlopen(
                self._request(url), timeout=self.timeout_seconds
            ) as response:
                payload = self._read_limited(
                    response,
                    max_bytes=self.max_text_response_bytes,
                    url=url,
                ).decode("utf-8")
        except urllib.error.URLError as exc:
            raise DownloadError(f"Request failed for {url}: {exc}") from exc
        try:
            return json.loads(payload)
        except json.JSONDecodeError as exc:
            raise DownloadError(f"Invalid JSON from {url}") from exc

    def get_text(self, url: str) -> str:
        try:
            with urllib.request.urlopen(
                self._request(url), timeout=self.timeout_seconds
            ) as response:
                return self._read_limited(
                    response,
                    max_bytes=self.max_text_response_bytes,
                    url=url,
                ).decode("utf-8")
        except urllib.error.URLError as exc:
            raise DownloadError(f"Request failed for {url}: {exc}") from exc

    def download(
        self,
        url: str,
        destination: Path,
        expected_hash: str | None = None,
        hash_algorithm: str = "sha1",
    ) -> Path:
        destination.parent.mkdir(parents=True, exist_ok=True)
        tmp_path: Path | None = None
        try:
            with urllib.request.urlopen(
                self._request(url), timeout=self.timeout_seconds
            ) as response, tempfile.NamedTemporaryFile(
                "wb", delete=False, dir=str(destination.parent)
            ) as tmp:
                tmp_path = Path(tmp.name)
                content_length = response.headers.get("Content-Length")
                if content_length:
                    try:
                        declared_size = int(content_length)
                    except ValueError:
                        declared_size = 0
                    if declared_size > self.max_download_bytes:
                        raise DownloadError(
                            f"Download for {destination.name} exceeds the size limit."
                        )
                received_bytes = 0
                while True:
                    chunk = response.read(1024 * 1024)
                    if not chunk:
                        break
                    received_bytes += len(chunk)
                    if received_bytes > self.max_download_bytes:
                        raise DownloadError(
                            f"Download for {destination.name} exceeded the allowed size limit."
                        )
                    tmp.write(chunk)
            if expected_hash:
                actual = hash_file(tmp_path, hash_algorithm)
                if actual.lower() != expected_hash.lower():
                    raise DownloadError(
                        f"Hash mismatch for {destination.name}. "
                        f"Expected {expected_hash} ({hash_algorithm}), got {actual}."
                    )
            tmp_path.replace(destination)
        except urllib.error.URLError as exc:
            raise DownloadError(f"Download failed for {url}: {exc}") from exc
        finally:
            if tmp_path and tmp_path.exists():
                try:
                    tmp_path.unlink()
                except OSError:
                    pass
        return destination

    @staticmethod
    def _validate_url(url: str) -> None:
        parsed = urllib.parse.urlparse(url)
        if parsed.scheme.lower() != "https":
            raise DownloadError(f"Blocked URL with unsupported scheme: {url}")
        host = parsed.hostname
        if not host:
            raise DownloadError(f"Blocked URL with missing host: {url}")
        try:
            ip = ipaddress.ip_address(host)
        except ValueError:
            return
        if (
            ip.is_private
            or ip.is_loopback
            or ip.is_link_local
            or ip.is_multicast
            or ip.is_reserved
        ):
            raise DownloadError(f"Blocked URL targeting disallowed address: {url}")

    @staticmethod
    def _read_limited(response, max_bytes: int, url: str) -> bytes:
        chunks: list[bytes] = []
        received = 0
        while True:
            chunk = response.read(1024 * 1024)
            if not chunk:
                break
            received += len(chunk)
            if received > max_bytes:
                raise DownloadError(
                    f"Response from {url} exceeded the allowed size limit."
                )
            chunks.append(chunk)
        return b"".join(chunks)
