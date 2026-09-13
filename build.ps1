$ErrorActionPreference = 'Stop'
Set-Location -LiteralPath $PSScriptRoot
if (-not (Test-Path -LiteralPath '.venv\Scripts\python.exe')) {
    python -m venv .venv
    if ($LASTEXITCODE -ne 0) { throw 'Could not create virtual environment' }
}
& .\.venv\Scripts\python.exe -c "import PIL, PySide6, PyInstaller; assert tuple(map(int, PIL.__version__.split('.')[:2])) >= (12, 1); assert PIL.__version__.split('.')[0] == '12'; assert PySide6.__version__ == '6.11.0'; assert PyInstaller.__version__ == '6.20.0'"
if ($LASTEXITCODE -ne 0) {
    & .\.venv\Scripts\python.exe -m pip install --disable-pip-version-check --no-input -r requirements-dev.txt
    if ($LASTEXITCODE -ne 0) { throw 'Dependency installation failed' }
}
& .\.venv\Scripts\python.exe tools\build_icon.py
if ($LASTEXITCODE -ne 0) { throw 'Application icon generation failed' }
$appVersion = (& .\.venv\Scripts\python.exe -c "from cropper.version import __version__; print(__version__)").Trim()
if (-not $appVersion) { throw 'Could not read the application version' }
$previousQtPlatform = $env:QT_QPA_PLATFORM
$env:QT_QPA_PLATFORM = 'offscreen'
& .\.venv\Scripts\python.exe -m unittest discover -s tests -v
$testExitCode = $LASTEXITCODE
$env:QT_QPA_PLATFORM = $previousQtPlatform
if ($testExitCode -ne 0) { throw 'Tests failed' }
& .\.venv\Scripts\python.exe -m PyInstaller --noconfirm --clean PhotoCropV2.spec
if ($LASTEXITCODE -ne 0) { throw 'Build failed' }
$verification = Start-Process -FilePath (Join-Path $PSScriptRoot 'dist\PhotoCropV2.exe') -ArgumentList '--self-test', 'test-results\compiled-v2.json' -WindowStyle Hidden -PassThru -Wait
if ($verification.ExitCode -ne 0) { throw 'Standalone verification failed; see test-results\compiled-v2.json' }
$report = Get-Content -LiteralPath 'test-results\compiled-v2.json' -Raw | ConvertFrom-Json
if (-not $report.passed -or -not $report.frozen) { throw 'Standalone verification did not pass' }
$innoCandidates = @(
    (Join-Path $env:LOCALAPPDATA 'Programs\Inno Setup 6\ISCC.exe'),
    (Join-Path ${env:ProgramFiles(x86)} 'Inno Setup 6\ISCC.exe'),
    (Join-Path $env:ProgramFiles 'Inno Setup 6\ISCC.exe')
)
$iscc = $innoCandidates | Where-Object { $_ -and (Test-Path -LiteralPath $_) } | Select-Object -First 1
if ($iscc) {
    & $iscc "/DAppVersion=$appVersion" 'installer\PhotoCropV2.iss'
    if ($LASTEXITCODE -ne 0) { throw 'Installer build failed' }
    Write-Host 'Ready: dist\PhotoCrop_Setup.exe'
} else {
    Write-Warning 'Inno Setup 6 was not found; installer build skipped.'
}
Write-Host 'Ready: dist\PhotoCropV2.exe'
