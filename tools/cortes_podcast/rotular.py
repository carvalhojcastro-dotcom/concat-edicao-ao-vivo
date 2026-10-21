import sys, json
sys.path.insert(0, sys.argv[0].rsplit('/', 1)[0])
from f0 import carregar, f0_trecho
tr, wav, out = sys.argv[1], sys.argv[2], sys.argv[3]
d = json.load(open(tr)); x, sr = carregar(wav)
segs = []
for s in d["segments"]:
    f, n = f0_trecho(x, sr, s["start"], s["end"])
    voz = "?" if f is None or n < 5 else ("M" if f < 158 else "F")
    s2 = {"start": s["start"], "end": s["end"], "text": s["text"].strip(), "f0": f, "speaker": voz,
          "words": [{"word": w["word"], "start": w["start"], "end": w["end"]} for w in s.get("words", [])]}
    segs.append(s2)
json.dump({"segments": segs}, open(out, "w"), ensure_ascii=False)
import collections
print(collections.Counter(s["speaker"] for s in segs))
