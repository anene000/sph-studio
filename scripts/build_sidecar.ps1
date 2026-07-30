# U19: build the PyInstaller backend sidecar for Tauri (Windows). Run from repo root.
$ErrorActionPreference = "Stop"

python -m pip install --quiet pyinstaller
python -m PyInstaller --clean --noconfirm backend/sph-backend.spec

$triple = (rustc -Vv | Select-String '^host: ').ToString().Replace('host: ', '').Trim()
$dest = "apps/desktop/src-tauri/binaries"
New-Item -ItemType Directory -Force -Path $dest | Out-Null

if (Test-Path "dist/sph-backend.exe") {
    Copy-Item "dist/sph-backend.exe" "$dest/sph-backend-$triple.exe" -Force
    Write-Output "wrote $dest/sph-backend-$triple.exe"
} else {
    throw "PyInstaller output dist/sph-backend.exe not found"
}
Write-Output "Now add `"externalBin`": [`"binaries/sph-backend`"] to tauri.conf.json bundle and run tauri build."
