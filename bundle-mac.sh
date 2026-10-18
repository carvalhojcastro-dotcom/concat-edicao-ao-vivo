#!/usr/bin/env bash
# Monta dist/Concat.app a partir do binário de release, como o CI faz: ícone e Info.plist
# gerados dos arquivos do repositório, FFmpeg do Homebrew copiado para Frameworks e
# assinatura ad-hoc. Rode depois de ./build-mac.sh. Precisa de: brew install dylibbundler
set -euo pipefail
root="$(cd "$(dirname "$0")" && pwd)"
app="$root/dist/Concat.app"
version="$(grep -m1 '^version' "$root/src/Cargo.toml" | sed -E 's/.*"(.*)".*/\1/')"
rm -rf "$app"
mkdir -p "$app/Contents/MacOS" "$app/Contents/Resources" "$app/Contents/Frameworks"
cp "$root/src/target/release/concat" "$app/Contents/MacOS/concat"

# O conjunto de ícones que a Apple pede: cada tamanho e o seu @2x.
iconset="$(mktemp -d)/Concat.iconset"; mkdir -p "$iconset"
icons="$root/assets/icons"
cp "$icons/concat_logo_16.png"  "$iconset/icon_16x16.png"
cp "$icons/concat_logo_32.png"  "$iconset/icon_16x16@2x.png"
cp "$icons/concat_logo_32.png"  "$iconset/icon_32x32.png"
cp "$icons/concat_logo_64.png"  "$iconset/icon_32x32@2x.png"
cp "$icons/concat_logo_128.png" "$iconset/icon_128x128.png"
cp "$icons/concat_logo_256.png" "$iconset/icon_128x128@2x.png"
cp "$icons/concat_logo_256.png" "$iconset/icon_256x256.png"
cp "$icons/concat_logo_512.png" "$iconset/icon_256x256@2x.png"
cp "$icons/concat_logo_512.png" "$iconset/icon_512x512.png"
iconutil -c icns "$iconset" -o "$app/Contents/Resources/Concat.icns"

cat > "$app/Contents/Info.plist" <<PLIST
<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN" "http://www.apple.com/DTDs/PropertyList-1.0.dtd">
<plist version="1.0"><dict>
  <key>CFBundleName</key><string>Concat</string>
  <key>CFBundleDisplayName</key><string>Concat</string>
  <key>CFBundleIdentifier</key><string>app.concat.editor</string>
  <key>CFBundleVersion</key><string>${version}</string>
  <key>CFBundleShortVersionString</key><string>${version}</string>
  <key>CFBundleExecutable</key><string>concat</string>
  <key>CFBundleIconFile</key><string>Concat</string>
  <key>CFBundlePackageType</key><string>APPL</string>
  <key>LSApplicationCategoryType</key><string>public.app-category.video</string>
  <key>LSMinimumSystemVersion</key><string>12.0</string>
  <key>NSHighResolutionCapable</key><true/>
  <key>NSHumanReadableCopyright</key><string>AGPL-3.0-or-later. Fork concat-edicao-ao-vivo; see FORK.md.</string>
  <key>NSMicrophoneUsageDescription</key><string>Concat records voiceovers from your microphone.</string>
  <key>NSSupportsAutomaticGraphicsSwitching</key><true/>
</dict></plist>
PLIST

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
