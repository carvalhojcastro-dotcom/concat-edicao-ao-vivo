"""Plano de legendas (legendas_estilos.py) a partir das palavras do corte.

Uso: plano_auto.py <dir do corte> [ajustes.json]
- words.json do corte é limpo (sem ponto final) e gravado de volta como words_leg.json;
- frases de até 4 palavras / 24 caracteres, quebrando em pontuação, pausa > 0,3 s e troca de locutor;
- todas em `linha` (branco), centro 0,67, sombra_suave;
- ajustes.json: {"<n da frase>": {"preset": "escada", "linhas": [...], "destaque": "#f4c430"}, ...,
  "_juntar": [[n, m], ...]} — o texto das linhas precisa ter as mesmas palavras da frase (pode marcar
  *chave*, palavra^g, palavra{#hex}).
Imprime as frases numeradas para revisar. Grava plano.json.
"""
import json, os, re, sys

pasta = sys.argv[1]
words = json.load(open(os.path.join(pasta, "words.json")))
corr = {}
if os.path.exists(os.path.join(pasta, "correcoes.json")):
    corr = json.load(open(os.path.join(pasta, "correcoes.json")))   # {"indice": "palavra certa"}
for i, w in enumerate(words):
    t = corr.get(str(i), w["word"]).strip()
    t = re.sub(r"\.+$", "", t) if not t.endswith("...") else t.rstrip(".")
    w["leg"] = t
# maiúsculas: 1ª palavra do vídeo, depois de ?/!, nomes próprios e siglas; o resto minúsculo
PROPRIOS = set("Rafael Rafa Bruno Ive Simone Barra Recreio Brasil Deus Cushing Fantástico Bia Isabela Isa Caxias TikTok Farah Rio Janeiro São Paulo Nordeste Minas Gerais Moçambique Angola Elon Musk Paula Paulinha".split())
for i, w in enumerate(words):
    t = w["leg"]
    nome = re.sub(r"[^\wÀ-ú]", "", t)
    if not nome:
        continue
    sigla = len(nome) >= 2 and nome.isupper()
    if i == 0 or re.search(r"[?!]$", words[i - 1]["leg"]):
        t = t[0].upper() + t[1:]
    elif nome not in PROPRIOS and not sigla:
        t = t[0].lower() + t[1:]
    w["leg"] = t
json.dump([{"word": w["leg"], "start": w["start"], "end": w["end"]} for w in words],
          open(os.path.join(pasta, "words_leg.json"), "w"), ensure_ascii=False, indent=1)

LIGA = set("a o as os um uma uns umas de do da dos das em no na nos nas para pra pro com por pelo pela e que se eu você ele ela me te lhe seu sua meu minha mas é não".split())
aj = json.load(open(sys.argv[2])) if len(sys.argv) > 2 and os.path.exists(sys.argv[2]) else []
comps = {c["de"]: c for c in aj}
def n_pal(c):
    return sum(len(l.split()) for l in c["linhas"])

def dividir(idx):
    """frases de até 4 palavras / 24 caracteres; quebra em pontuação, pausa e troca de locutor."""
    out, cur = [], []
    for i in idx:
        if cur:
            ant = words[cur[-1]]
            txt = " ".join(words[k]["leg"] for k in cur + [i])
            forte = re.search(r"[.?!,;:]$", ant["word"].strip()) or words[i]["start"] - ant["end"] > 0.3 or words[i]["speaker"] != ant["speaker"]
            if forte or len(cur) >= 4 or len(txt) > 24:
                if not forte and len(cur) > 1 and words[cur[-1]]["leg"].lower().strip(",") in LIGA:
                    out.append(cur[:-1]); cur = [cur[-1]]
                else:
                    out.append(cur); cur = []
        cur.append(i)
    if cur:
        out.append(cur)
    return out

plano = {"destaque": "#ffffff", "frases": []}
i, livres = 0, []
blocos = []
while i < len(words):
    if i in comps:
        if livres:
            blocos += [("linha", f) for f in dividir(livres)]; livres = []
        c = comps[i]; blocos.append((c, list(range(i, i + n_pal(c))))); i += n_pal(c)
    else:
        livres.append(i); i += 1
if livres:
    blocos += [("linha", f) for f in dividir(livres)]
for n, (c, f) in enumerate(blocos):
    txt = " ".join(words[k]["leg"] for k in f)
    fr = {"preset": "linha", "linhas": [" ".join(words[k]["leg"] + "^m" for k in f)], "de": f[0], "centro": [0.5, 0.67], "sombra_suave": 0.6, "contorno": 0.02}
    if c != "linha":
        fr.update({k: v for k, v in c.items() if k != "de"})
        falado = [re.sub(r"[^\wà-ú]", "", words[k]["leg"].lower()) for k in f]
        escrito = [re.sub(r"[^\wà-ú]", "", re.sub(r"\{.*\}|\^\w+", "", t).lower()) for l in fr["linhas"] for t in l.split()]
        if falado != escrito:
            print(f"!! composição em {f[0]}: escrito {escrito} != falado {falado}")
    plano["frases"].append(fr)
    print(f"{n:3d} [{f[0]:3d}] {words[f[0]]['start']:6.2f} {fr['preset']:9s} {' / '.join(fr['linhas'])}")
# a última legenda nunca passa do fim do vídeo (senão o export ganha quadro preto com legenda)
cfg = json.load(open(os.path.join(pasta, "corte.json")))
nq = sum(int(round((b - a) * 30)) for a, b in cfg["segmentos"])
plano["frases"][-1]["fim"] = round(min(words[-1]["end"] + 0.6, (nq - 2) / 30), 3)
json.dump(plano, open(os.path.join(pasta, "plano.json"), "w"), ensure_ascii=False, indent=1)
dur = words[-1]["end"]
frases = blocos
print(f"{len(frases)} frases em {dur:.1f}s ({len(frases) / dur * 60:.0f}/min), {sum(1 for f in plano['frases'] if f['preset'] != 'linha')} composições")
