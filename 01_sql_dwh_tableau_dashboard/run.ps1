$ErrorActionPreference = "Stop"
$ProjectRoot = Split-Path -Parent $MyInvocation.MyCommand.Path
$Python = if ($env:PYTHON_EXE) { $env:PYTHON_EXE } else { "python" }
$Deps = Join-Path $ProjectRoot ".deps"

if (-not (Test-Path -LiteralPath $Deps)) {
    & (Join-Path $ProjectRoot "setup_tableau.ps1")
}
$env:PYTHONPATH = "$Deps;$env:PYTHONPATH"

Push-Location $ProjectRoot
try {
    & $Python "src\generate_data.py"
    & $Python "src\build_dwh.py"
    & $Python "src\export_dashboard_data.py"
    & $Python "src\export_tableau_kpis.py"
    & $Python "src\build_tableau_workbook.py"
    & $Python "src\repair_tableau_workbook.py"
    & $Python "src\build_tableau_professional.py"
    & $Python "src\finalize_tableau_professional.py"
    & $Python "src\build_preview.py"
    & $Python "src\validate_dwh.py"
    & $Python "-m" "unittest" "discover" "-s" "tests" "-v"
}
finally {
    Pop-Location
}