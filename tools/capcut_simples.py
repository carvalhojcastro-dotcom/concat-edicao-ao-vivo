#!/usr/bin/env python3
"""Estilo Simples Medicina (Dr. Leonardo Luna) num projeto do CapCut, editável: o nosso jeito (cortes, 1,05x, zoom seco
por grupos de frases com o rosto centrado, legenda palavra por palavra) mesclado com o manual da marca da Bia.

Pedido de 2026-11-05: "manter elementos da edição que já fazemos como zoom in e zoom out, acelerar em 1.05x, legendas
dinâmicas estilo reels; porém ... usar mais elementos visuais como animações e motions quando for falado de números e
informações estatísticas ... manter aquela cor de fundo nas legendas para ficar parecido com a da marca ... usar a tela
dividida para chamar mais atenção ... também faça a finalização com a marca". Referência: o vídeo de apresentação
aprovado pela Bia em 03/11/2026 (skill simples-medicina-video, seção 7).

O que entra no projeto:
  - trilha principal: o bruto original da câmera, cortado pelo reel.py cortes, a 1,05x, com a redução de ruído do próprio
    CapCut ligada (85%; pedido de 2026-11-06, no lugar do "voz limpa" do limpar_audio.py);
  - TELA CHEIA: zoom seco por grupos de frases (plano "zoom"), rosto centrado (YuNet do kit); legenda abaixo do queixo,
    nunca em cima da estampa da camiseta (regra do Dr. Leonardo: a estampa vence);
  - TELA DIVIDIDA ("painel"): o painel de dados 1080x960 em cima (simples_cenas.py) e ele embaixo (zoom 1,16, topo da
    cabeça logo abaixo da faixa marinho); a legenda passa na faixa marinho do painel;
  - TELA SÓ DE MOTION ("tela"): 1080x1920 por cima dele, sem legenda (o texto já é a fala); serve também para destacar
    o número ou a fala mais importante (as cenas de painel vão para o meio da tela cheia; feedback da Bia, 05/11/2026:
    "mesclar entre ele sozinho, ele dividindo a tela e o motion sozinho");
  - cartão de nome (PNG da marca, com a entrada Fade-in) na primeira frase;
  - legendas: blocos de até 4 palavras em Inter Bold off-white, a palavra falada em marinho sobre a pílula coral do kit
    (uma imagem atrás da palavra; trilhas "Legendas Simples ... bloco / pílula / palavra");
  - moldura da marca (trilhas "Marca ..."): arco verde em cada troca de formato (com a pausa natural de até 0,75 s antes
    da fala seguinte, a legenda some enquanto ele passa), e no fim o arco off-white emendando na vinheta, 0,5 s depois da
    última palavra (o rabo fica sem som). Arcos e vinheta feitos com o próprio código do kit (build/arco.py e
    build/vinheta.py) e conferidos com os arquivos da Bia; ficam em Broll Concat/Simples Medicina marca.
  Sem música e sem efeito sonoro na fala (manual: "sem música sob a voz e sem efeito sonoro repetitivo"); o arco verde é
  mudo, como no vídeo de referência; só o arco off-white e a vinheta têm som.

Uso:
  capcut_simples.py telas <plano.json>                 calcula a timeline e renderiza as telas (não mexe no CapCut)
  capcut_simples.py folha <plano.json>                 quadros parados de cada tela (aprovar a direção antes)
  capcut_simples.py montar <plano.json>                telas + projeto do CapCut (o CapCut precisa estar FECHADO)
  capcut_simples.py previa <plano.json> <saida.jpg> [t1,t2,...]   folha de revisão como o CapCut mostra (sem abri-lo)
  capcut_simples.py conferir <plano.json>              transcreve a fala cortada de novo e compara com as legendas
Plano (JSON):
  {"nome": "<nome do vídeo>", "trabalho": "<pasta do reel.py>", "video": "<bruto com voz limpa>",
   "projeto": "<pasta do projeto no CapCut>", "modelo": "<projeto modelo do cliente>",
   "broll_modelo": "<projeto com B-roll de foto e Fade-in>", "velocidade": 1.05, "volume": 1.0,
   "estampa": 0.56,                       (topo da estampa da camiseta, fração da altura do bruto)
   "camiseta_clara": true,                (camiseta branca/creme: o bloco da legenda em marinho, sem sombra;
                                           na camiseta escura e na faixa da tela dividida fica off-white)
   "substituir": {"monjaro": "Mounjaro"},  (correções de texto, palavra inteira, sem caixa)
   "zoom": [[i, 1.08], [i, 1.35], ...],    (índice da palavra que abre o grupo, escala; vale até o próximo)
   "telas": [{"formato": "painel"|"tela", "de": i, "ate": j, "cena": "numero", "params": {...}, "ancoras": [i, ...]}],
   "cartao": {"de": i, "ate": j}}
  Índices = palavras do words.json do reel.py cortes. Uma tela vai do começo da palavra "de" até o fim da "ate".
"""
import copy
import glob
import hashlib
import json
import os
import re
import shutil
import subprocess
import sys
import tempfile
import time
import uuid

AQUI = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, AQUI)
import numpy as np  # noqa: E402
import cv2  # noqa: E402
from fontTools.ttLib import TTFont  # noqa: E402
from PIL import Image, ImageDraw, ImageFilter, ImageFont  # noqa: E402

KIT = os.environ.get("SIMPLES_KIT", os.path.expanduser("~/Desktop/Edições/Kit de edição/Simples Medicina"))
VISTA = os.path.expanduser("~/Library/Containers/com.lemon.lvoverseas/Data")
BROLL = os.path.expanduser("~/Movies/CapCut/User Data/Broll Concat")
CAPCUT_FONTES = os.path.expanduser("~/Movies/CapCut/User Data/Fontes Concat")
NOME_TRILHA = "Legendas Simples"
W, H, PH, FPS = 1080, 1920, 960, 30
STRIP_H = 110
VEL = 1.05
SPLIT_Z = 1.30          # zoom dele na tela dividida (o kit usa 1,16 num bruto mais fechado; o da Sony é aberto)
SPLIT_GAP = 150         # px entre a divisão e o topo do rosto (o cabelo fica logo abaixo da faixa)
ALVO_Y = 0.33           # altura do rosto no zoom in (fração do quadro)
# cores da marca
MAR, VER, COR, OFF = (8, 19, 31), (30, 92, 73), (239, 148, 114), (247, 245, 241)
# legenda (manual, seção 7): Inter Bold; 66 px em tela cheia, 54 na faixa; até 4 palavras; margem de 64 px
FONTE_LEG = "Inter-Bold.otf"
LEG_CHEIA, LEG_FAIXA, LEG_MARGEM = 66, 54, 64
LEG_QUEIXO = 150        # centro da legenda abaixo do queixo (px)
MAX_PALAVRAS = 4
K_CAPCUT = 0.0032       # altura typo da fonte = tamanho x K x altura do quadro (medido; capcut_legendas_ig.py)
# sombra da legenda em tela cheia: a nossa (35%, indefinição 8%, distância 3, -90°)
SOMBRA = dict(alpha=0.3534, difuso=0.0128, distancia=3.0, angulo=-90)
# pílula da palavra falada: o retângulo coral do kit (build/comp.py, caption): 8 px além da palavra dos lados, de 4 px
# abaixo do topo da linha até 2 px acima da base dela, cantos de 11 px, texto marinho por cima. O fundo do próprio texto
# do CapCut não chega nisso (tem folga mínima: saía com 1,8 em de altura e 0,45 em de folga, cobrindo a letra vizinha;
# feedback da Bia de 05/11/2026: "a legenda ficou um pouquinho diferente"), por isso a pílula é uma imagem atrás da palavra.
PILULA = dict(folga=8, topo=4, base=2, raio=11)
# moldura da marca (kit: arco verde nas trocas de tela, arco off-white + vinheta no fim), feita com o próprio código do
# kit (build/arco.py e build/vinheta.py; conferidos quadro a quadro com os arquivos que a Bia mandou pelo WhatsApp)
MARCA = os.path.join(BROLL, "Simples Medicina marca")
ARCO_VERDE, ARCO_OFF = "SIMPLES_transicao_arco_verde_alpha_4k.mov", "SIMPLES_transicao_arco_offwhite_alpha_4k.mov"
SOM_ARCO_OFF, VINHETA, SOM_VINHETA = "SIMPLES_transicao_arco_offwhite.wav", "SIMPLES_vinheta_4k.mp4", "SIMPLES_vinheta_som.wav"
ARCO_DUR, VIN_DUR = 1.1, 3.6
COBRE_VERDE = 0.55      # s do arquivo do arco verde até ele cobrir a tela inteira (quadros 16-17): a troca cai aí
COBRE_OFF = 0.80        # arco off-white: cobre no quadro 24 e emenda na vinheta (o som dele começa junto)
PAUSA_TROCA = 0.75      # s de pausa do bruto mantidos antes da 1ª palavra depois de uma troca com arco (o kit põe 0,75 s)
ESCONDE = (0.55, 0.50)  # legenda escondida enquanto o arco atravessa a tela (kit: -0,55 < t - troca < 0,5)
FIM_DEPOIS = 0.50       # a vinheta entra 0,5 s depois da última palavra (kit: end_start = voice_end + 0,50), sem voz
ABREV = {"dr.", "dra.", "sr.", "sra.", "prof.", "profa.", "etc."}

