#!/usr/bin/env bash
# Prepara um Mac (Apple Silicon) para editar reels com este fork. Rode da raiz do repositório:
#   ./tools/setup.sh            dependências + venv + fontes
#   ./tools/setup.sh --app      também compila e monta dist/Concat.app (demora ~10 min)
set -euo pipefail
raiz="$(cd "$(dirname "$0")/.." && pwd)"
cd "$raiz"

echo "== Homebrew: rustup, ffmpeg, dylibbundler, python"
command -v brew >/dev/null || { echo "Instale o Homebrew primeiro: https://brew.sh" >&2; exit 1; }
brew list rustup >/dev/null 2>&1 || brew install rustup
brew list ffmpeg >/dev/null 2>&1 || brew install ffmpeg
brew list dylibbundler >/dev/null 2>&1 || brew install dylibbundler
command -v python3 >/dev/null || brew install python

echo "== Ambiente Python das ferramentas (tools/.venv)"
[ -d tools/.venv ] || python3 -m venv tools/.venv
tools/.venv/bin/pip install -q --upgrade pip
tools/.venv/bin/pip install -q mlx-whisper higgsfield-client python-dotenv pillow fonttools mediapipe \
  "numpy<2.1"
# o mediapipe puxa o opencv 5, que tirou o detector de rosto do zoom: fica o contrib 4.x
tools/.venv/bin/pip uninstall -y -q opencv-python-headless 2>/dev/null || true
tools/.venv/bin/pip install -q --force-reinstall --no-deps "opencv-contrib-python<5"

echo "== Fontes das Legendas Dinâmicas (fonts/)"
mkdir -p fonts
cache="$HOME/Movies/CapCut/User Data/Cache"
for f in Scholar-Regular.otf Scholar-Italic.otf Montserrat-Bold.otf; do
  [ -f "fonts/$f" ] && continue
  achado="$(find "$cache" -name "$f" 2>/dev/null | head -1 || true)"
  if [ -n "$achado" ]; then cp "$achado" "fonts/$f"; echo "  $f copiada do cache do CapCut"
  else echo "  FALTA fonts/$f (Scholar: baixe no CapCut; Montserrat: fonts.google.com)"; fi
done

if [ ! -f fonts/HelveticaNeue-Medium.ttf ]; then
  tools/.venv/bin/python - <<'PY'
from fontTools.ttLib import TTCollection
c = TTCollection("/System/Library/Fonts/HelveticaNeue.ttc")
f = next(x for x in c.fonts if x["name"].getDebugName(2) == "Medium")
for r in f["name"].names:
    if r.nameID in (1, 4, 16): r.string = "Helvetica Neue Medium"
    if r.nameID in (2, 17): r.string = "Regular"
    if r.nameID == 6: r.string = "HelveticaNeue-Medium-Concat"
f.save("fonts/HelveticaNeue-Medium.ttf")
print("  HelveticaNeue-Medium.ttf extraída do sistema (semibold das legendas)")
PY
fi

# Helvetica do print "helvetica" (referencias/Legendas dinamicas): condensada e pesada, no destaque em bold.
if [ ! -f fonts/HelveticaNeue-CondensedBlack.ttf ]; then
  tools/.venv/bin/python - <<'PY'
from fontTools.ttLib import TTCollection
c = TTCollection("/System/Library/Fonts/HelveticaNeue.ttc")
f = next(x for x in c.fonts if x["name"].getDebugName(4) == "Helvetica Neue Condensed Black")
for r in f["name"].names:
    if r.nameID in (1, 4, 16): r.string = "Helvetica Neue Condensed Black"
    if r.nameID in (2, 17): r.string = "Regular"
    if r.nameID == 6: r.string = "HelveticaNeue-CondensedBlack-Concat"
f.save("fonts/HelveticaNeue-CondensedBlack.ttf")
print("  HelveticaNeue-CondensedBlack.ttf extraída do sistema (destaque em bold)")
PY
fi

# Montserrat Light (OFL) e Coolvetica (Typodermic, grátis, sem redistribuir) não vêm no Mac.
[ -f fonts/Montserrat-Light.ttf ] || echo "  FALTA fonts/Montserrat-Light.ttf (github.com/JulietaUla/Montserrat, fonts/ttf)"
[ -f fonts/Coolvetica-Rg.otf ] || echo "  FALTA fonts/Coolvetica-Rg.otf (typodermicfonts.com/downloads, pacote grátis: 'Coolvetica Rg.otf')"

if [ "${1:-}" = "--app" ]; then
  echo "== Compilando o Concat deste fork"
  ./build-mac.sh && ./bundle-mac.sh
  echo "  Instale com: rm -rf /Applications/Concat.app && cp -R dist/Concat.app /Applications/"
fi

cat <<'FIM'

== Falta fazer à mão (uma vez)
1. Abra o Concat deste fork > Configurações > API: ligue o servidor (porta 7420) e copie o token
   para o arquivo .concat-token na raiz do repositório.
2. Chave da API do Higgsfield (B-roll): ./tools/configurar_chave_higgsfield.sh
   (a chave é digitada sem aparecer e fica em .env.local, fora do Git).
Pronto: abra o Claude Code nesta pasta e diga "edita esse vídeo: <arquivo>".
FIM
