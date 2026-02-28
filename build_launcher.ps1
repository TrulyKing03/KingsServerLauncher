param(
    [string]$PythonExe = "python",
    [string]$Name = "KingsServerLauncher"
)

$ErrorActionPreference = "Stop"

Write-Host "Using Python: $PythonExe"
& $PythonExe -m mcserverlib.build --name $Name

Write-Host "Done. Check the dist folder for the launcher executable."
