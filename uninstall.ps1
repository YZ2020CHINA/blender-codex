[CmdletBinding()]
param([string]$CodexExe = 'codex')
$ErrorActionPreference = 'Stop'
& $CodexExe plugin remove 'blender-studio@blender-studio-tools' --json
if ($LASTEXITCODE -ne 0) { throw 'Plugin removal failed' }
Write-Output 'Scenes, downloaded assets and .state are retained in the source folder.'
