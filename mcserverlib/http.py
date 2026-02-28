from __future__ import annotations

from pathlib import Path
from typing import Any
import json
import tempfile
import urllib.error
import urllib.request

from .exceptions import DownloadError
from .utils import hash_file


class HttpClient:
    def __init__(self, timeout_seconds: int = 30) -> None:
        self.timeout_seconds = timeout_seconds
        self.user_agent = "mcserverlib/0.1 (+https://github.com/)"

    def _request(self, url: str) -> urllib.request.Request:
        return urllib.request.Request(url, headers={"User-Agent": self.user_agent})

    def get_json(self, url: str) -> Any:
        try:
            with urllib.request.urlopen(
                self._request(url), timeout=self.timeout_seconds
            ) as response:
                payload = response.read().decode("utf-8")
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
                return response.read().decode("utf-8")
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
                while True:
                    chunk = response.read(1024 * 1024)
                    if not chunk:
                        break
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
