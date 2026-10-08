$ErrorActionPreference = "Stop"
$ProjectRoot = Split-Path -Parent $MyInvocation.MyCommand.Path
$Python = if ($env:PYTHON_EXE) { $env:PYTHON_EXE } else { "python" }
& $Python -m pip install --disable-pip-version-check --no-input --target (Join-Path $ProjectRoot ".deps") "pytableau==3.0.0"