novo_id = lambda: __import__("uuid").uuid4().__str__().upper()  # noqa: E731
us = lambda s: int(round(s * 1e6))  # noqa: E731
quadro30 = lambda s: round(s * FPS) / FPS  # noqa: E731


def vista(p):
    """Caminho como o CapCut (sandbox) vê um arquivo de ~/Movies/CapCut/User Data."""
    return p.replace(os.path.expanduser("~/Movies"), VISTA + "/Movies", 1)


# ---------------------------------------------------------------- texto
def ponto_final(t):
    t = t.strip()
    return t.endswith(".") and not t.endswith("..") and t.lower() not in ABREV


def carregar(arq):
    P = json.load(open(arq, encoding="utf-8"))
    P["_arq"] = os.path.abspath(arq)
    P.setdefault("velocidade", VEL)
    P["_trab"] = os.path.join(os.path.dirname(P["_arq"]), "simples_" + re.sub(r"\W+", "_", P["nome"])[:40])
    os.makedirs(P["_trab"], exist_ok=True)
    return P


def palavras(P):
    """words.json do reel.py (tempos do bruto), com as correções do plano, sem ponto final visível (maiúscula depois
    dele, como nas nossas legendas) e o texto pronto para a tela."""
    ws = json.load(open(os.path.join(P["trabalho"], "words.json"), encoding="utf-8"))
    sub = {k.lower(): v for k, v in P.get("substituir", {}).items()}
    out = []
    for k, w in enumerate(ws):
        t = w["word"].strip()
        m = re.match(r"^(\W*)(.*?)(\W*)$", t)
        if m and m.group(2).lower() in sub:
            t = m.group(1) + sub[m.group(2).lower()] + m.group(3)
        if str(k) in P.get("troca", {}):
            t = P["troca"][str(k)]
        out.append(dict(w, word=t, i=k))
    for k, w in enumerate(out):     # "9" "%" e "2" ",5" (o Whisper separa) viram "9%" e "2,5"; troca vazia some
        if k and (re.match(r"^(%|,\d)", w["word"]) or not w["word"]):
            dono = next(x for x in reversed(out[:k]) if not x.get("oculta"))
            dono["word"] += w["word"]
            dono["end"] = max(dono["end"], w["end"])
            w["oculta"] = True
    for k, w in enumerate(out):
        if k and ponto_final(out[k - 1]["word"]) and w["word"]:
            w["word"] = w["word"][0].upper() + w["word"][1:]
        w["vis"] = w["word"][:-1] if ponto_final(w["word"]) else w["word"]
        w["fecha"] = bool(re.search(r"[,.?!:;]$", w["word"]))
    return out


# ---------------------------------------------------------------- pedaços e timeline
VOZ_BAIXA = -42.0      # dB (RMS do bruto a -25 LUFS): rabo de palavra dito baixinho, acima de respiração e eco


def pausas_sem_fala(P, cortes):
    """O corte de pausa do reel.py (abaixo de -36 dB) às vezes comia o fim de palavra dito baixinho ("calculadoras de
    ris-co", -37 a -49 dB, vídeo 12). Em cada pausa de dentro de um trecho, o rabo da palavra colado na fala (acima do
    ruído de fundo + 10 dB) fica, até 0,35 s, e o começo suave da palavra seguinte, até 0,12 s; a respiração no meio da
    pausa continua cortada (EDICAO.md: pausas cortadas com respiração incluída). Pausa que fica curta não é cortada."""
    rms = np.load(os.path.join(P["trabalho"], "rms.npy"))
    trechos = json.load(open(os.path.join(P["trabalho"], "keep.json")))
    J = 0.025
    limiar = float(np.percentile(rms, 10)) + 10.0
    out = []
    for a, b in cortes:
        if not any(s - 1e-3 <= a and b <= e + 1e-3 for s, e in trechos):    # troca de tomada: fica como está
            out.append([a, b])
            continue
        i, fim = int(round(a / J)), int(round(b / J))
        k = i
        while k < fim and k < len(rms) and rms[k] > limiar and (k - i) * J < 0.35:
            k += 1
        # só é rabo de palavra se tiver voz (pico acima de -42 dB, como os -37 do "risco"); respiração e eco ficam abaixo
        na = a if k == i or max(rms[i:k]) < VOZ_BAIXA else k * J + 0.03
        m = fim - 1
        while m > k and rms[m] > limiar and (fim - 1 - m) * J < 0.12:
            m -= 1
        nb = b if m == fim - 1 or max(rms[m + 1:fim]) < VOZ_BAIXA else (m + 1) * J - 0.03
        if nb - na >= 0.15:
            out.append([round(na, 4), round(nb, 4)])
    return out


def fim_do_trecho(P):
    return max(e for _, e in json.load(open(os.path.join(P["trabalho"], "keep.json"))))


GAP_TELAS = 2.2         # s do bruto: duas telas separadas por até isso (umas poucas palavras) ficam emendadas


def emendas(P, ws):
    """Primeira palavra de cada tela: a dela, ou a logo depois da tela anterior quando entre as duas só há uma ou duas
    palavras (sem voltar para ele por meio segundo, com dois arcos seguidos; um arco só, na troca)."""
    telas = P.get("telas", [])
    ini = []
    for t in telas:
        u = next((u for u in telas if u["ate"] < t["de"] and ws[t["de"]]["start"] - ws[u["ate"]]["end"] <= GAP_TELAS), None)
        ini.append(u["ate"] + 1 if u else t["de"])
    return ini


def trocas(P, ws):
    """Palavras em que o formato muda (ele sozinho, tela dividida, motion sozinho): ali passa o arco verde. O que vem
    depois do último trecho (bastidor) não conta."""
    telas = P.get("telas", [])
    fim = fim_do_trecho(P)
    ini = emendas(P, ws)
    out = set()
    for n, t in enumerate(telas):
        if next((u["formato"] for u in telas if u["ate"] == ini[n] - 1), "cheia") != t["formato"] and ini[n] > 0:
            out.add(ini[n])
        prox = next((telas[m]["formato"] for m in range(len(telas)) if ini[m] == t["ate"] + 1), "cheia")
        if prox != t["formato"] and t["ate"] + 1 < len(ws) and ws[t["ate"] + 1]["start"] < fim:
            out.add(t["ate"] + 1)
    return sorted(out)


def pedacos(P, ws):
    cortes = pausas_sem_fala(P, json.load(open(os.path.join(P["trabalho"], "cortes.json"))))
    dur = json.load(open(os.path.join(P["trabalho"], "info.json")))["duracao"]
    # o Whisper às vezes cola o começo de uma palavra na anterior e a pausa cortada fica dentro dela ("quilos. Com", vídeo
    # 5): nas palavras que abrem ou fecham uma tela, o começo dito de fato é o fim desse corte
    for i in {t["de"] for t in P.get("telas", [])} | {t["ate"] + 1 for t in P.get("telas", []) if t["ate"] + 1 < len(ws)}:
        s = ws[i]["start"]
        for a, b in cortes:
            if s - 0.02 <= a < min(ws[i]["end"], s + 0.7) and b < ws[i]["end"]:
                ws[i]["start"] = round(b, 4)
                break
    # troca de tela com arco: fica a pausa natural antes da 1ª palavra (até 0,75 s, como o kit) e a troca cai nela, a 1/3
    # do fim; o arco passa quase todo no silêncio e a legenda some menos
    bordas = {}
    for i in trocas(P, ws):
        a0, b0 = ws[i - 1]["end"], ws[i]["start"]
        L = max(0.0, min(PAUSA_TROCA, b0 - a0))
        novo = []
        for a, b in cortes:
            if b <= b0 - L or a >= b0:
                novo.append([a, b])
            elif min(b, b0 - L) - a >= 0.15:
                novo.append([a, round(min(b, b0 - L), 4)])
        cortes = novo
        bordas[i] = b0 - L / 3 if L > 0.3 else b0 - 0.04
    keep, prev = [], 0.0
    for a, b in cortes:
        if a - prev > 0.05:
            keep.append([prev, a])
        prev = b
    if dur - prev > 0.05:
        keep.append([prev, dur])
    # fim: o vídeo segue 0,5 s depois da última palavra (o arco off-white sobe nele), sem som, e aí entra a vinheta
    fim_trecho = fim_do_trecho(P)       # o bastidor depois do último trecho fica fora
    fim_voz = max(w["end"] for w in ws if w["word"] and not w.get("oculta") and w["start"] < fim_trecho)
    keep = [[s, e] for s, e in keep if s < fim_voz]
    keep[-1][1] = round(min(dur, fim_voz + FIM_DEPOIS * P["velocidade"] + 0.05), 4)
    # divisões: começo de cada grupo de zoom, começo e fim de cada tela (no começo da palavra, 0,04 s antes; com arco, na
    # pausa) e o começo do rabo sem som
    marcas = [ws[i]["start"] - 0.04 for i, _ in P.get("zoom", [])[1:]] + [fim_voz + 0.06]
    ini = emendas(P, ws) + ([P["cartao"]["de"]] if P.get("cartao") else [])
    for n, tl in enumerate(P.get("telas", []) + ([P["cartao"]] if P.get("cartao") else [])):
        marcas.append(bordas.get(ini[n], ws[ini[n]]["start"] - 0.04))
        if tl["ate"] + 1 < len(ws):
            marcas.append(bordas.get(tl["ate"] + 1, ws[tl["ate"] + 1]["start"] - 0.04))
    for t in sorted(marcas):
        for k, (s, e) in enumerate(keep):
            if s + 0.2 < t < e - 0.2:
                keep[k:k + 1] = [[s, t], [t, e]]
                break
    vel = P["velocidade"]
    out, ini = [], 0.0
    for s, e in keep:
        d = round((e - s) / vel * FPS) / FPS
        out.append(dict(fonte=round(s, 4), fonte_dur=round(e - s, 4), ini=round(ini, 6), dur=d, mudo=s >= fim_voz + 0.05))
        ini += d
    return out


