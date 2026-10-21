#!/bin/zsh
# finalizar.sh <dir do corte> <saida.mp4>: legenda no Concat, exporta e faz a folha de conferência
SP=${TRABALHO:?defina TRABALHO (pasta de trabalho)}
BIN=${0:A:h}
PY=~/Desktop/Concat/ferramentas/tools/.venv/bin/python
C=$1; O=$2
$PY -I $BIN/legendar_corte.py $C/vertical.mp4 $C/words_leg.json $C/plano.json "$O" 2>&1 | grep -E "exportado|falhou|Error|Traceback"
python3 $BIN/recentes.py
ffprobe -v error -show_entries stream=width,height,r_frame_rate,color_transfer -show_entries format=duration -of csv=p=0 "$O" | tr '\n' ' '; echo
python3 -c 1 && $PY -I $BIN/folha.py $C "$O" $C/folha.jpg
n=$(ffprobe -v error -count_frames -select_streams v -show_entries stream=nb_read_frames -of csv=p=0 "$O")
k=$(ffmpeg -nostats -sseof -1 -i "$O" -vf "crop=1080:700:0:0,signalstats,metadata=print:key=lavfi.signalstats.YAVG" -an -f null - 2>&1 | grep -o "YAVG=[0-9.]*" | cut -d= -f2 | python3 -c "
import sys; v=[float(x) for x in sys.stdin.read().split()]; k=0
while k < len(v) and v[-1-k] < 25: k += 1
print(k)")
if [ "$k" -gt 0 ]; then
  m=$((n-k)); t="${O%.mp4}.tmp.mp4"
  ffmpeg -v error -y -i "$O" -map 0:v -map 0:a -frames:v $m -c:v libx264 -preset slow -crf 16 -pix_fmt yuv420p -color_primaries bt709 -color_trc bt709 -colorspace bt709 -c:a copy -t $(python3 -c "print($m/30)") -movflags +faststart "$t" && mv "$t" "$O"
  echo "fim escuro: tirei $k quadro(s)"
fi
