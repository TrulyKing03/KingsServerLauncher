from __future__ import annotations

from pathlib import Path
from typing import Iterable

from .http import HttpClient
from .models import InstallRequest, InstallResult, ServerManifest
from .process import LogHandler, ServerProcess
from .providers import create_provider_registry
from .utils import (
    normalize_loader,
    load_manifest,
    save_manifest,
    write_eula,
    write_server_properties,
)


class ServerManager:
    def __init__(self, http_client: HttpClient | None = None) -> None:
        self.http_client = http_client or HttpClient()
        self._providers = create_provider_registry()

    @property
    def supported_loaders(self) -> tuple[str, ...]:
        return tuple(sorted(self._providers.keys()))

    def install(self, request: InstallRequest) -> InstallResult:
        loader_id = normalize_loader(request.loader)
        provider = self._providers[loader_id]
        request.loader = loader_id
        request.instance_dir = Path(request.instance_dir).resolve()
        request.instance_dir.mkdir(parents=True, exist_ok=True)

        provider_result = provider.install(request=request, http_client=self.http_client)

        write_eula(request.instance_dir, accepted=request.accept_eula)
        if request.server_properties:
            write_server_properties(
                instance_dir=request.instance_dir,
                properties=dict(request.server_properties),
            )

        manifest_path = save_manifest(
            instance_dir=request.instance_dir,
            manifest=provider_result.manifest,
        )
        return InstallResult(
            instance_dir=request.instance_dir,
            manifest_path=manifest_path,
            manifest=provider_result.manifest,
            server_jar=provider_result.server_jar,
            notes=provider_result.notes or [],
        )

    def load_manifest(self, instance_dir: str | Path) -> ServerManifest:
        return load_manifest(Path(instance_dir))

    def build_start_command(
        self,
        manifest: ServerManifest,
        java_path: str = "java",
        xms: str | None = None,
        xmx: str | None = None,
        jvm_args: Iterable[str] | None = None,
    ) -> list[str]:
        raw_command = manifest.start.for_platform()
        command = [java_path if token == "{java}" else token for token in raw_command]
        if "{java}" in raw_command and command:
            insert_at = command.index(java_path) + 1
            extra: list[str] = []
            if xms:
                extra.append(f"-Xms{xms}")
            if xmx:
                extra.append(f"-Xmx{xmx}")
            if jvm_args:
                extra.extend(list(jvm_args))
            if extra:
                command[insert_at:insert_at] = extra
        return command

    def start(
        self,
        instance_dir: str | Path,
        java_path: str = "java",
        xms: str | None = None,
        xmx: str | None = None,
        jvm_args: Iterable[str] | None = None,
        log_handler: LogHandler | None = None,
        env: dict[str, str] | None = None,
    ) -> ServerProcess:
        instance = Path(instance_dir).resolve()
        manifest = load_manifest(instance)
        command = self.build_start_command(
            manifest=manifest,
            java_path=java_path,
            xms=xms,
            xmx=xmx,
            jvm_args=jvm_args,
        )
        return ServerProcess.start(
            command=command,
            cwd=instance,
            log_handler=log_handler,
            env=env,
        )
