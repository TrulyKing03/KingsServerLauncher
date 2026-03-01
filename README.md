# KingsServerLauncher

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
- A JVM runtime installed and reachable (default executable: `java`)
- Internet access for metadata and artifact downloads

## Install

From this repository:

```bash
python -m pip install -e .[dev]
```

If `python` is not on your PATH, use your full interpreter path instead.

## One-Task Build (Windows EXE)

Build a desktop launcher executable in one command:

```bash
python -m mcserverlib.build
```

Output:

- `dist/KingsServerLauncher.exe`

PowerShell wrapper (same result):

```powershell
.\build_launcher.ps1
```

## Cross-Platform Builds (Linux/macOS/Windows)

Native binaries are built per operating system:

- Windows: `KingsServerLauncher.exe`
- Linux: `KingsServerLauncher-linux`
- macOS: `KingsServerLauncher-macos`

Platform maintainers:

- Linux/macOS builds are managed by `boyninja1555`.
- Windows builds are managed by `TrulyKing03`.

The repository includes a GitHub Actions workflow for this:

- `.github/workflows/build-multiplatform.yml`

How to use it:

1. Open the repository on GitHub.
2. Go to **Actions**.
3. Run **Build Multi-Platform Binaries**.
4. Download artifacts from the completed run.

Note:

- Executable files are intentionally **not committed** to this repository.

## Desktop Launcher

Run the GUI directly from Python:

```bash
python -m mcserverlib.cli gui
```

The launcher lets users:

- choose and save the server storage folder before install/start
- choose loader
- choose Minecraft version from fetched metadata
- optionally pin loader version/build
- install server files
- start/stop the server with live console logs
- send in-game server console commands directly from the launcher UI
- open Help links directly from the launcher:
  - Discord: `https://discord.gg/AqUmRUshhK`
  - Website: `https://TrulyKing.dev`

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

- Uses Forge metadata endpoints.
- For `latest`, uses the upstream release marker directly.
- For pinned Minecraft versions, selects latest matching Forge line.
- Runs Forge installer and launches via generated argfiles.

### NeoForge

- Uses NeoForge metadata endpoints.
- Resolves stable versions by default (`alpha`/`beta`/`snapshot` excluded unless required by the request).
- Runs NeoForge installer and launches via generated argfiles.

## Launch Behavior

Each installed instance stores a `.mcserverlib.json` manifest in its server folder.

The manifest contains:

- resolved loader/version/build information
- runtime major-version requirement (when available)
- exact startup command template for the host platform
- download sources used during installation

For loaders that generate startup scripts with `pause` on Windows (Forge/NeoForge), the library intentionally launches the runtime with argfiles directly to keep automation and graceful shutdown reliable.

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
- `--java` (runtime executable path)
- `--accept-eula`
- `--property key=value` (repeatable, writes `server.properties`)

### `start`

Required:

- `--dir`

Optional:

- `--java` (runtime executable path)
- `--xms`
- `--xmx`
- `--jvm-arg` (repeatable)

### `manifest`

Required:

- `--dir`

Prints the stored install manifest as JSON.

### `gui`

Opens the desktop launcher UI.

## Project Layout

```text
mcserverlib/
  build.py                # one-command PyInstaller build
  catalog.py              # version catalog for launcher UI
  cli.py                  # command line entrypoint
  gui_launcher.py         # desktop launcher
  manager.py              # high-level install/start API
  process.py              # process lifecycle and log streaming
  models.py               # dataclasses for requests/results/manifests
  http.py                 # network/download helper
  minecraft.py            # Mojang metadata helpers
  providers/              # per-loader installers/resolvers
build_launcher.ps1        # Windows one-command build wrapper
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
- If your runtime binary is not named `java`, pass `--java /path/to/runtime`.
- Installers can be heavy on first run (especially Forge/NeoForge) due to dependency hydration.
- Loader ecosystems evolve frequently. Keep pinned versions for production reproducibility.

## Troubleshooting

### "Python was not found"

Use a full interpreter path:

```bash
C:\path\to\python.exe -m mcserverlib.cli loaders
```

### Runtime mismatch errors

Install the required runtime version and pass it explicitly:

```bash
python -m mcserverlib.cli install ... --java "C:\path\to\java.exe"
```

### Installer exits non-zero

Common causes:

- stale/broken partial install directory
- transient network failure
- blocked metadata endpoints
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