def no_pedaco(ps, t):
    """Pedaço que contém o instante t do bruto (ou o primeiro depois dele, se t caiu num corte)."""
    for k, p in enumerate(ps):
        if t < p["fonte"] + p["fonte_dur"] - 1e-6:
            return k
    return len(ps) - 1


def ate_pedaco(ps, t):
    """Último pedaço que começa antes do instante t do bruto (o fim de uma tela que cai numa pausa cortada)."""
    k = 0
    for j, p in enumerate(ps):
        if p["fonte"] < t:
            k = j
    return k


def tl(ps, t):
    """Instante do bruto -> timeline (num corte, vai para o começo do pedaço seguinte)."""
    k = no_pedaco(ps, t)
    p = ps[k]
    return p["ini"] + max(0.0, min(t - p["fonte"], p["fonte_dur"])) / P_VEL[0]


P_VEL = [VEL]


def janelas(P, ws, ps):
    """Para cada pedaço: modo ("cheia", "painel", "tela"), índice da tela e grupo de zoom."""
    modo = [("cheia", None)] * len(ps)
    fim = fim_do_trecho(P)
    ultima = max(i for i, w in enumerate(ws) if w["word"] and not w.get("oculta") and w["start"] < fim)
    ini = emendas(P, ws)
    for n, t in enumerate(P.get("telas", [])):
        a = no_pedaco(ps, ws[ini[n]]["start"])
        b = max(a, ate_pedaco(ps, ws[t["ate"]]["end"] - 0.05))
        if t["ate"] + 1 < len(ws) and ws[t["ate"] + 1]["start"] < fim:     # a pausa mantida até o arco cobrir é dela
            b = max(b, no_pedaco(ps, ws[t["ate"] + 1]["start"]) - 1)
        if t["ate"] >= ultima:      # a tela fecha a fala: segue no rabo até a vinheta (sem voltar para ele)
            b = len(ps) - 1
        for k in range(a, b + 1):
            modo[k] = (t["formato"], n)
        t["_pk"] = (a, b)
    grupos = sorted(P.get("zoom", [[0, 1.08]]))
    gk = [0] * len(ps)
    for g, (i, _) in enumerate(grupos):
        a = no_pedaco(ps, ws[i]["start"])
        for k in range(a, len(ps)):
            gk[k] = g
    return modo, grupos, gk


# ---------------------------------------------------------------- rosto (YuNet do kit)
_det = []


def estampa_quadro(img, fx, fchin, clara):
    """Topo da estampa da camiseta ("SIMPLES MEDICINA") abaixo do queixo: a 1ª faixa de linhas em que as letras (claras na
    camiseta verde, escuras na creme) ocupam boa parte da largura do peito. O microfone de lapela é pequeno e não conta.
    Ele anda para a frente e para trás: a estampa medida num quadro só deixava a legenda em cima dela (vídeo 11)."""
    hsv = cv2.cvtColor(img, cv2.COLOR_BGR2HSV)
    h, w = img.shape[:2]
    x0, x1 = max(0, int((fx - 0.17) * w)), min(w, int((fx + 0.17) * w))
    y0, y1 = int((fchin + 0.05) * h), int(min(0.95, fchin + 0.40) * h)     # a estampa nunca encosta no queixo
    if y1 - y0 < 10 or x1 - x0 < 20:
        return None
    reg = hsv[y0:y1, x0:x1]
    letra = (reg[..., 2] < 95) if clara else ((reg[..., 2] > 200) & (reg[..., 1] < 45))
    fr = np.convolve(letra.mean(1), np.ones(5) / 5, mode="same")
    # as letras se espalham pelo peito; pescoço, mão e microfone são manchas estreitas
    larg = np.array([(np.nonzero(r)[0][-1] - np.nonzero(r)[0][0]) / r.size if r.any() else 0.0 for r in letra])
    larg = np.convolve(larg, np.ones(5) / 5, mode="same")
    acima = np.nonzero((fr > 0.16) & (larg > 0.5))[0]
    return float((y0 + acima[0]) / h) if len(acima) else None


def rosto_quadro(video, t, tmp, clara=False):
    png = os.path.join(tmp, f"r{t:.3f}.png")
    subprocess.run(["ffmpeg", "-v", "error", "-y", "-ss", f"{t:.3f}", "-i", video, "-frames:v", "1", "-vf", "scale=540:960", png], check=True)
    img = cv2.imread(png)
    if not _det:
        _det.append(cv2.FaceDetectorYN.create(os.path.join(KIT, "kit", "yunet.onnx"), "", (540, 960), 0.6))
    _det[0].setInputSize((img.shape[1], img.shape[0]))
    _, f = _det[0].detect(img)
    if f is None or not len(f):
        return None
    x, y, w, h = max(f, key=lambda r: r[2] * r[3])[:4]
    fx, ftop, fchin = float((x + w / 2) / 540), float(y / 960), float((y + h) / 960)
    return fx, ftop, fchin, estampa_quadro(img, fx, fchin, clara), 2     # centro x, topo, queixo, estampa (frações), versão


def rostos(P, ps, gk, modo):
    """Mediana do rosto por grupo (tela cheia) e por tela dividida: enquadramento estável dentro do grupo."""
    cache_arq = os.path.join(P["_trab"], "rostos.json")
    cache = json.load(open(cache_arq)) if os.path.exists(cache_arq) else {}
    tmp = tempfile.mkdtemp()
    chaves = {}
    for k, p in enumerate(ps):
        ch = f"t{modo[k][1]}" if modo[k][0] == "painel" else f"g{gk[k]}"
        chaves.setdefault(ch, []).append(k)
    out = {}
    for ch, ks in chaves.items():
        ts = []
        for k in ks:
            p = ps[k]
            ts += [p["fonte"] + p["fonte_dur"] * f for f in ((0.5,) if p["fonte_dur"] < 1.0 else (0.3, 0.7))]
        if len(ts) > 6:
            ts = [ts[int(i * (len(ts) - 1) / 5)] for i in range(6)]
        rs = []
        for t in ts:
            c = f"{t:.2f}"
            if c not in cache or (cache[c] and len(cache[c]) < 5):
                cache[c] = rosto_quadro(P["video"], t, tmp, P.get("camiseta_clara", False))
            if cache[c]:
                rs.append(cache[c])
        m = tuple(np.median(np.array([r[:3] for r in rs]), 0)) if rs else (0.5, 0.25, 0.39)
        est = [r[3] for r in rs if len(r) > 3 and r[3] is not None]
        m = m + (float(np.min(est)) if est else None,)     # a estampa mais alta do grupo: a legenda fica acima dela sempre
        xs = [r[0] for r in rs]
        for k in ks:                                         # quanto ele anda para os lados: começo, meio e fim de cada pedaço
            p = ps[k]
            for fr in (0.15, 0.5, 0.85):
                c = f"{p['fonte'] + p['fonte_dur'] * fr:.2f}"
                if c not in cache or (cache[c] and len(cache[c]) < 5):
                    cache[c] = rosto_quadro(P["video"], float(c), tmp, P.get("camiseta_clara", False))
                if cache[c]:
                    xs.append(cache[c][0])
                    if len(cache[c]) > 3 and cache[c][3] is not None:
                        est.append(cache[c][3])
        xs = xs or [m[0]]
        # a estampa mais alta com as amostras de todos os pedaços (com poucas, a legenda encostava no "SIMPLES" no vídeo 2)
        m = m[:3] + (float(np.min(est)) if est else None,) + (float(min(xs)), float(max(xs)))
        for k in ks:
            out[k] = m
    json.dump(cache, open(cache_arq, "w"))
    return out


