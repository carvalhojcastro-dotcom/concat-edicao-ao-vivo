#!/usr/bin/env bash
# Prepara um Mac (Apple Silicon) para editar reels com este fork. Passo a passo em INSTALAR.md.
#   ./tools/setup.sh            dependências, venv, fontes, pastas, Concat.app (da Release) e API ligada
#   ./tools/setup.sh --compilar  compila o Concat do código em vez de baixar (demora ~10 min)
set -euo pipefail
raiz="$(cd "$(dirname "$0")/.." && pwd)"
cd "$raiz"

echo "== Homebrew: ffmpeg, gh, python (e rustup/dylibbundler para compilar)"
command -v brew >/dev/null || { echo "Instale o Homebrew primeiro: https://brew.sh" >&2; exit 1; }
brew list rustup >/dev/null 2>&1 || brew install rustup
brew list ffmpeg >/dev/null 2>&1 || brew install ffmpeg
brew list dylibbundler >/dev/null 2>&1 || brew install dylibbundler
command -v gh >/dev/null || brew install gh
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
# Montserrat, Poppins, Plus Jakarta e Playfair (OFL) já vêm no repositório. A Scholar tem licença
# própria: vem do cache do CapCut (baixe a fonte uma vez dentro do CapCut) ou copie do Mac antigo.
for f in Scholar-Regular.otf Scholar-Italic.otf; do
  [ -f "fonts/$f" ] && continue
  achado="$(find "$cache" -name "$f" 2>/dev/null | head -1 || true)"
  if [ -n "$achado" ]; then cp "$achado" "fonts/$f"; echo "  $f copiada do cache do CapCut"
  else echo "  FALTA fonts/$f: copie do Mac antigo (ferramentas/fonts) ou use a fonte Scholar uma vez no CapCut"; fi
done

# Coolvetica (Typodermic): grátis, mas sem redistribuir; baixa do site oficial, só os arquivos dela.
if [ ! -f fonts/Coolvetica-Rg.otf ]; then
  tmp="$(mktemp -d)"
  if curl -sSL -m 180 -A "Mozilla/5.0" -o "$tmp/t.zip" "https://typodermicfonts.com/assets/downloads/$(curl -sSL -m 30 -A "Mozilla/5.0" https://typodermicfonts.com/downloads/ | grep -oE 'typodermic-free-fonts-[^"/]*\.zip' | head -1)" \
     && unzip -q -o -j "$tmp/t.zip" "Coolvetica Rg.otf" "Coolvetica Rg It.otf" "Typodermic Desktop EULA*.pdf" -d "$tmp/x"; then
    cp "$tmp/x/Coolvetica Rg.otf" fonts/Coolvetica-Rg.otf
    cp "$tmp/x/Coolvetica Rg It.otf" fonts/Coolvetica-RgIt.otf
    cp "$tmp/x/"Typodermic*EULA*.pdf fonts/Coolvetica-EULA-Typodermic.pdf
    echo "  Coolvetica baixada da Typodermic"
  else echo "  FALTA fonts/Coolvetica-Rg.otf (typodermicfonts.com/downloads, pacote grátis)"; fi
  rm -rf "$tmp"
fi

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

echo "== Pastas de trabalho, ao lado do repositório"
mae="$(dirname "$raiz")"   # a pasta Concat: editados/, exportados/, referencias/ e ferramentas/ (este repositório)
mkdir -p "$mae/editados" "$mae/exportados"
[ -e "$mae/referencias" ] || ln -s "$(basename "$raiz")/referencias" "$mae/referencias"
echo "  $mae/{editados,exportados,referencias}"

echo "== Concat deste fork"
if [ "${1:-}" = "--compilar" ]; then
  ./build-mac.sh && ./bundle-mac.sh
  rm -rf /Applications/Concat.app && cp -R dist/Concat.app /Applications/
  echo "  compilado e instalado em /Applications"
elif [ ! -d /Applications/Concat.app ]; then
  gh auth status >/dev/null 2>&1 || gh auth login
  repo="$(git remote get-url origin 2>/dev/null | sed -E 's#(\.git)?$##; s#.*github.com[:/]##')"
  tmp="$(mktemp -d)"
  gh release download --repo "$repo" --pattern 'Concat-*-mac-arm64.zip' --dir "$tmp"
  ditto -x -k "$tmp"/Concat-*-mac-arm64.zip /Applications/
  xattr -dr com.apple.quarantine /Applications/Concat.app 2>/dev/null || true
  rm -rf "$tmp"
  echo "  baixado da Release do GitHub e instalado em /Applications"
else
  echo "  já instalado em /Applications/Concat.app"
fi

echo "== API do Concat (porta 7420) e .concat-token"
# Liga o servidor nas preferências do Concat e grava o mesmo token em .concat-token. Com o Concat
# aberto ele regravaria as preferências ao fechar, então isso só é feito com o app fechado.
if pgrep -f "Concat.app/Contents/MacOS" >/dev/null; then
  [ -f .concat-token ] || echo "  feche o Concat e rode o setup de novo para ligar a API"
else
  tools/.venv/bin/python - <<'PY'
import json, os, secrets
pasta = os.path.expanduser("~/Library/Application Support/app.concat.editor")
os.makedirs(pasta, exist_ok=True)
arq = os.path.join(pasta, "settings.json")
prefs = json.load(open(arq)) if os.path.exists(arq) else {}
srv = prefs.get("server") or {}
if not srv.get("token"):
    srv["token"] = secrets.token_hex(24)
srv["enabled"] = True
srv.setdefault("listen", "127.0.0.1:7420")
prefs["server"] = srv
json.dump(prefs, open(arq, "w"), indent=2)
fd = os.open(".concat-token", os.O_WRONLY | os.O_CREAT | os.O_TRUNC, 0o600)
os.write(fd, srv["token"].encode()); os.close(fd)
print("  API ligada; token em .concat-token (fora do Git)")
PY
fi

cat <<'FIM'

== Falta fazer à mão (uma vez)
- Chave da API do Higgsfield (B-roll): ./tools/configurar_chave_higgsfield.sh
  (a chave é digitada sem aparecer e fica em .env.local, fora do Git).
- Se o setup avisou FALTA na Scholar: copie Scholar-Regular.otf e Scholar-Italic.otf para fonts/.
Pronto: abra o Claude Code nesta pasta e diga "edita esse vídeo: <arquivo>".
FIM
