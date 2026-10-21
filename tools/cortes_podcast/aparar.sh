#!/bin/zsh
# aparar.sh <final.mp4>...: tira os quadros escuros do fim (vídeo acabou e a legenda ficou), sem reencode
for F in "$@"; do
  nf=$(ffprobe -v error -count_packets -select_streams v -show_entries stream=nb_read_packets -of csv=p=0 "$F")
  k=$(ffmpeg -nostats -sseof -1.5 -i "$F" -vf "crop=1080:700:0:0,signalstats,metadata=print:key=lavfi.signalstats.YAVG" -an -f null - 2>&1 | grep -o "YAVG=[0-9.]*" | cut -d= -f2 | python3 -c "
import sys; v=[float(x) for x in sys.stdin.read().split()]; k=0
while k < len(v) and v[-1-k] < 25: k += 1
print(k)")
  if [ "$k" -gt 0 ]; then
    t="${F%.mp4}.tmp.mp4"
    ffmpeg -v error -y -i "$F" -map 0 -c copy -t $(python3 -c "print(($nf-$k)/30)") -movflags +faststart "$t" && mv "$t" "$F"
    echo "aparado $k quadro(s): ${F:t}"
  fi
done
