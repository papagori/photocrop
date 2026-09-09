$ErrorActionPreference = 'Stop'
Set-Location -LiteralPath $PSScriptRoot
if (-not (Test-Path -LiteralPath '.venv\Scripts\python.exe')) {
    python -m venv .venv
    if ($LASTEXITCODE -ne 0) { throw 'Could not create virtual environment' }
}
& .\.venv\Scripts\python.exe -m pip install -r requirements-dev.txt
if ($LASTEXITCODE -ne 0) { throw 'Dependency installation failed' }
& .\.venv\Scripts\python.exe -m unittest discover -s tests -v
if ($LASTEXITCODE -ne 0) { throw 'Tests failed' }
& .\.venv\Scripts\python.exe -m PyInstaller --noconfirm --clean --onefile --windowed --name PhotoCropV2 main.py
if ($LASTEXITCODE -ne 0) { throw 'Build failed' }
$verification = Start-Process -FilePath (Join-Path $PSScriptRoot 'dist\PhotoCropV2.exe') -ArgumentList '--self-test', 'test-results\compiled-v2.json' -WindowStyle Hidden -PassThru -Wait
if ($verification.ExitCode -ne 0) { throw 'Standalone verification failed; see test-results\compiled-v2.json' }
$report = Get-Content -LiteralPath 'test-results\compiled-v2.json' -Raw | ConvertFrom-Json
if (-not $report.passed -or -not $report.frozen) { throw 'Standalone verification did not pass' }
Write-Host 'Ready: dist\PhotoCropV2.exe'
