"""Texto das legendas de um corte: words_tl.json + correcoes_tl.json -> words.json -> plano_auto (maiúsculas) -> words_leg.json
correcoes_tl.json (não "correcoes.json", que o plano_auto aplicaria de novo, com índices já deslocados):
  {"12": "rouquidão", "77-79": "rouquidão", "343-347": "vape. O ideal é que não faça uso, né?",
   "49-76": [S do corte, t0, t1, velocidade]}
  - índices do texto.txt; um trecho vira as palavras novas, com o tempo dividido entre elas;
  - lista: trecho que o turbo do corte pulou (fala sobreposta), trocado pelas palavras do episódio inteiro
    (rotulado.json) entre t0 e t1 do bruto, levadas para a timeline.
Palavras que começam depois do fim do corte saem.
Uso: preparar_legenda.py <W> <id> <duração do corte na timeline>"""
import json, os, subprocess, sys
W, cid, dur = sys.argv[1], sys.argv[2], float(sys.argv[3])
d = os.path.join(W, f"c{cid}")
ws = json.load(open(os.path.join(d, "words_tl.json")))
arq = os.path.join(d, "correcoes_tl.json")
corr = json.load(open(arq)) if os.path.exists(arq) else {}
trocas = {}
for k, v in corr.items():
    a, b = (int(x) for x in k.split("-")) if "-" in k else (int(k), int(k))
    trocas[a] = (b, v)
out, i = [], 0
while i < len(ws):
    if i in trocas and isinstance(trocas[i][1], list):
        b, (S0, t0, t1, vel) = trocas[i]
        for s in json.load(open(os.path.join(W, "rotulado.json")))["segments"]:
            for w in s["words"]:
                if t0 <= w["start"] <= t1:
                    out.append({"word": w["word"].strip(), "start": round((w["start"] - S0) / vel, 3),
                                "end": round((w["end"] - S0) / vel, 3)})
        i = b + 1
        continue
    if i in trocas:
        b, v = trocas[i]
        novas = v.split()
        t0, t1 = ws[i]["start"], ws[b]["end"]
        for j, p in enumerate(novas):
            out.append({"word": p, "start": round(t0 + (t1 - t0) * j / len(novas), 3),
                        "end": round(t0 + (t1 - t0) * (j + 1) / len(novas), 3)})
        i = b + 1
        continue
    out.append(dict(ws[i]))
    i += 1
# nomes que o Whisper escreve errado em todo o episódio: "trocas_nomes" no config.json ({"Miriam": "Myrian"})
cfgp = os.path.join(W, "config.json")
nomes = json.load(open(cfgp)).get("trocas_nomes", {}) if os.path.exists(cfgp) else {}
for w in out:
    nucleo = w["word"].strip(".,!?;:…")
    if nucleo in nomes:
        w["word"] = w["word"].replace(nucleo, nomes[nucleo])
out = [w for w in out if w["start"] < dur - 0.05]
out[-1]["end"] = min(out[-1]["end"], dur - 0.1)
json.dump(out, open(os.path.join(d, "words.json"), "w"), ensure_ascii=False, indent=0)
subprocess.run([sys.executable, "-I", os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "plano_auto.py"), d], check=True)
leg = json.load(open(os.path.join(d, "words_leg.json")))
open(os.path.join(d, "texto_leg.txt"), "w").write(" ".join(f"{i}:{w['word']}" for i, w in enumerate(leg)))
print(" ".join(w["word"] for w in leg))