def enquadrar(P, ps, modo, grupos, gk, rs):
    """Escala, posição do CapCut (metade do quadro; y para cima) e a linha da legenda de cada pedaço."""
    for k, p in enumerate(ps):
        fx, ftop, fchin, est = rs[k][:4]
        xmin, xmax = rs[k][4:6] if len(rs[k]) > 5 else (fx, fx)
        if est is None:
            est = P.get("estampa", 0.56)
        m = modo[k][0]
        if m == "painel":
            s = P.get("zoom_painel", SPLIT_Z)
            tx = -2 * (fx - 0.5) * s
            ty = ((ftop - 0.5) * H * s - SPLIT_GAP) / PH
            p["leg"] = ("faixa", PH - STRIP_H / 2)
        else:
            if m == "tela" and k:        # coberto pela tela de motion: fica o enquadramento de antes
                s, tx, ty = ps[k - 1]["escala"], ps[k - 1]["tx"], ps[k - 1]["ty"]
            else:
                s = grupos[gk[k]][1]
                if abs(fx - 0.5) > 0.03:     # fora do centro: o zoom sobe até dar folga para centralizar (máx. 1,40)
                    s = max(s, min(1.40, 1 / (1 - 2 * abs(fx - 0.5))))
                # ele anda para os lados no grupo: o zoom desce até o rosto nunca passar de 30% do centro (o rosto saía
                # cortado na borda no vídeo 2, num trecho que a tela dividida cobria antes, 05/11/2026)
                amp = max(xmax - fx, fx - xmin)
                if amp * s > 0.30:
                    s = max(1.0, 0.30 / amp)
                tx = -2 * (fx - 0.5) * s
                fy = (ftop + fchin) / 2
                alvo = fy if s < 1.2 else ALVO_Y
                ty = 2 * (0.5 + (fy - 0.5) * s - alvo)
                folga = s - 1
                tx, ty = max(-folga, min(folga, tx)), max(-folga, min(folga, ty))
            queixo = (0.5 + (fchin - 0.5) * s - ty / 2) * H
            estampa = (0.5 + (est - 0.5) * s - ty / 2) * H
            y = min(queixo + LEG_QUEIXO, estampa - 62, 1500)    # a estampa vence (regra do Dr. Leonardo)
            if m == "cheia" and y < queixo + 70:
                print(f"  aviso: pedaço em {p['ini']:.2f}s sem espaço entre o queixo ({queixo:.0f}) e a estampa ({estampa:.0f}): suba o zoom")
            p["leg"] = ("cheia" if m == "cheia" else "nenhuma", max(y, queixo + 70))
        folga = s - 1
        p["escala"], p["tx"], p["ty"] = round(s, 4), round(max(-folga, min(folga, tx)), 4), round(ty, 4)
        p["modo"], p["tela"] = m, modo[k][1]


# ---------------------------------------------------------------- telas
def montar_telas(P, ws, ps):
    """Tempo de cada tela na timeline e as âncoras (palavras) relativas a ela."""
    cenas = []
    for n, t in enumerate(P.get("telas", [])):
        a, b = t["_pk"]
        ini = ps[a]["ini"]
        fim = ps[b]["ini"] + ps[b]["dur"]
        anc = [round(tl(ps, ws[i]["start"]) - ini, 3) if i is not None else None for i in t.get("ancoras", [])]
        cid = f"{n + 1:02d} - {t['cena']}"
        cenas.append(dict(id=cid, formato=t["formato"], cena=t["cena"], dur=round(fim - ini, 4), ancoras=anc,
                          params=t.get("params", {}), _ini=ini, _fim=fim))
    return cenas


def versao(cena):
    """Assinatura da tela: o conteúdo, o código da cena e das funções do simples_cenas.py que ela chama, e o kit (mudou o
    desenho dela, muda o arquivo; mudar outra cena não obriga a renderizar esta de novo)."""
    import inspect
    import types
    import simples_cenas as SC
    h = hashlib.md5(json.dumps(cena, sort_keys=True, ensure_ascii=False).encode())
    vistos, fila = set(), [SC.CENAS[cena["cena"]], SC.quadro]
    while fila:
        f = fila.pop()
        if f.__name__ in vistos:
            continue
        vistos.add(f.__name__)
        h.update(inspect.getsource(f).encode())
        for nome in f.__code__.co_names:
            g = getattr(SC, nome, None)
            if isinstance(g, types.FunctionType) and g.__module__ == SC.__name__:
                fila.append(g)
    for arq in (os.path.join(KIT, "kit", "motion.py"), os.path.join(KIT, "kit", "marca.py"), os.path.join(KIT, "kit", "components.py")):
        h.update(open(arq, "rb").read())
    return h.hexdigest()[:8]


def renderizar_telas(P, cenas):
    import simples_cenas as SC
    pasta = os.path.join(BROLL, P["nome"][:50].strip())
    os.makedirs(pasta, exist_ok=True)
    for c in cenas:
        sem = {k: v for k, v in c.items() if not k.startswith("_")}
        c["_arq"] = os.path.join(pasta, f"{c['id']} {versao(sem)}.mp4")   # nome novo a cada mudança: o CapCut não relê o mesmo nome
        if not os.path.exists(c["_arq"]):
            for velho in glob.glob(os.path.join(pasta, f"{c['id']} *.mp4")):
                os.remove(velho)
            n = SC.renderizar(sem, c["_arq"])
            print(f"  tela {c['id']}: {n} quadros")
    return pasta


def cartao_png(P, pasta):
    """Cartão de nome da marca (kit: marca.name_card), parado e inteiro, num PNG 1080x1920 transparente."""
    arq = os.path.join(pasta, "cartao de nome.png")
    if os.path.exists(arq):
        return arq
    import simples_cenas as SC
    rgba = SC.KM.render_rgba(lambda c, tt: SC.M.name_card(c, tt, 99.0, y=P.get("cartao", {}).get("y", 1470)), 2.0, W, H, sub=1)
    a = rgba[..., 3:4]
    rgb = np.where(a > 1e-4, rgba[..., :3] / np.maximum(a, 1e-4), 0)
    Image.fromarray(np.clip(np.concatenate([rgb, a], 2) * 255, 0, 255).astype(np.uint8)).save(arq)
    return arq


# ---------------------------------------------------------------- legendas
_f = {}


def fonte_px(px):
    k = int(round(px * 4))
    if k not in _f:
        _f[k] = ImageFont.truetype(os.path.join(KIT, "fonts", FONTE_LEG), size=k / 4)
    return _f[k]


def blocos(ws, ps, P):
    """Blocos de até 4 palavras: quebram sempre no fim da frase (. ? !), na vírgula com 2 palavras ou mais, numa pausa
    longa e em toda troca de tela ou de grupo de zoom (a legenda não pula de lugar no meio). Nunca um bloco de 1
    palavra: junta ao anterior da mesma frase e do mesmo lugar."""
    def lugar(w):
        k = no_pedaco(ps, w["start"])
        return (ps[k]["modo"], ps[k].get("tela"), ps[k]["leg"])
    fim_frase = lambda w: bool(re.search(r"[.?!]$", w["word"])) and w["word"].lower() not in ABREV  # noqa: E731
    saida, cur = [], []
    ws = [w for w in ws if not w.get("oculta")]
    for k, w in enumerate(ws):
        if cur and (lugar(w) != lugar(cur[0]) or w["start"] - cur[-1]["end"] > 0.6):
            saida.append(cur)
            cur = []
        cur.append(w)
        if len(cur) >= MAX_PALAVRAS or fim_frase(w) or (w["fecha"] and len(cur) >= 2):
            saida.append(cur)
            cur = []
    if cur:
        saida.append(cur)
    juntos = []
    for b in saida:
        ant = juntos[-1] if juntos else None
        if len(b) == 1 and ant and lugar(ant[0]) == lugar(b[0]) and not fim_frase(ant[-1]) and b[0]["start"] - ant[-1]["end"] < 0.6:
            juntos[-1] = ant + b
        else:
            juntos.append(b)
    return [(b, lugar(b[0])) for b in juntos]


def legendas(P, ws, ps):
    """Itens de texto: o bloco off-white e, por cima, a palavra falada em marinho sobre a pílula coral (uma imagem com as
    medidas do kit, posta atrás da palavra). Some enquanto o arco verde atravessa a tela."""
    itens = []
    bs = blocos(ws, ps, P)
    asc, desc = metricas()
    for n, (b, (modo, _, (tipo, cy))) in enumerate(bs):
        if modo == "tela" or tipo == "nenhuma":
            continue
        em = LEG_CHEIA if tipo == "cheia" else LEG_FAIXA
        txt = " ".join(w["vis"] for w in b)
        f = fonte_px(em)
        larg = f.getlength(txt)
        maxw = W - 2 * LEG_MARGEM - 32
        if larg > maxw:
            em *= maxw / larg
            f = fonte_px(em)
            larg = f.getlength(txt)
        ini = max(tl(ps, b[0]["start"]) - 0.03, ps[no_pedaco(ps, b[0]["start"])]["ini"])
        prox = bs[n + 1][0][0] if n + 1 < len(bs) else None
        fim = tl(ps, b[-1]["end"]) + 0.14
        if prox is not None:      # emenda no próximo bloco sem sobrepor (o próximo entra 0,03 s antes da palavra)
            fim = min(max(fim, tl(ps, prox["start"]) - 0.03), tl(ps, b[-1]["end"]) + 0.45, tl(ps, prox["start"]) - 0.03)
        x0 = W / 2 - larg / 2
        clara = tipo == "cheia" and P.get("camiseta_clara")
        itens.append(dict(texto=txt, ini=ini, fim=fim, cx=0.5, cy=cy, em=em, cor=MAR if clara else OFF,
                          sombra=tipo == "cheia" and not clara, fundo=None, camada=0))
        pref = ""
        base = cy + ((asc - desc) / 2 + 0.018) * em        # linha de base do texto do CapCut (medida)
        for j, w in enumerate(b):
            a0 = tl(ps, w["start"]) - 0.02
            a1 = tl(ps, b[j + 1]["start"]) - 0.02 if j + 1 < len(b) else fim
            xw = x0 + f.getlength(pref)
            ww = f.getlength(w["vis"])
            pil = dict(x0=xw - PILULA["folga"], x1=xw + ww + PILULA["folga"], y0=base - asc * em + PILULA["topo"],
                       y1=base + desc * em - PILULA["base"])
            itens.append(dict(texto=w["vis"], ini=max(a0, ini), fim=a1, cx=(xw + ww / 2) / W, cy=cy, em=em, cor=MAR, sombra=False,
                              fundo=None, pilula=pil, camada=1))
            pref += w["vis"] + " "
    for h in P.get("_trocas", []):           # o arco atravessa a tela: a legenda sai e volta depois dele
        h0, h1 = h - ESCONDE[0], h + ESCONDE[1]
        for it in itens:
            if it["ini"] < h1 and it["fim"] > h0:
                if it["ini"] >= h0:
                    it["ini"] = h1
                else:
                    it["fim"] = h0
    for it in itens:
        it["ini"], it["fim"] = quadro30(it["ini"]), quadro30(it["fim"])
    return [it for it in itens if it["fim"] - it["ini"] >= 1 / FPS - 1e-6]


