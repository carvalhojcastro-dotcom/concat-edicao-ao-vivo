#!/bin/zsh
# final_lote.sh <ep> <ID=nome> ...
SP=${TRABALHO:?defina TRABALHO (pasta de trabalho)}
BIN=${0:A:h}
EP=$1; shift
D=$(cat $SP/p$EP/saida.txt); mkdir -p "$D"   # pasta Cortes do episódio
REC="$HOME/Library/Application Support/app.concat.editor/recents.json"; [ -f $SP/recents_backup.json ] || cp "$REC" $SP/recents_backup.json
for par in "$@"; do
  ID=${par%%=*}; NOME=${par#*=}; C=$SP/c$EP/$ID
  python3 $BIN/plano_auto.py $C >/dev/null
  python3 $BIN/destaques.py $SP/c$EP/destaques.txt $ID $C | grep "!!"
  python3 $BIN/plano_auto.py $C $C/aj.json | grep -E "^!!|frases em" | sed "s/^/$ID /"
  $BIN/finalizar.sh $C "$D/$NOME.mp4" 2>&1 | grep -E "exportado|falhou|Error|!!|1080" | sed "s/^/$ID /"
done
