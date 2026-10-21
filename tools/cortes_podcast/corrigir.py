"""Corrige palavras do words.json por texto. Uso: corrigir.py <dir> '<json {"de": "para"}>'
"de" e "para" são sequências de palavras; casa ignorando maiúsculas e pontuação; os tempos da
sequência original são repartidos entre as palavras novas."""
import json, os, re, sys
pasta, pares = sys.argv[1], json.loads(sys.argv[2])
f = os.path.join(pasta, "words.json"); w = json.load(open(f))
norm = lambda t: re.sub(r"[^\wà-úç]", "", t.lower())
for de, para in pares.items():
    a, b = de.split(), para.split(); n = len(a); i = 0; feitos = 0
    while i <= len(w) - n:
        if [norm(x["word"]) for x in w[i:i + n]] == [norm(t) for t in a]:
            t0, t1 = w[i]["start"], w[i + n - 1]["end"]
            passo = (t1 - t0) / len(b)
            novos = [dict(w[i], word=t, start=round(t0 + k * passo, 3), end=round(t0 + (k + 1) * passo, 3)) for k, t in enumerate(b)]
            novos[0]["start"] = t0
            w[i:i + n] = novos; i += len(b); feitos += 1
        else:
            i += 1
    print(f"{de!r} -> {para!r}: {feitos}")
json.dump(w, open(f, "w"), ensure_ascii=False, indent=1)