def fonte_capcut():
    os.makedirs(CAPCUT_FONTES, exist_ok=True)
    dst = os.path.join(CAPCUT_FONTES, FONTE_LEG)
    if not os.path.exists(dst):
        shutil.copy2(os.path.join(KIT, "fonts", FONTE_LEG), dst)
    return vista(dst)


def metricas():
    t = TTFont(os.path.join(KIT, "fonts", FONTE_LEG))
    o, u = t["OS/2"], t["head"].unitsPerEm
    return o.sTypoAscender / u, -o.sTypoDescender / u


def hexa(c):
    return "#%02X%02X%02X" % c


def texto_capcut(it, modelo, render_index, caminho):
    asc, desc = metricas()
    tamanho = round(it["em"] * (asc + desc) / (K_CAPCUT * H), 3)
    cor = [round(v / 255, 4) for v in it["cor"]]
    estilo = json.loads(modelo["material"]["content"])["styles"][0]
    estilo = dict(estilo, range=[0, len(it["texto"])], size=tamanho, font={"path": caminho, "id": ""},
                  fill={"content": {"solid": {"color": cor}, "render_type": "solid"}})
    estilo.pop("strokes", None)
    if it["sombra"]:
        for sh in estilo.get("shadows", []):
            sh.update(alpha=SOMBRA["alpha"], diffuse=SOMBRA["difuso"], distance=SOMBRA["distancia"], angle=SOMBRA["angulo"])
    else:
        estilo.pop("shadows", None)
    m = copy.deepcopy(modelo["material"])
    m.update(id=novo_id(), type="text", content=json.dumps({"styles": [estilo], "text": it["texto"]}, ensure_ascii=False),
             font_path=caminho, font_title="Inter Bold", font_name="", font_size=tamanho, letter_spacing=0.0,
             has_shadow=it["sombra"], shadow_alpha=SOMBRA["alpha"] if it["sombra"] else 0.0,
             shadow_smoothing=SOMBRA["difuso"] * 18 if it["sombra"] else 0.0, border_width=0.0, text_color=hexa(it["cor"]),
             alignment=1, group_id="", add_type=0, recognize_task_id="", recognize_text="", name="", line_max_width=0.98)
    if it["fundo"]:
        fd = it["fundo"]
        m.update(background_color=fd["cor"], background_alpha=1.0, background_style=1, background_round_radius=fd["raio"],
                 background_width=fd["largura"], background_height=fd["altura"], background_vertical_offset=0.0,
                 background_horizontal_offset=0.0)
    else:
        m.update(background_color="", background_alpha=1.0, background_style=0)
    # check_flag diz ao CapCut o que o texto usa: 1|2|4 sempre, 8 contorno, 16 fundo, 32 sombra. Sem o 16 o fundo não
    # aparece (a pílula sumia e o texto marinho por cima do bloco deixava só o contorno branco, 2026-11-05: "a legenda tá
    # estranha"); o headline de caixa branca da Luciana, que aparece, tem 23
    m["check_flag"] = 7 | (16 if it["fundo"] else 0) | (32 if it["sombra"] else 0)
    m.update(base_content="", words={"start_time": [], "end_time": [], "text": []})
    anim = copy.deepcopy(modelo["refs"]["material_animations"])
    anim.update(id=novo_id(), animations=[])
    s = copy.deepcopy(modelo["segmento"])
    s.update(id=novo_id(), material_id=m["id"], extra_material_refs=[anim["id"]], render_index=render_index,
             target_timerange={"start": us(it["ini"]), "duration": max(us(it["fim"]) - us(it["ini"]), 33333)},
             keyframe_refs=[], common_keyframes=[], group_id="")
    s["clip"] = {"scale": {"x": 1.0, "y": 1.0}, "rotation": 0.0, "alpha": 1.0, "flip": {"vertical": False, "horizontal": False},
                 "transform": {"x": round(2 * it["cx"] - 1, 6), "y": round(1 - 2 * it["cy"] / H, 6)}}
    return m, anim, s


# ---------------------------------------------------------------- CapCut
def alvos(pasta):
    return [p for p in [os.path.join(pasta, "draft_info.json")] + glob.glob(os.path.join(pasta, "Timelines", "*", "draft_info.json"))
            if os.path.exists(p)]


def backup(pasta, rotulo):
    copia = os.path.expanduser(f"~/Desktop/Claude Code Skills/backup-capcut/{os.path.basename(pasta)} {time.strftime('%Y-%m-%d %H%M%S')} ({rotulo})")
    for p in glob.glob(os.path.join(pasta, "*.json")) + glob.glob(os.path.join(pasta, "*.tmp")) + glob.glob(os.path.join(pasta, "Timelines", "**", "*"), recursive=True):
        if os.path.isfile(p):
            d = os.path.join(copia, os.path.relpath(p, pasta))
            os.makedirs(os.path.dirname(d), exist_ok=True)
            shutil.copy2(p, d)
    return copia


def gravar(pasta, N):
    texto = json.dumps(N, ensure_ascii=False, separators=(",", ":"))
    for p in alvos(pasta):
        open(p, "w", encoding="utf-8").write(texto)
        tmp = os.path.join(os.path.dirname(p), "template-2.tmp")
        if os.path.exists(tmp):
            open(tmp, "w", encoding="utf-8").write(texto)


def material_de(N, mid):
    for k, v in N["materials"].items():
        if isinstance(v, list):
            for m in v:
                if isinstance(m, dict) and m.get("id") == mid:
                    return k, m
    return None, None


def tirar_trilhas(N, prefixos):
    """Tira as trilhas com esses nomes e os materiais delas (rodar de novo refaz)."""
    velhas = [t for t in N["tracks"] if any(t.get("name", "").startswith(p) for p in prefixos)]
    ids = {s["material_id"] for t in velhas for s in t["segments"]} | {r for t in velhas for s in t["segments"] for r in s.get("extra_material_refs", [])}
    N["tracks"] = [t for t in N["tracks"] if t not in velhas]
    for k, v in N["materials"].items():
        if isinstance(v, list):
            N["materials"][k] = [m for m in v if not (isinstance(m, dict) and m.get("id") in ids)]


def refs_copia(N, seg, de=None):
    """Referências do segmento molde (velocidade, canal de som, tela...) copiadas com ids novos, a 1x e sem animação."""
    ids = []
    for r in seg.get("extra_material_refs", []):
        k, m = material_de(de or N, r)
        if m is None:
            continue
        m = dict(copy.deepcopy(m), id=novo_id())
        if k == "material_animations":
            m["animations"] = []
        if k == "speeds":
            m["speed"] = 1.0
        N["materials"].setdefault(k, []).append(m)
        ids.append(m["id"])
    return ids


def molde_midia(N, tipo):
    """Trilha, segmento e material de um B-roll posto pelo capcut_montar: "photo" (o cartão) ou "video" (um painel)."""
    for t in N["tracks"]:
        if t["type"] == "video" and t.get("name") == "B-roll":
            for s in t["segments"]:
                _, m = material_de(N, s["material_id"])
                if m and m.get("type") == tipo:
                    return t, s, m
    sys.exit(f"sem B-roll de {tipo} no projeto para servir de molde")


def reindexar(N):
    if N.get("render_index_track_mode_on"):
        for i, t in enumerate(N["tracks"]):
            for s in t["segments"]:
                s["track_render_index"] = i


def alocar(lista, ini, fim, criar):
    """Primeira trilha livre em ini (uma nova só quando dois se sobrepõem)."""
    livre = next((k for k, (f, _) in enumerate(lista) if f <= ini), None)
    if livre is None:
        lista.append([fim, criar(len(lista) + 1)])
        livre = len(lista) - 1
    lista[livre][0] = fim
    return lista[livre][1]


