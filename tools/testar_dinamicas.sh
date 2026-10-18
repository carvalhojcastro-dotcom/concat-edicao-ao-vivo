#!/usr/bin/env bash
# Aplica o plano numa cópia de teste do projeto e renderiza o quadro final de cada frase.
# Uso: testar_dinamicas.sh <projeto base> <plano.json> <saida.jpg>
set -euo pipefail
here="$(cd "$(dirname "$0")" && pwd)"
py="${PY:-python3}"
tmp="$here/../dist/verificacao/teste_dinamicas"
rm -rf "$tmp"; mkdir -p "$tmp"; cp "$1/concat.json" "$tmp/concat.json"
"$py" "$here/legendas_dinamicas.py" "$tmp" "$2" | tail -1
times=$(python3 - "$tmp" <<'PY'
import json, sys
tl = json.load(open(sys.argv[1] + "/concat.json"))["timelines"][0]
ends = sorted({round(c["start"] + c["duration"], 3) for c in tl["clips"] if c["kind"] == "text" and c["trackId"] != "T4"})
print(" ".join(str(round(e - 0.1, 3)) for e in ends))
PY
)
python3 "$here/quadros.py" "$tmp" "$3" $times
