from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass
from pathlib import Path

from ..http import HttpClient
from ..models import InstallRequest, ServerManifest


@dataclass(slots=True)
class ProviderInstallResult:
    manifest: ServerManifest
    server_jar: Path | None = None
    notes: list[str] | None = None


class LoaderProvider(ABC):
    loader_id: str

    @abstractmethod
    def install(self, request: InstallRequest, http_client: HttpClient) -> ProviderInstallResult:
        raise NotImplementedError