def png_pilula(pasta, w, h):
    """Retângulo coral de cantos redondos (a pílula do kit) em 2x, para ficar nítido no 4K."""
    os.makedirs(pasta, exist_ok=True)
    arq = os.path.join(pasta, f"pilula {w}x{h}.png")
    if not os.path.exists(arq):
        ss = 4
        im = Image.new("RGBA", (w * ss, h * ss), COR + (0,))
        ImageDraw.Draw(im).rounded_rectangle([0, 0, w * ss - 1, h * ss - 1], radius=PILULA["raio"] * 2 * ss, fill=COR + (255,))
        im.resize((w, h), Image.LANCZOS).save(arq)
    return arq


def foto_pilula(N, molde, it, pasta, render_index):
    """Segmento de foto (PNG coral) do tamanho e no lugar da pílula, no tempo da palavra."""
    _, s_m, m_m = molde
    p = it["pilula"]
    w2, h2 = int(round(2 * (p["x1"] - p["x0"]))), int(round(2 * (p["y1"] - p["y0"])))
    arq = png_pilula(pasta, w2, h2)
    m = dict(copy.deepcopy(m_m), id=novo_id(), path=vista(arq), width=w2, height=h2, material_name=os.path.basename(arq),
             material_id="", source=0, source_platform=0, category_id="", category_name="local", local_material_id=novo_id().lower(), md5="")
    N["materials"]["videos"].append(m)
    dur = max(us(it["fim"]) - us(it["ini"]), 33333)
    esc = (p["x1"] - p["x0"]) / W      # a foto larga entra encaixada na largura do quadro: escala = largura certa / 1080
    s = copy.deepcopy(s_m)
    s.update(id=novo_id(), material_id=m["id"], extra_material_refs=refs_copia(N, s_m), render_index=render_index,
             source_timerange={"start": 0, "duration": dur}, target_timerange={"start": us(it["ini"]), "duration": dur},
             common_keyframes=[], keyframe_refs=[], volume=1.0, speed=1.0)
    s["clip"] = dict(copy.deepcopy(s_m["clip"]), scale={"x": round(esc, 6), "y": round(esc, 6)}, rotation=0.0, alpha=1.0,
                     transform={"x": round(((p["x0"] + p["x1"]) / 2 - W / 2) / (W / 2), 6),
                                "y": round((H / 2 - (p["y0"] + p["y1"]) / 2) / (H / 2), 6)})
    s["uniform_scale"] = {"on": True, "value": 1.0}
    return s


def escrever_legendas(pasta, itens, P):
    N = json.load(open(alvos(pasta)[0], encoding="utf-8"))
    modelo = json.load(open(os.path.join(AQUI, "capcut_modelo_texto.json"), encoding="utf-8"))
    tirar_trilhas(N, [NOME_TRILHA])
    caminho = fonte_capcut()
    foto = molde_midia(N, "photo")
    pasta_pil = os.path.join(BROLL, P["nome"][:50].strip(), "pilulas")
    render = max([s.get("render_index", 0) for t in N["tracks"] for s in t["segments"]] + [0]) + 1
    trilhas = {0: [], 1: [], 2: []}      # 0 bloco (texto), 2 pílula (imagem), 1 palavra (texto marinho por cima)
    for it in sorted(itens, key=lambda i: (i["camada"], i["ini"])):
        m, anim, s = texto_capcut(it, modelo, render + (10000 if it["camada"] else 0), caminho)
        N["materials"].setdefault("texts", []).append(m)
        N["materials"].setdefault("material_animations", []).append(anim)
        ini, fim = s["target_timerange"]["start"], s["target_timerange"]["start"] + s["target_timerange"]["duration"]
        tipo = "palavra" if it["camada"] else "bloco"
        alocar(trilhas[it["camada"]], ini, fim, lambda k: dict(copy.deepcopy(modelo["trilha"]), id=novo_id(), type="text", flag=0,
                                                               name=f"{NOME_TRILHA} {tipo} {k}", is_default_name=False,
                                                               segments=[]))["segments"].append(s)
        if it.get("pilula"):
            sp = foto_pilula(N, foto, it, pasta_pil, render + 5000)
            alocar(trilhas[2], ini, fim, lambda k: dict(copy.deepcopy({kk: v for kk, v in foto[0].items() if kk != "segments"}),
                                                        id=novo_id(), name=f"{NOME_TRILHA} pílula {k}", segments=[]))["segments"].append(sp)
        render += 1
    N["tracks"] += [tr for _, tr in trilhas[0]] + [tr for _, tr in trilhas[2]] + [tr for _, tr in trilhas[1]]
    reindexar(N)
    gravar(pasta, N)
    return len(trilhas[0]) + len(trilhas[1]) + len(trilhas[2])


def escrever_marca(pasta, P, ps):
    """Moldura da marca por cima de tudo: o arco verde em cada troca de formato (mudo, como no vídeo de referência), o arco
    off-white emendando na vinheta no fim, e o som dos dois (o whoosh do arco off-white e a vinheta)."""
    N = json.load(open(alvos(pasta)[0], encoding="utf-8"))
    tirar_trilhas(N, ["Marca "])
    total = ps[-1]["ini"] + ps[-1]["dur"]
    tv, sv, mv = molde_midia(N, "video")
    render = [max([s.get("render_index", 0) for t in N["tracks"] for s in t["segments"]] + [0]) + 20000]

    def video(arq, ini, dur):
        m = dict(copy.deepcopy(mv), id=novo_id(), path=vista(arq), width=2160, height=3840, duration=us(dur),
                 material_name=os.path.basename(arq), local_material_id=novo_id().lower(), md5="")
        N["materials"]["videos"].append(m)
        s = copy.deepcopy(sv)
        s.update(id=novo_id(), material_id=m["id"], extra_material_refs=refs_copia(N, sv), render_index=render[0],
                 source_timerange={"start": 0, "duration": us(dur)}, target_timerange={"start": us(ini), "duration": us(dur)},
                 common_keyframes=[], keyframe_refs=[], volume=0.0, speed=1.0)
        s["clip"] = dict(copy.deepcopy(sv["clip"]), scale={"x": 1.0, "y": 1.0}, transform={"x": 0.0, "y": 0.0}, rotation=0.0, alpha=1.0)
        s["uniform_scale"] = {"on": True, "value": 1.0}
        render[0] += 1
        return s
    base = {k: v for k, v in tv.items() if k != "segments"}
    arcos = []
    marcas = [(os.path.join(MARCA, ARCO_VERDE), quadro30(b - COBRE_VERDE)) for b in P.get("_trocas", [])]
    marcas.append((os.path.join(MARCA, ARCO_OFF), quadro30(total - COBRE_OFF)))
    for arq, ini in marcas:
        alocar(arcos, us(ini), us(ini + ARCO_DUR), lambda k: dict(copy.deepcopy(base), id=novo_id(), name=f"Marca arcos {k}",
                                                                   segments=[]))["segments"].append(video(arq, ini, ARCO_DUR))
    vin = dict(copy.deepcopy(base), id=novo_id(), name="Marca vinheta", segments=[video(os.path.join(MARCA, VINHETA), total, VIN_DUR)])
    N["tracks"] += [t for _, t in arcos] + [vin]
    # sons: molde de áudio do projeto do B-roll, virado arquivo local (a receita do capcut_sfx.py)
    B = json.load(open(os.path.join(P["broll_modelo"], "draft_info.json"), encoding="utf-8"))
    ta = next(t for t in B["tracks"] if t["type"] == "audio" and t["segments"])
    sa = ta["segments"][0]
    _, ma = material_de(B, sa["material_id"])
    sons = []      # o whoosh e a vinheta se sobrepõem: uma trilha para cada (o CapCut separa sozinho, senão)
    for arq, em in ((os.path.join(MARCA, SOM_ARCO_OFF), quadro30(total - COBRE_OFF)), (os.path.join(MARCA, SOM_VINHETA), total)):
        dur = float(subprocess.run(["ffprobe", "-v", "error", "-show_entries", "format=duration", "-of", "csv=p=0", arq],
                                   capture_output=True, text=True).stdout)
        m = copy.deepcopy(ma)
        m.update(id=novo_id(), path=vista(arq), name=os.path.splitext(os.path.basename(arq))[0], duration=us(dur), type="extract_music",
                 category_name="local", category_id="", music_id=novo_id(), unique_id=uuid.uuid4().hex, resource_id="",
                 third_resource_id="", effect_id="", source_platform=0, wave_points=[], check_flag=1, local_material_id="",
                 copyright_limit_type="none")
        N["materials"].setdefault("audios", []).append(m)
        s = copy.deepcopy(sa)
        s.update(id=novo_id(), material_id=m["id"], extra_material_refs=refs_copia(N, sa, B),
                 source_timerange={"start": 0, "duration": us(dur)}, target_timerange={"start": us(em), "duration": us(dur)},
                 volume=1.0, speed=1.0, common_keyframes=[], keyframe_refs=[])
        alocar(sons, us(em), us(em + dur), lambda k: dict(copy.deepcopy({kk: v for kk, v in ta.items() if kk != "segments"}),
                                                          id=novo_id(), name=f"Marca sons {k}", segments=[]))["segments"].append(s)
    N["tracks"] += [t for _, t in sons]
    ajuste_doutor(N, P, total)
    N["duration"] = us(total + VIN_DUR)
    reindexar(N)
    gravar(pasta, N)
    meta = os.path.join(pasta, "draft_meta_info.json")
    if os.path.exists(meta):
        mi = json.load(open(meta, encoding="utf-8"))
        mi["tm_duration"] = us(total + VIN_DUR)
        json.dump(mi, open(meta, "w", encoding="utf-8"), ensure_ascii=False)
    return len(marcas) - 1, total + VIN_DUR


