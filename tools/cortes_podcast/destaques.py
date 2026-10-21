"""Converte a decupagem de destaque (texto do edit-director) em composições para plano_auto.py.
Uso: destaques.py <destaques.txt> <ID> <dir do corte>  -> grava <dir>/aj.json"""
import json, os, re, sys, difflib
txt, cid, pasta = sys.argv[1:4]
words = json.load(open(os.path.join(pasta, "words_leg.json")))
norm = lambda w: re.sub(r"[^\wà-úç%]", "", w.lower())
W = [norm(w["word"]) for w in words]
bloco, itens = None, []
for l in open(txt):
    l = l.strip()
    if re.fullmatch(r"M\d+", l):
        bloco = l; continue
    if bloco == cid and l.startswith("-"):
        m = re.match(r'-\s*"(.+?)".*?chave:\s*([^|]+)\|\s*(\w+)', l)
        if m:
            itens.append((m.group(1), m.group(2).strip(), m.group(3)))
PRESETS = ["escada", "chave", "sanduiche"]
comps, usados = [], set()
for frase, chave, cor in itens:
    alvo = [norm(t) for t in frase.split() if norm(t)]
    n = len(alvo); melhor = (0, None)
    for i in range(len(W) - n + 1):
        if any(k in usados for k in range(i, i + n)):
            continue
        r = difflib.SequenceMatcher(a=alvo, b=W[i:i + n]).ratio()
        if r > melhor[0]:
            melhor = (r, i)
    if melhor[0] < 0.7:
        print(f"!! não achei: {frase} ({melhor[0]:.2f})"); continue
    i = melhor[1]; idx = list(range(i, i + n))
    toks = [words[k]["word"] for k in idx]
    nk = [norm(t) for t in toks]
    kc = norm(chave)
    kpos = nk.index(kc) if kc in nk else max(range(n), key=lambda j: difflib.SequenceMatcher(a=kc, b=nk[j]).ratio())
    chave_txt = "*" + re.sub(r"[,.;:!]+$", "", toks[kpos]) + "*"
    antes, depois = toks[:kpos], toks[kpos + 1:]
    if not antes:
        linhas = [chave_txt] + ([" ".join(depois)] if depois else [])
        if not depois:
            linhas = [chave_txt]
    else:
        if len(antes) > 3:
            h = (len(antes) + 1) // 2
            linhas = [" ".join(antes[:h]), " ".join(antes[h:])]
        else:
            linhas = [" ".join(antes)]
        linhas.append(" ".join([chave_txt] + depois))
    comps.append({"de": i, "linhas": linhas, "destaque": "#f4c430" if cor.startswith("amar") else "#ffffff"})
    usados.update(idx)
comps.sort(key=lambda c: c["de"])
ant = None
for c in comps:
    nl = len(c["linhas"])
    ops = ["escada", "chave"] if nl >= 2 else ["grande"]
    if nl >= 3:
        ops = ["escada", "chave", "sanduiche"]
    p = next(o for o in ops if o != ant) if len(ops) > 1 else ops[0]
    c["preset"] = p; ant = p
    pequenas = {"escada": [0], "sanduiche": [1]}.get(p, [])   # linhas "p" do preset: sobe para "m" (legível no celular)
    for j in pequenas:
        if j < len(c["linhas"]) - 1 or (j < len(c["linhas"]) and "*" not in c["linhas"][j]):
            c["linhas"][j] = " ".join(t if "*" in t else t + "^m" for t in c["linhas"][j].split())
    print(f"[{c['de']:3d}] {p:9s} {' / '.join(c['linhas'])}  {c['destaque']}")
json.dump(comps, open(os.path.join(pasta, "aj.json"), "w"), ensure_ascii=False, indent=1)
