"""Dá nome ao locutor de cada segmento: voz (M/F) + câmera no ar (host/guest).
Uso: nomear.py rotulado.json layout.raw nomes.json saida.json   (nomes: {"host":{"M":..,"F":..},"guest":{...}})"""
import sys, json, numpy as np, collections
rot, raw, nomes, out = sys.argv[1:5]
d = json.load(open(rot)); nomes = json.load(open(nomes))
a = np.fromfile(raw, np.uint8).reshape(-1, 18, 32, 3)
lay = np.where(a[:, 0:5, 0:10, 0].reshape(len(a), -1).mean(1) > 120, "host", "guest")
FPSL = 4
cont = collections.Counter()
for s in d["segments"]:
    i0, i1 = int(s["start"] * FPSL), max(int(s["start"] * FPSL) + 1, int(s["end"] * FPSL))
    c = collections.Counter(lay[i0:i1])
    l = c.most_common(1)[0][0] if c else "host"
    v = s["speaker"] if s["speaker"] in "MF" else "M"
    s["camera"] = l
    s["speaker"] = nomes[l][v]
    cont[s["speaker"]] += 1
json.dump(d, open(out, "w"), ensure_ascii=False)
print(cont)
