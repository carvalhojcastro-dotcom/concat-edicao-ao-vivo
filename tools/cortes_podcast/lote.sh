#!/bin/zsh
# lote.sh <ep> <run> <id...>: monta, enquadra, renderiza e confere cada candidato
SP=${TRABALHO:?defina TRABALHO (pasta de trabalho)}
BIN=${0:A:h}
PY=~/Desktop/Concat/ferramentas/tools/.venv/bin/python
EP=$1; R=$2; shift 2
V=$(cat $SP/p$EP/fonte.txt)   # caminho do vídeo do episódio
for ID in "$@"; do
  C=$SP/c$EP/$ID; mkdir -p $C
  T=$(python3 -c "
import json,sys;d=json.load(open('$R/06-candidates.json'));c=[c for c in d['clips'] if c.get('id')=='$ID' or c.get('clip_id')=='$ID'][0]
ov=json.load(open('$SP/c$EP/overrides.json')) if __import__('os').path.exists('$SP/c$EP/overrides.json') else {}
if '$ID' in ov: print(ov['$ID'])
else: print(','.join(f\"{s['source_start']}-{s['source_end']}\" for s in (c.get('segments') or c.get('intervals'))))")
  echo "== $ID $T"
  $PY -I $BIN/montar_corte.py $SP/p$EP/nomeado.json $SP/p$EP/audio.wav "$V" $C "$T"
  $PY -I $BIN/enquadrar.py $C/corte.json 2>&1 | grep -E "^ +[0-9]" > $C/enquadrar.txt
  python3 $BIN/estabilizar.py $C/corte.json > $C/estabilizar.txt
  $PY -I $BIN/render_vertical.py $C/corte.json $C/vertical.mp4 >/dev/null
  $PY -I $BIN/conferir.py $C $SP/p$EP/audio.wav 2>&1 | grep -v -E "Warning|mel_spec" > $C/conferir.txt
  echo "   ok"
done
