#!/usr/bin/env bash
# U19: build the PyInstaller backend sidecar and place it where Tauri expects it
# (externalBin requires the `<name>-<target-triple>` suffix). Run from repo root.
set -euo pipefail

python -m pip install --quiet pyinstaller
python -m PyInstaller --clean --noconfirm backend/sph-backend.spec

TRIPLE="$(rustc -Vv | sed -n 's/^host: //p')"
DEST="apps/desktop/src-tauri/binaries"
mkdir -p "$DEST"
if [ -f "dist/sph-backend" ]; then
  cp "dist/sph-backend" "$DEST/sph-backend-$TRIPLE"
  chmod +x "$DEST/sph-backend-$TRIPLE"
  echo "wrote $DEST/sph-backend-$TRIPLE"
elif [ -f "dist/sph-backend.exe" ]; then
  cp "dist/sph-backend.exe" "$DEST/sph-backend-$TRIPLE.exe"
  echo "wrote $DEST/sph-backend-$TRIPLE.exe"
else
  echo "ERROR: PyInstaller output not found in dist/"; exit 1
fi

echo "Now add \"externalBin\": [\"binaries/sph-backend\"] to tauri.conf.json bundle and run tauri build."
