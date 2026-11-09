[CmdletBinding()]
param([string]$PythonExe = 'python', [string]$BlenderExe = '', [string]$CodexExe = 'codex')
$ErrorActionPreference = 'Stop'
$arguments = @('-X','utf8','-s',(Join-Path $PSScriptRoot 'scripts/package_plugin.py'),'--prepare')
if ($BlenderExe) { $arguments += @('--blender',$BlenderExe) }
& $PythonExe @arguments
if ($LASTEXITCODE -ne 0) { throw 'Plugin preparation failed' }
& $CodexExe plugin marketplace add $PSScriptRoot --json
if ($LASTEXITCODE -ne 0) { throw 'Marketplace registration failed' }
& $CodexExe plugin add 'blender-studio@blender-studio-tools' --json
if ($LASTEXITCODE -ne 0) { throw 'Plugin installation failed' }
& $CodexExe plugin list --marketplace blender-studio-tools --json
if ($LASTEXITCODE -ne 0) { throw 'Plugin verification failed' }
Write-Output 'Restart Codex or open a new chat to load Blender Studio. Keep this source folder in place.'