def ajuste_do_projeto(pasta):
    """A camada de ajuste de cor que o usuário pôs num projeto (trilha "adjust"): trilha, segmento, material e referências
    (brilho, contraste, saturação, nitidez, temperatura, tom, HSL)."""
    N = json.load(open(alvos(pasta)[0], encoding="utf-8"))
    for t in N["tracks"]:
        if t["type"] == "adjust" and t["segments"]:
            s = t["segments"][0]
            return dict(trilha={k: v for k, v in t.items() if k != "segments"}, segmento=s, material=material_de(N, s["material_id"]),
                        refs=[x for x in (material_de(N, r) for r in s.get("extra_material_refs", [])) if x[1]])
    return None


def ajuste_doutor(N, P, total):
    """Camada de ajuste de cor só em cima do vídeo dele (pedido de 05/11/2026: "adicione a camada de ajustes ... em cima
    apenas da camada de video doutor"): logo acima da trilha principal, embaixo das telas, legendas, arcos e vinheta, do
    começo ao fim da fala. Fica a do próprio projeto (a que o usuário ajustou nele); sem ela, uma cópia da do projeto
    "ajuste_de" do plano."""
    proprias = [t for t in N["tracks"] if t["type"] == "adjust"]
    if not proprias and P.get("ajuste_de"):
        A = ajuste_do_projeto(P["ajuste_de"])
        if not A:
            sys.exit(f"sem camada de ajuste em {P['ajuste_de']}")
        k, m = A["material"]
        m = dict(copy.deepcopy(m), id=novo_id())
        N["materials"].setdefault(k, []).append(m)
        ids = []
        for kr, mr in A["refs"]:
            mr = dict(copy.deepcopy(mr), id=novo_id())
            N["materials"].setdefault(kr, []).append(mr)
            ids.append(mr["id"])
        s = dict(copy.deepcopy(A["segmento"]), id=novo_id(), material_id=m["id"], extra_material_refs=ids)
        proprias = [dict(copy.deepcopy(A["trilha"]), id=novo_id(), segments=[s])]
    else:
        N["tracks"] = [t for t in N["tracks"] if t not in proprias]
    principal = next(i for i, t in enumerate(N["tracks"]) if t["type"] == "video")
    for t in reversed(proprias):
        N["tracks"].insert(principal + 1, t)
        if len(t["segments"]) == 1:
            t["segments"][0]["target_timerange"] = {"start": 0, "duration": us(total)}
    return len(proprias)


def limpar_extras(pasta):
    """Antes do capcut_montar: tira as legendas, as pílulas e a moldura de uma montagem anterior (ele estica trilhas de um
    segmento só até o fim do vídeo); elas são refeitas depois."""
    N = json.load(open(alvos(pasta)[0], encoding="utf-8"))
    tirar_trilhas(N, [NOME_TRILHA, "Marca "])
    reindexar(N)
    gravar(pasta, N)


def ruido_capcut(pasta, ligado=True):
    """Redução de ruído do próprio CapCut nos pedaços dele (85%, a do modelo). Pedido de 2026-11-06: "gostaria que usasse
    os arquivos originais mas adicionasse a redução de ruído do proprio capcut em todos eles" (antes era o "voz limpa"
    do DeepFilterNet com ela desligada). Com "ruido_capcut": false no plano, ela fica desligada."""
    N = json.load(open(alvos(pasta)[0], encoding="utf-8"))
    principal = next(t for t in N["tracks"] if t["type"] == "video")
    for s in principal["segments"]:
        for r in s.get("extra_material_refs", []):
            k, m = material_de(N, r)
            if k == "realtime_denoises":
                m["is_denoise"] = ligado
                m["denoise_rate"] = m.get("denoise_rate") or 0.85
    gravar(pasta, N)


def capcut_aberto():
    return subprocess.run(["pgrep", "-x", "CapCut"], capture_output=True).returncode == 0


# ---------------------------------------------------------------- comandos
def preparar(P):
    P_VEL[0] = P["velocidade"]
    ws = palavras(P)
    ps = pedacos(P, ws)
    modo, grupos, gk = janelas(P, ws, ps)
    rs = rostos(P, ps, gk, modo)
    enquadrar(P, ps, modo, grupos, gk, rs)
    # trocas de formato na timeline (onde o arco verde cobre a tela)
    P["_trocas"] = [round(ps[k]["ini"], 4) for k in range(1, len(ps)) if ps[k]["modo"] != ps[k - 1]["modo"]]
    cenas = montar_telas(P, ws, ps)
    return ws, ps, cenas


def resumo(ps, cenas):
    for p in ps:
        print(f"  {p['ini']:6.2f}-{p['ini'] + p['dur']:6.2f} {p['modo']:6s} x{p['escala']:.2f} tx {p['tx']:+.3f} ty {p['ty']:+.3f} "
              f"legenda {p['leg'][0]} {p['leg'][1]:.0f}")
    for c in cenas:
        print(f"  tela {c['id']}: {c['_ini']:.2f}-{c['_fim']:.2f} ({c['dur']:.2f}s) âncoras {c['ancoras']}")


def cmd_telas(P):
    ws, ps, cenas = preparar(P)
    resumo(ps, cenas)
    pasta = renderizar_telas(P, cenas)
    if P.get("cartao"):
        cartao_png(P, pasta)
    return ws, ps, cenas, pasta


def cmd_folha(P):
    ws, ps, cenas = preparar(P)
    import simples_cenas as SC
    saida = os.path.join(P["_trab"], "folha_telas.jpg")
    SC.folha([{k: v for k, v in c.items() if not k.startswith("_")} for c in cenas], saida)
    print(saida)


def volume_voz(P, ps, alvo=-14.0):
    """Ganho (linear, o "volume" do CapCut) que leva a fala cortada a ~-14 LUFS (o nosso padrão de rede social),
    com o pico verdadeiro abaixo de -1 dBTP."""
    expr = "+".join(f"between(t,{p['fonte']:.3f},{p['fonte'] + p['fonte_dur']:.3f})" for p in ps)
    e = subprocess.run(["ffmpeg", "-nostats", "-i", P["video"], "-vn", "-af", f"aselect='{expr}',asetpts=N/SR/TB,ebur128=peak=true",
                        "-f", "null", "-"], capture_output=True, text=True).stderr
    lufs = float(re.findall(r"I:\s+(-?[\d.]+) LUFS", e)[-1])
    pico = float(re.findall(r"Peak:\s+(-?[\d.]+) dBFS", e)[-1])
    ganho = min(alvo - lufs, -1.0 - pico)
    print(f"  voz cortada: {lufs:.1f} LUFS, pico {pico:.1f} dBTP -> ganho {ganho:+.1f} dB")
    return round(10 ** (ganho / 20), 3)


CARTAO_MAX = 5.5        # s: o cartão de nome fica no máximo isso (o da referência fica uns 4 s)


def janela_cartao(P, ws, ps, cenas):
    """O cartão de nome entra 0,2 s depois da 1ª palavra e sai 0,3 s depois da última (até 5,5 s), mas nunca invade a tela
    seguinte. Ele abre todo vídeo (pedido de 05/11/2026: "comece sempre com o doutor enquadrado aparecendo, e adicione
    legendas"; a Bia: "quando ele começa a falar, entra sempre o cardzinho com o nome dele")."""
    t = P["cartao"]
    c0 = quadro30(tl(ps, ws[t["de"]]["start"]) + 0.2)
    c1 = min(quadro30(tl(ps, ws[t["ate"]]["end"]) + 0.3), quadro30(c0 + CARTAO_MAX))
    depois = [c["_ini"] for c in cenas if c["_ini"] > c0 + 1e-3]
    return c0, min([c1] + depois)


