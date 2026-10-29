"""Converte a decupagem de destaque (texto do edit-director) nos blocos dinâmicos do capcut_legendas_ig.py.
Uso: destaques.py <destaques.txt> <ID> <dir do corte>  -> grava <dir>/blocos.json
Cada frase de destaque vira um bloco (linhas de 1 a 3 palavras, a chave grande); tudo branco (a cor que o
edit-director sugere é ignorada: as legendas são sempre brancas desde 2026-10-29)."""
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
blocos, usados = [], set()
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
    nk = [norm(words[k]["word"]) for k in idx]
    kc = norm(chave)
    kpos = nk.index(kc) if kc in nk else max(range(n), key=lambda j: difflib.SequenceMatcher(a=kc, b=nk[j]).ratio())
    antes, depois = idx[:kpos], idx[kpos + 1:]
    # linhas equilibradas de até 3 palavras; um pedaço curto (1-2 palavras) antes da chave divide a linha com ela
    # ("o seu / CORAÇÃO" vira "o seu CORAÇÃO"), como nos blocos aprovados
    def partir(ks):
        if not ks:
            return []
        n_l = -(-len(ks) // 3)
        tam = [len(ks) // n_l + (1 if j < len(ks) % n_l else 0) for j in range(n_l)]
        out, a = [], 0
        for t in sorted(tam, reverse=True):
            out.append(ks[a:a + t]); a += t
        return out
    cima = partir(antes)
    linha_chave = [idx[kpos]] + (depois if len(depois) <= 2 else [])
    if cima and len(cima[-1]) <= 2 and len(linha_chave) == 1:
        linha_chave = cima.pop() + linha_chave
    linhas = cima + [linha_chave] + (partir(depois) if len(depois) > 2 else [])
    blocos.append({"linhas": linhas, "chave": [idx[kpos]]})
    usados.update(idx)
blocos.sort(key=lambda b: b["linhas"][0][0])
for b in blocos:
    print(f"[{b['linhas'][0][0]:3d}] " + " / ".join(" ".join(("*" + words[k]["word"] + "*") if k in b["chave"] else words[k]["word"]
                                                            for k in l) for l in b["linhas"]))
json.dump({"blocos": blocos}, open(os.path.join(pasta, "blocos.json"), "w"), ensure_ascii=False, indent=1)
