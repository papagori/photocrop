$ErrorActionPreference = 'Stop'
$projectRoot = Split-Path -Parent $PSScriptRoot
$setupPath = Join-Path $projectRoot 'dist\PhotoCrop_Setup.exe'
$installTarget = Join-Path $env:TEMP "PhotoCropV2-distribution-test-$PID"
$reportPath = Join-Path $projectRoot 'test-results\installer-smoke.json'

if (-not (Test-Path -LiteralPath $setupPath)) {
    throw "Installer not found: $setupPath"
}
if (Test-Path -LiteralPath $installTarget) {
    throw "Refusing to overwrite existing test target: $installTarget"
}

$install = Start-Process -FilePath $setupPath -ArgumentList @(
    '/VERYSILENT', '/SUPPRESSMSGBOXES', '/NORESTART', '/SP-', '/NOICONS',
    "/DIR=$installTarget"
) -WindowStyle Hidden -PassThru -Wait
if ($install.ExitCode -ne 0) {
    throw "Installer exited with code $($install.ExitCode)"
}

$installedExe = Join-Path $installTarget 'PhotoCropV2.exe'
$uninstaller = Join-Path $installTarget 'unins000.exe'
if (-not (Test-Path -LiteralPath $installedExe) -or
    -not (Test-Path -LiteralPath $uninstaller)) {
    throw 'Installed application or uninstaller is missing'
}

$application = Start-Process -FilePath $installedExe -ArgumentList @(
    '--self-test', $reportPath
) -WindowStyle Hidden -PassThru -Wait
if ($application.ExitCode -ne 0) {
    throw "Installed application self-test exited with code $($application.ExitCode)"
}
$report = Get-Content -LiteralPath $reportPath -Raw | ConvertFrom-Json
if (-not $report.passed -or -not $report.frozen -or
    $report.runtime.external_python_required) {
    throw 'Installed application did not pass the frozen runtime checks'
}

$uninstall = Start-Process -FilePath $uninstaller -ArgumentList @(
    '/VERYSILENT', '/SUPPRESSMSGBOXES', '/NORESTART'
) -WindowStyle Hidden -PassThru -Wait
if ($uninstall.ExitCode -ne 0) {
    throw "Uninstaller exited with code $($uninstall.ExitCode)"
}
Start-Sleep -Seconds 2
if (Test-Path -LiteralPath $installTarget) {
    throw "Uninstaller left the installation directory behind: $installTarget"
}

Write-Host 'Installer distribution test passed.'
