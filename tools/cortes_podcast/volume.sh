#!/bin/zsh
# volume.sh <arquivo.mp4>...: loudnorm em 2 passadas para -14 LUFS / -1.5 dBTP, vídeo copiado
for f in "$@"; do
  j=$(ffmpeg -nostats -i "$f" -vn -af loudnorm=I=-14:TP=-1.5:LRA=11:print_format=json -f null - 2>&1 | sed -n '/^{/,/^}/p')
  mi=$(echo $j | python3 -c "import json,sys;d=json.load(sys.stdin);print(f\"measured_I={d['input_i']}:measured_TP={d['input_tp']}:measured_LRA={d['input_lra']}:measured_thresh={d['input_thresh']}:offset={d['target_offset']}\")")
  t="${f%.mp4}.tmp.mp4"
  ffmpeg -v error -y -i "$f" -map 0:v -map 0:a -c:v copy -af "loudnorm=I=-14:TP=-1.5:LRA=11:${mi}:linear=true" -ar 48000 -c:a aac -b:a 256k -movflags +faststart "$t" && mv "$t" "$f"
  echo "$(ffmpeg -nostats -i "$f" -vn -af ebur128=peak=true -f null - 2>&1 | grep -E '^\s+(I|Peak):' | awk '{print $2}' | tr '\n' ' ') ${f:t}"
done
