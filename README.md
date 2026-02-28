# mcserverinitalsetupall

`mcserverlib` is a Python library and CLI for provisioning and running Minecraft servers across major server stacks from a single interface.

It handles:

- version resolution (`latest` or pinned versions)
- artifact download and checksum verification
- installer execution for loader families that require it
- server bootstrap files (`eula.txt`, `server.properties`)
- process lifecycle (start, send commands, graceful stop)

## Supported Loaders

Current providers:

- `vanilla` (Mojang official server)
- `paper`
- `purpur`
- `folia`
- `fabric`
- `quilt`
- `forge`
- `neoforge`

The library targets stable versions by default when `--minecraft-version latest` is used. You can always pin exact versions/builds.

## Requirements

- Python `>= 3.10`
- Java installed and reachable (default command: `java`)
- Internet access for metadata and artifact downloads

## Install

From this repository:

```bash
python -m pip install -e .[dev]
```

If `python` is not on your PATH, use your full interpreter path instead.

## Quick Start (CLI)

List loaders:

```bash
python -m mcserverlib.cli loaders
```

Install a Paper server:

```bash
python -m mcserverlib.cli install \
  --loader paper \
  --dir ./servers/paper-main \
  --minecraft-version latest \
  --accept-eula
```

Start it:

```bash
python -m mcserverlib.cli start \
  --dir ./servers/paper-main \
  --xms 2G \
  --xmx 4G
```

Inspect install metadata:

```bash
python -m mcserverlib.cli manifest --dir ./servers/paper-main
```

## Quick Start (Python API)

```python
from pathlib import Path
from mcserverlib import InstallRequest, ServerManager

manager = ServerManager()

result = manager.install(
    InstallRequest(
        loader="fabric",
        instance_dir=Path("./servers/fabric-test"),
        minecraft_version="latest",
        accept_eula=True,
    )
)

print(result.manifest.to_dict())

process = manager.start(
    "./servers/fabric-test",
    xms="1G",
    xmx="2G",
    log_handler=print,
)

# later:
process.stop()
```

## How Version Resolution Works

### Vanilla

- Reads Mojang version manifest.
- Resolves `latest` to latest stable release.
- Downloads official server jar from version metadata.

### Paper / Folia

- Uses PaperMC v2 API.
- Resolves game version from project version list.
- Resolves build:
  - pinned with `--build`, or
  - latest `default` channel build, with fallback to highest available build.

### Purpur

- Uses Purpur v2 API.
- Resolves latest game version and latest build unless pinned.

### Fabric

- Uses Fabric Meta for game/loader/installer versions.
- Runs Fabric installer in server mode.
- Uses generated `fabric-server-launch.jar`.

### Quilt

- Uses Quilt Meta v3 for game/loader/installer versions.
- Runs Quilt installer in server mode.
- Uses generated `quilt-server-launch.jar`.

### Forge

- Uses Forge Maven metadata.
- For `latest`, uses Maven `<release>` directly.
- For pinned Minecraft versions, selects latest matching Forge line.
- Runs Forge installer and launches via generated argfiles.

### NeoForge

- Uses NeoForge Maven metadata.
- Resolves stable versions by default (`alpha`/`beta`/`snapshot` excluded unless required by the request).
- Runs NeoForge installer and launches via generated argfiles.

## Launch Behavior

Each installed instance stores a `.mcserverlib.json` manifest in its server folder.

The manifest contains:

- resolved loader/version/build information
- Java major version requirement (when available)
- exact startup command template for the host platform
- download sources used during installation

For loaders that generate startup scripts with `pause` on Windows (Forge/NeoForge), the library intentionally launches Java with argfiles directly to keep automation and graceful shutdown reliable.

## CLI Reference

### `loaders`

Prints all supported provider IDs.

### `install`

Required:

- `--loader`
- `--dir`

Optional:

- `--minecraft-version` (default: `latest`)
- `--loader-version` (provider-specific exact version)
- `--build` (provider-specific build number)
- `--java` (Java executable path)
- `--accept-eula`
- `--property key=value` (repeatable, writes `server.properties`)

### `start`

Required:

- `--dir`

Optional:

- `--java`
- `--xms`
- `--xmx`
- `--jvm-arg` (repeatable)

### `manifest`

Required:

- `--dir`

Prints the stored install manifest as JSON.

## Project Layout

```text
mcserverlib/
  cli.py                  # command line entrypoint
  manager.py              # high-level install/start API
  process.py              # process lifecycle and log streaming
  models.py               # dataclasses for requests/results/manifests
  http.py                 # network/download helper
  minecraft.py            # Mojang metadata helpers
  providers/              # per-loader installers/resolvers
tests/
  test_*.py               # deterministic unit tests
pyproject.toml
```

## Testing

Run unit tests:

```bash
python -m pytest
```

The local test suite is fully offline/mocked.

For release validation, run real smoke installs on clean folders for each provider (`install -> start -> stop`) because upstream metadata and installer behavior can change over time.

## Operational Notes

- `eula.txt` is always written by install. Use `--accept-eula` to set `eula=true`.
- If your Java binary is not named `java`, pass `--java /path/to/java`.
- Installers can be heavy on first run (especially Forge/NeoForge) due to dependency hydration.
- Loader ecosystems evolve frequently. Keep pinned versions for production reproducibility.

## Troubleshooting

### "Python was not found"

Use a full interpreter path:

```bash
C:\path\to\python.exe -m mcserverlib.cli loaders
```

### Java mismatch errors

Install the required Java version and pass it explicitly:

```bash
python -m mcserverlib.cli install ... --java "C:\Program Files\Java\jdk-21\bin\java.exe"
```

### Installer exits non-zero

Common causes:

- stale/broken partial install directory
- transient network failure
- blocked Maven endpoints
- wrong pinned loader version for selected Minecraft version

Fix by clearing the target directory and reinstalling with explicit pinned versions.

### Start command exits immediately

Inspect manifest and server logs in the instance directory:

```bash
python -m mcserverlib.cli manifest --dir ./servers/my-server
```

## Status

This implementation has been tested with live installs and startup/shutdown flow across:

- Vanilla
- Paper
- Purpur
- Folia
- Fabric
- Quilt
- Forge
- NeoForge

If you want to extend it with additional providers (for example, Pufferfish, Mohist, or custom private distributions), add a new provider under `mcserverlib/providers` and register it in `providers/__init__.py`.

## License

This project is proprietary and is provided under an "All Rights Reserved"
license. See [LICENSE](LICENSE).
