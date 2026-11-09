[CmdletBinding()]
param([string]$PythonExe = 'python')
$ErrorActionPreference = 'Stop'
& $PythonExe -X utf8 -s (Join-Path $PSScriptRoot 'scripts/package_plugin.py') --zip
if ($LASTEXITCODE -ne 0) { throw 'Packaging failed' }
