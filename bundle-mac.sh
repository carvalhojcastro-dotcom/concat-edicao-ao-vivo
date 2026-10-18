#!/usr/bin/env bash
# Monta dist/Concat.app a partir do binário de release, como o CI faz:
# FFmpeg do Homebrew copiado para Frameworks e assinatura ad-hoc.
set -euo pipefail
root="$(cd "$(dirname "$0")" && pwd)"
app="$root/dist/Concat.app"
rm -rf "$app"
mkdir -p "$app/Contents/MacOS" "$app/Contents/Resources" "$app/Contents/Frameworks"
cp "$root/src/target/release/concat" "$app/Contents/MacOS/concat"
cp /Applications/Concat.app/Contents/Info.plist "$app/Contents/Info.plist"
cp /Applications/Concat.app/Contents/Resources/Concat.icns "$app/Contents/Resources/Concat.icns"
dylibbundler -od -b \
  -x "$app/Contents/MacOS/concat" \
  -d "$app/Contents/Frameworks" \
  -p @executable_path/../Frameworks >/dev/null
if otool -L "$app/Contents/MacOS/concat" | grep -E '/opt/homebrew|/usr/local'; then
  echo "o binário ainda carrega bibliotecas de fora do app" >&2
  exit 1
fi
codesign --force --deep -s - "$app"
codesign --verify --deep --strict "$app"
echo "ok: $app"