def cmd_montar(P):
    if capcut_aberto() and not os.environ.get("CAPCUT_TESTE"):
        sys.exit("feche o CapCut antes (ele regrava o projeto aberto por cima)")
    ws, ps, cenas, pasta = cmd_telas(P)
    backup(P["projeto"], "antes da moldura")
    limpar_extras(P["projeto"])
    broll = []
    for c in cenas:
        b = dict(tipo="video", arquivo=vista(c["_arq"]), largura=W, altura=H if c["formato"] == "tela" else PH,
                 inicio=round(c["_ini"], 4), fim=round(c["_fim"], 4), duracao=round(c["_fim"] - c["_ini"], 4))
        if c["formato"] == "painel":
            b["ty"] = 0.5          # metade de cima
        broll.append(b)
    if P.get("cartao"):
        arq = cartao_png(P, pasta)
        c0, c1 = janela_cartao(P, ws, ps, cenas)
        broll.append(dict(arquivo=vista(arq), largura=W, altura=H, inicio=round(c0, 4), fim=round(c1, 4), zoom=1.0))
    broll.sort(key=lambda b: b["inicio"])
    for a, b in zip(broll, broll[1:]):
        if b["inicio"] < a["fim"] - 1e-3:
            sys.exit(f"telas sobrepostas em {b['inicio']:.2f}s")
    plano = dict(pedacos=[dict({k: p[k] for k in ("fonte", "fonte_dur", "ini", "dur", "escala", "tx", "ty")},
                               **({"volume": 0.0} if p.get("mudo") else {})) for p in ps],     # rabo sem voz antes da vinheta
                 velocidade=P["velocidade"], broll=broll, broll_modelo=P["broll_modelo"])
    plano["volume"] = P["volume"] if P.get("volume") is not None else volume_voz(P, ps)
    arq_plano = os.path.join(P["_trab"], "plano_capcut.json")
    json.dump(plano, open(arq_plano, "w"), ensure_ascii=False, indent=1)
    env = dict(os.environ, CAPCUT_TESTE="1") if os.environ.get("CAPCUT_TESTE") else None
    subprocess.run([sys.executable, os.path.join(AQUI, "capcut_montar.py"), P["projeto"], P["modelo"], arq_plano], check=True, env=env)
    ruido_capcut(P["projeto"], P.get("ruido_capcut", True))
    itens = legendas(P, ws, ps)
    n = escrever_legendas(P["projeto"], itens, P)
    narcos, total_vin = escrever_marca(P["projeto"], P, ps)
    json.dump([dict(it, cor=list(it["cor"])) for it in itens], open(os.path.join(P["_trab"], "legendas.json"), "w"), ensure_ascii=False)
    total = ps[-1]["ini"] + ps[-1]["dur"]
    print(f"{len(ps)} pedaços ({total:.2f}s a {P['velocidade']}x), {len(cenas)} telas, {len(itens)} textos em {n} trilhas, "
          f"{narcos} arcos verdes, vinheta até {total_vin:.2f}s")


def cmd_previa(P, saida, tempos=None):
    """Folha de revisão sem abrir o CapCut: o bruto com a escala e a posição de cada pedaço, as telas por cima, o
    cartão e as legendas desenhadas com a mesma fonte e as mesmas posições."""
    ws, ps, cenas = preparar(P)
    import simples_cenas as SC  # noqa: F401
    pasta = os.path.join(BROLL, P["nome"][:50].strip())
    for c in cenas:
        sem = {k: v for k, v in c.items() if not k.startswith("_")}
        c["_arq"] = os.path.join(pasta, f"{c['id']} {versao(sem)}.mp4")
    itens = legendas(P, ws, ps)
    total = ps[-1]["ini"] + ps[-1]["dur"]
    ts = [float(x) for x in tempos.split(",")] if tempos else [round(x, 2) for x in np.arange(0.5, total, 2.0)]
    tmp = tempfile.mkdtemp()
    quadros = []
    cartao = os.path.join(pasta, "cartao de nome.png")
    for t in ts:
        k = next((k for k, p in enumerate(ps) if p["ini"] <= t < p["ini"] + p["dur"]), len(ps) - 1)
        p = ps[k]
        src = p["fonte"] + (t - p["ini"]) * P["velocidade"]
        png = os.path.join(tmp, "q.png")
        subprocess.run(["ffmpeg", "-v", "error", "-y", "-ss", f"{src:.3f}", "-i", P["video"], "-frames:v", "1", "-vf", "scale=1080:1920", png], check=True)
        base = Image.open(png).convert("RGB")
        s = p["escala"]
        z = base.resize((int(W * s), int(H * s)), Image.BILINEAR)
        cx = W / 2 + p["tx"] * W / 2
        cy = H / 2 - p["ty"] * H / 2
        img = Image.new("RGB", (W, H), (0, 0, 0))
        img.paste(z, (int(round(cx - z.width / 2)), int(round(cy - z.height / 2))))
        c = next((c for c in cenas if c["_ini"] <= t < c["_fim"]), None)
        if c and os.path.exists(c["_arq"]):
            subprocess.run(["ffmpeg", "-v", "error", "-y", "-ss", f"{t - c['_ini']:.3f}", "-i", c["_arq"], "-frames:v", "1", png], check=True)
            ov = Image.open(png).convert("RGB")
            img.paste(ov, (0, 0))
        if P.get("cartao") and os.path.exists(cartao):
            a0, a1 = janela_cartao(P, ws, ps, cenas)
            if a0 <= t < a1:
                img.paste(Image.open(cartao), (0, 0), Image.open(cartao))
        img = desenhar_legendas(img, [it for it in itens if it["ini"] <= t < it["fim"]])
        d = ImageDraw.Draw(img)
        d.rectangle([0, 0, 200, 46], fill=(0, 0, 0))
        d.text((10, 8), f"{t:.2f}s", fill=(255, 255, 0), font=fonte_px(30))
        quadros.append(img.resize((W // 4, H // 4)))
    cols = 8
    rows = (len(quadros) + cols - 1) // cols
    sheet = Image.new("RGB", (cols * (W // 4 + 6), rows * (H // 4 + 6)), (255, 255, 255))
    for i, q in enumerate(quadros):
        sheet.paste(q, ((i % cols) * (W // 4 + 6), (i // cols) * (H // 4 + 6)))
    sheet.save(saida, quality=88)
    print(saida)


def desenhar_legendas(img, itens):
    img = img.convert("RGBA")
    for it in sorted(itens, key=lambda i: i["camada"]):
        f = fonte_px(it["em"])
        larg = f.getlength(it["texto"])
        asc, desc = metricas()
        base = it["cy"] + ((asc - desc) / 2 + 0.018) * it["em"]
        x = it["cx"] * W - larg / 2
        if it["sombra"]:
            sh = Image.new("RGBA", img.size, (0, 0, 0, 0))
            ImageDraw.Draw(sh).text((x, base + 3), it["texto"], font=f, fill=(0, 0, 0, int(255 * SOMBRA["alpha"])), anchor="ls")
            img.alpha_composite(sh.filter(ImageFilter.GaussianBlur(4)))
        d = ImageDraw.Draw(img)
        if it.get("pilula"):     # a pílula é a imagem coral posta atrás da palavra
            p = it["pilula"]
            d.rounded_rectangle([p["x0"], p["y0"], p["x1"], p["y1"]], radius=PILULA["raio"], fill=COR + (255,))
        d.text((x, base), it["texto"], font=f, fill=tuple(it["cor"]) + (255,), anchor="ls")
    return img.convert("RGB")


def cmd_conferir(P):
    """Confere a fala cortada (EDICAO.md: palavra faltando, sobrando ou comida perto de corte): remonta o áudio dos pedaços,
    transcreve de novo e compara com o texto das legendas. Diferença de grafia (Mounjaro/monjaro) é esperada; o resto,
    ouça ou transcreva o trecho com outro modelo antes de mexer."""
    import difflib
    import unicodedata
    import plataforma
    P_VEL[0] = P["velocidade"]
    ws = [w for w in palavras(P) if not w.get("oculta")]
    ps = pedacos(P, ws)
    expr = "+".join(f"between(t,{p['fonte']:.3f},{p['fonte'] + p['fonte_dur']:.3f})" for p in ps)
    wav = os.path.join(P["_trab"], "fala_cortada.wav")
    subprocess.run(["ffmpeg", "-v", "error", "-y", "-i", P["video"], "-vn", "-af", f"aselect='{expr}',asetpts=N/SR/TB", "-ac", "1",
                    "-ar", "16000", wav], check=True)
    r = plataforma.transcrever(wav, language="pt")
    norm = lambda t: re.sub(r"[^\w%]+", " ", unicodedata.normalize("NFC", t.lower())).split()  # noqa: E731
    ouvido = [x for s in r["segments"] for w in s.get("words", []) for x in norm(w["word"])]
    leg = [(x, tl(ps, w["start"])) for w in ws for x in norm(w["vis"])]
    a = [x for x, _ in leg]
    sm = difflib.SequenceMatcher(a=a, b=ouvido, autojunk=False)
    print(f"{len(a)} palavras, semelhança {sm.ratio():.3f}")
    for op, i1, i2, j1, j2 in sm.get_opcodes():
        if op == "equal" or " ".join(a[i1:i2]).replace("ou", "o").replace(" ", "") == " ".join(ouvido[j1:j2]).replace(" ", ""):
            continue
        t = leg[min(i1, len(leg) - 1)][1]
        print(f"  {t:6.2f}s legenda: ...{' '.join(a[max(0, i1 - 3):i1])} [{' '.join(a[i1:i2])}] {' '.join(a[i2:i2 + 2])}   "
              f"ouvido: [{' '.join(ouvido[j1:j2])}]")


def main():
    cmd, arq = sys.argv[1], sys.argv[2]
    P = carregar(arq)
    if cmd == "telas":
        cmd_telas(P)
    elif cmd == "folha":
        cmd_folha(P)
    elif cmd == "montar":
        cmd_montar(P)
    elif cmd == "previa":
        cmd_previa(P, sys.argv[3], sys.argv[4] if len(sys.argv) > 4 else None)
    elif cmd == "conferir":
        cmd_conferir(P)
    else:
        sys.exit(__doc__)


if __name__ == "__main__":
    main()
