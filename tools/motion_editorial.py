#!/usr/bin/env python3
"""Motions editoriais (paleta vinho/rosé/creme, estilo Tay Dantas) para projetos do CapCut, como vídeos ProRes 4444 com
alfa, mais os efeitos sonoros e zooms suaves. Aprovado nos vídeos 1 e 2 da Dra. Larissa (2026-11-09/10).

Regras aprendidas (ver memória tay-dantas-estilo e larissa-capcut):
  - cartões creme flutuantes (desfoque + fade + subida na entrada, flutuação leve), com margem >= 170 px das laterais e
    >= 240 px do topo, em posições que o corpo dela nunca cobre em nenhum zoom (máscara MediaPipe binarizada);
  - moldura de B-roll limpa: vinho escuro, janela com cantos de raio 60, sem texto, sem traços, sem filete e SEM animação
    de entrada/saída; dentro só um avanço lento da foto, corte seco entre fotos;
  - foto do assunto que ela explica = foto real; pessoas e cenas genéricas = IA realista (brasileiras ~40 anos);
  - zoom suave só quando pedido: keyframes FreeCurveInOut com alças de saída exponencial.

Uso como biblioteca: um script de cenas (tools/planos/<cliente>_<video>_motion.py) cria Video(...), registra cenas e
chama os comandos: mascaras, livres, folha, render, inserir. Ver tools/planos_exemplo/motion_editorial_exemplo.py.
"""
import copy
import glob
import json
import math
import os
import shutil
import subprocess
import sys
import time
import uuid
from concurrent.futures import ThreadPoolExecutor

import cv2
import numpy as np
from PIL import Image, ImageDraw, ImageFont, ImageFilter

W, H, FPS = 2160, 3840, 30
RAIZ = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
FONTES = os.path.join(RAIZ, "fonts")
SERIF = os.path.join(FONTES, "PlayfairDisplay-SemiBoldItalic.ttf")
SB = os.path.join(FONTES, "Poppins-SemiBold.ttf")
MD = os.path.join(FONTES, "Poppins-Medium.ttf")
VINHO, VINHO2 = (92, 20, 40), (128, 34, 58)
ROSE, BLUSH, CREME = (226, 168, 178), (246, 222, 222), (252, 246, 241)
DRAFTS = os.path.expanduser("~/Movies/CapCut/User Data/Projects/com.lveditor.draft")
VISTA = lambda p: p.replace(os.path.expanduser("~/Movies"), os.path.expanduser("~/Library/Containers/com.lemon.lvoverseas/Data/Movies"))  # noqa: E731
nid = lambda: str(uuid.uuid4()).upper()  # noqa: E731
us = lambda s: int(round(s * 1e6))  # noqa: E731


# ---------------- curvas ----------------
def cl(u):
    return min(max(u, 0.0), 1.0)


def eoq(u):
    return 1 - (1 - cl(u)) ** 5


def eoc(u):
    return 1 - (1 - cl(u)) ** 3


def eic(u):
    return cl(u) ** 3


def expo(u):
    u = cl(u)
    return 1.0 if u >= 1 else 1 - 2 ** (-10 * u)


def eob(u, s=1.5):
    u = cl(u) - 1
    return u * u * ((s + 1) * u + s) + 1


def suave(u):
    u = cl(u)
    return u * u * (3 - 2 * u)


def bez_expo(u):
    """cubic-bezier(0.16, 1, 0.3, 1), a mesma curva escrita nos keyframes do CapCut."""
    u = cl(u)
    lo, hi = 0.0, 1.0
    for _ in range(40):
        m = (lo + hi) / 2
        x = 3 * (1 - m) ** 2 * m * 0.16 + 3 * (1 - m) * m * m * 0.3 + m ** 3
        lo, hi = (m, hi) if x < u else (lo, m)
    m = (lo + hi) / 2
    return 3 * (1 - m) ** 2 * m + 3 * (1 - m) * m * m + m ** 3


_F = {}


def fonte(arq, tam):
    k = (arq, int(tam))
    if k not in _F:
        _F[k] = ImageFont.truetype(arq, int(tam))
    return _F[k]


# ---------------- sprites (RGBA float pré-multiplicado) ----------------
def de_pil(im):
    a = np.asarray(im.convert("RGBA")).astype(np.float32) / 255
    a[..., :3] *= a[..., 3:4]
    return a


def com_sombra(sp, desl=16, sig=26, forca=0.22, pad=70):
    h, w = sp.shape[:2]
    out = np.zeros((h + 2 * pad, w + 2 * pad, 4), np.float32)
    a = np.zeros(out.shape[:2], np.float32)
    a[pad + desl:pad + desl + h, pad:pad + w] = sp[..., 3]
    out[..., 3] = cv2.GaussianBlur(a, (0, 0), sig) * forca
    sub = out[pad:pad + h, pad:pad + w]
    sub[...] = sp + sub * (1 - sp[..., 3:4])
    return out


def xf(sp, sc=1.0, rot=0.0, blur=0.0):
    if abs(sc - 1) > 1e-3:
        h, w = sp.shape[:2]
        sp = cv2.resize(sp, (max(1, int(w * sc)), max(1, int(h * sc))), interpolation=cv2.INTER_AREA if sc < 1 else cv2.INTER_CUBIC)
    if abs(rot) > 0.02:
        h, w = sp.shape[:2]
        sp = cv2.warpAffine(sp, cv2.getRotationMatrix2D((w / 2, h / 2), rot, 1.0), (w, h), flags=cv2.INTER_LINEAR)
    if blur > 0.4:
        sp = cv2.GaussianBlur(sp, (0, 0), blur)
    return sp


def cola(dst, sp, cx, cy, op=1.0):
    h, w = sp.shape[:2]
    x, y = int(round(cx - w / 2)), int(round(cy - h / 2))
    x0, y0, x1, y1 = max(0, x), max(0, y), min(dst.shape[1], x + w), min(dst.shape[0], y + h)
    if x1 <= x0 or y1 <= y0:
        return
    s = sp[y0 - y:y1 - y, x0 - x:x1 - x] * op
    d = dst[y0:y1, x0:x1]
    d[...] = s + d * (1 - s[..., 3:4])


def cartao(w, h, r=56, cor=CREME, alfa=0.97, k=2):
    """Imagem PIL (já em k x) de um cartão arredondado."""
    im = Image.new("RGBA", (w * k, h * k), (0, 0, 0, 0))
    ImageDraw.Draw(im).rounded_rectangle([0, 0, w * k - 1, h * k - 1], radius=r * k, fill=cor + (int(255 * alfa),))
    return im


def fecha(im, w, h, **sombra):
    """Imagem PIL em k x -> sprite com sombra no tamanho final."""
    return com_sombra(de_pil(im.resize((w, h), Image.LANCZOS)), **sombra)


def texto(d, xy, s, f, cor, anc="ls", espaco=0):
    if not espaco:
        d.text(xy, s, font=f, fill=cor, anchor=anc)
        return f.getlength(s)
    x = xy[0]
    for c in s:
        d.text((x, xy[1]), c, font=f, fill=cor, anchor=anc)
        x += f.getlength(c) + espaco
    return x - xy[0]


def flutua(canvas, sp, t, t_in, t_out, cx, cy, fase=0.0, amp=10):
    """Entrada (desfoque, fade, subida, leve mola), flutuação e saída de um cartão."""
    u = t - t_in
    if u < 0 or t > t_out + 0.4:
        return
    op = eoc(u / 0.45)
    blur = (1 - eoc(u / 0.5)) * 22
    dy = (1 - eoq(u / 0.75)) * 80
    sc = 0.9 + 0.1 * eob(u / 0.6)
    e = (t - t_out) / 0.35
    if e > 0:
        ee = eic(e)
        op *= 1 - ee
        blur = max(blur, ee * 18)
        dy -= ee * 50
        sc *= 1 - 0.05 * ee
    if op <= 0.003:
        return
    k = min(u / 0.9, 1)
    dy += k * amp * math.sin(2 * math.pi * 0.31 * t + fase)
    rot = k * 0.7 * math.sin(2 * math.pi * 0.21 * t + fase + 1.3)
    cola(canvas, xf(sp, sc, rot, blur), cx, cy + dy, op)


def visto(d, cx, cy, q, k, cor=CREME, larg=8):
    """Visto desenhado (q 0..1) centrado em (cx, cy) em pixels já multiplicados por k."""
    p = [(cx - 16 * k, cy + 1 * k), (cx - 4 * k, cy + 13 * k), (cx + 18 * k, cy - 13 * k)]
    c1, c2 = math.dist(p[0], p[1]), math.dist(p[1], p[2])
    L = (c1 + c2) * cl(q)
    if L <= 0:
        return
    seg = [p[0]]
    if L <= c1:
        seg.append((p[0][0] + (p[1][0] - p[0][0]) * L / c1, p[0][1] + (p[1][1] - p[0][1]) * L / c1))
    else:
        m = (L - c1) / c2
        seg += [p[1], (p[1][0] + (p[2][0] - p[1][0]) * m, p[1][1] + (p[2][1] - p[1][1]) * m)]
    d.line(seg, fill=cor, width=larg * k, joint="curve")


# ---------------- moldura limpa e B-roll ----------------
JAN = (110, 170, 2050, 3670)
RAIO = 60
_PAINEL = {}


def painel():
    if "p" not in _PAINEL:
        yy = np.linspace(0, 1, H, dtype=np.float32)[:, None]
        xx = np.linspace(0, 1, W, dtype=np.float32)[None, :]
        a, b = np.array([44, 7, 19], np.float32), np.array([64, 11, 27], np.float32)
        base = a + (b - a) * yy[..., None]
        luz = np.exp(-(((xx - 0.5) / 0.6) ** 2 + (yy / 0.25) ** 2))[..., None] * np.array([16, 4, 7], np.float32)
        grao = np.random.default_rng(7).normal(0, 2.4, (H, W, 1)).astype(np.float32)
        rgb = np.clip(base + luz + grao, 0, 255)
        m = Image.new("L", (W * 2, H * 2), 255)
        ImageDraw.Draw(m).rounded_rectangle([JAN[0] * 2, JAN[1] * 2, JAN[2] * 2, JAN[3] * 2], radius=RAIO * 2, fill=0)
        alfa = np.asarray(m.resize((W, H), Image.LANCZOS)).astype(np.float32) / 255
        _PAINEL["p"] = de_pil(Image.fromarray(np.dstack([rgb, alfa * 255]).astype(np.uint8), "RGBA"))
    return _PAINEL["p"]


_FOTOS = {}


def foto(arq, girar=0):
    k = (arq, girar)
    if k not in _FOTOS:
        img = cv2.cvtColor(cv2.imread(arq), cv2.COLOR_BGR2RGB)
        if girar:
            img = np.ascontiguousarray(np.rot90(img, -girar // 90))
        _FOTOS[k] = img.astype(np.float32) / 255
    return _FOTOS[k]


def quadro_broll(fotos, t):
    """fotos: [(arquivo, ini, fim, foco=(fx, fy), girar=0)], tempos da timeline. Sem animação de entrada nem de saída."""
    jw, jh = JAN[2] - JAN[0], JAN[3] - JAN[1]
    out = np.zeros((H, W, 4), np.float32)
    for i, f in enumerate(fotos):
        arq, a, b = f[:3]
        foco = f[3] if len(f) > 3 and f[3] else (0.5, 0.5)
        girar = f[4] if len(f) > 4 else 0
        if not (a <= t < b or (i == len(fotos) - 1 and t >= a)):
            continue
        img = foto(arq, girar)
        ih, iw = img.shape[:2]
        tau, dur = t - a, b - a
        esc = max(jw / iw, jh / ih) * (1.0 + 0.045 * tau / dur)
        cxw = (JAN[0] + JAN[2]) / 2 + (1 if i % 2 == 0 else -1) * 24 * tau / dur
        cyw = (JAN[1] + JAN[3]) / 2
        M = np.float32([[esc, 0, cxw - foco[0] * iw * esc], [0, esc, cyw - foco[1] * ih * esc]])
        M[0, 2] = min(max(M[0, 2], JAN[2] - iw * esc), JAN[0])
        M[1, 2] = min(max(M[1, 2], JAN[3] - ih * esc), JAN[1])
        ph = cv2.warpAffine(img, M, (W, H), flags=cv2.INTER_AREA if esc < 1 else cv2.INTER_LANCZOS4)
        if esc > 1.2:
            ph = np.clip(ph * 1.35 - cv2.GaussianBlur(ph, (0, 0), 2.2) * 0.35, 0, 1)
        out[..., :3] = ph
        out[..., 3] = 1.0
    pn = painel()
    return pn + out * (1 - pn[..., 3:4])


def para_rgba8(pm):
    a = pm[..., 3:4]
    rgb = np.where(a > 1e-4, pm[..., :3] / np.maximum(a, 1e-4), 0)
    return (np.clip(np.dstack([rgb, a]), 0, 1) * 255 + 0.5).astype(np.uint8)


# ---------------- o vídeo: timeline dela, máscaras, cenas ----------------
class Video:
    def __init__(self, projeto, bruto, saida, trabalho, zooms=None):
        """projeto: nome da pasta no CapCut; bruto: vídeo da trilha principal; saida: pasta dos .mov (sob ~/Movies/CapCut/User Data);
        trabalho: pasta de trabalho (máscaras, folhas); zooms: {início do take na timeline: (escala final, duração da subida)}."""
        self.P = os.path.join(DRAFTS, projeto)
        self.bruto, self.saida, self.trab = bruto, saida, trabalho
        self.zooms = zooms or {}
        self.cenas = {}     # nome -> dict(ini, fim, faz(t)->canvas, trilha)
        self.rostos = {}
        os.makedirs(trabalho, exist_ok=True)
        r = os.path.join(trabalho, "rostos.json")
        if os.path.exists(r):
            self.rostos = {float(k): tuple(v) for k, v in json.load(open(r)).items()}

    # timeline
    def takes(self):
        d = json.load(open(os.path.join(self.P, "draft_info.json"), encoding="utf-8"))
        m = next(t for t in d["tracks"] if t["type"] == "video")
        out = []
        caminhos = {x["id"]: x.get("path", "") for x in d["materials"].get("videos", [])}
        vista = os.path.expanduser("~/Library/Containers/com.lemon.lvoverseas/Data")
        for s in sorted(m["segments"], key=lambda s: s["target_timerange"]["start"]):
            # cada take lê o seu bruto (um vídeo pode juntar duas gravações, PSV2 da Dra. Larissa, 2026-11-17)
            arq = caminhos.get(s["material_id"], "").replace(vista, os.path.expanduser("~"))
            arq = arq if os.path.exists(arq) else self.bruto
            sc, tx, ty = s["clip"]["scale"]["x"], s["clip"]["transform"]["x"], s["clip"]["transform"]["y"]
            kf = {k["property_type"]: k["keyframe_list"][0]["values"][0] for k in (s.get("common_keyframes") or []) if k.get("keyframe_list")}
            out.append(dict(ini=s["target_timerange"]["start"] / 1e6, dur=s["target_timerange"]["duration"] / 1e6,
                            src=s["source_timerange"]["start"] / 1e6, vel=s["speed"], sc=kf.get("KFTypeScaleX", sc),
                            tx=kf.get("KFTypePositionX", tx), ty=kf.get("KFTypePositionY", ty), arq=arq))
        return out

    def chave(self, tk):
        return next((k for k in self.zooms if abs(tk["ini"] - k) < 0.02), None)

    def enquadramento(self, tk, t):
        k = self.chave(tk)
        if k is None:
            return tk["sc"], tk["tx"], tk["ty"]
        s1, rampa = self.zooms[k]
        px, py = self.rostos.get(k, (0.5, 0.42))
        s = tk["sc"] + (s1 - tk["sc"]) * bez_expo((t - tk["ini"]) / rampa)
        return s, tk["tx"] + 2 * (px - 0.5) * (tk["sc"] - s), tk["ty"] + 2 * (py - 0.5) * (s - tk["sc"])

    def quadro(self, tks, t, w=540, h=960):
        tk = next((x for x in tks if x["ini"] <= t < x["ini"] + x["dur"]), tks[-1])
        src = tk["src"] + (t - tk["ini"]) * tk["vel"]
        r = subprocess.run(["ffmpeg", "-v", "error", "-ss", f"{src:.4f}", "-i", tk.get("arq", self.bruto), "-frames:v", "1", "-vf", f"scale={w}:{h}",
                            "-f", "rawvideo", "-pix_fmt", "rgb24", "-"], capture_output=True, check=True)
        img = np.frombuffer(r.stdout, np.uint8).reshape(h, w, 3)
        s, tx, ty = self.enquadramento(tk, t)
        M = np.float32([[s, 0, (w - w * s) / 2 + tx * w / 2], [0, s, (h - h * s) / 2 - ty * h / 2]])
        return cv2.warpAffine(img, M, (w, h), flags=cv2.INTER_LINEAR)

    def detectar_rostos(self):
        det = cv2.CascadeClassifier(cv2.data.haarcascades + "haarcascade_frontalface_default.xml")
        for tk in self.takes():
            k = self.chave(tk)
            if k is None:
                continue
            xs = []
            for dt in (0.1, 0.5, 0.9):
                r = subprocess.run(["ffmpeg", "-v", "error", "-ss", f"{tk['src'] + dt:.3f}", "-i", tk.get("arq", self.bruto), "-frames:v", "1", "-vf",
                                    "scale=540:960", "-f", "rawvideo", "-pix_fmt", "gray", "-"], capture_output=True, check=True)
                f = det.detectMultiScale(np.frombuffer(r.stdout, np.uint8).reshape(960, 540), 1.1, 5, minSize=(60, 60))
                if len(f):
                    x, y, w, h = max(f, key=lambda b: b[2] * b[3])
                    xs.append(((x + w / 2) / 540, (y + h / 2) / 960))
            self.rostos[k] = tuple(np.mean(xs, axis=0)) if xs else (0.5, 0.42)
        json.dump({str(k): list(v) for k, v in self.rostos.items()}, open(os.path.join(self.trab, "rostos.json"), "w"))
        return self.rostos

    def mascaras(self, passo=0.2):
        """Quadros (540x960) a cada passo e a máscara da pessoa (MediaPipe selfie multiclass) -> trabalho/q."""
        import mediapipe as mp
        from mediapipe.tasks.python import BaseOptions, vision
        modelo = os.path.join(RAIZ, "tools", "modelos", "selfie_multiclass_256x256.tflite")
        if not os.path.exists(modelo):
            os.makedirs(os.path.dirname(modelo), exist_ok=True)
            subprocess.run(["curl", "-sL", "-o", modelo, "https://storage.googleapis.com/mediapipe-models/image_segmenter/"
                            "selfie_multiclass_256x256/float32/latest/selfie_multiclass_256x256.tflite"], check=True)
        q = os.path.join(self.trab, "q")
        os.makedirs(q, exist_ok=True)
        tks = self.takes()
        ts = [round(t, 3) for t in np.arange(0.05, tks[-1]["ini"] + tks[-1]["dur"], passo)]

        def um(i):
            f = os.path.join(q, f"f{i:04d}.jpg")
            if not os.path.exists(f):
                cv2.imwrite(f, cv2.cvtColor(self.quadro(tks, ts[i]), cv2.COLOR_RGB2BGR))
            return f
        with ThreadPoolExecutor(6) as ex:
            fs = list(ex.map(um, range(len(ts))))
        seg = vision.ImageSegmenter.create_from_options(vision.ImageSegmenterOptions(base_options=BaseOptions(model_asset_path=modelo),
                                                                                     output_confidence_masks=True))
        for f in fs:
            bgr = cv2.imread(f)
            r = seg.segment(mp.Image(image_format=mp.ImageFormat.SRGB, data=cv2.cvtColor(bgr, cv2.COLOR_BGR2RGB).copy()))
            p = np.clip(1.0 - r.confidence_masks[0].numpy_view().astype(np.float32), 0, 1)
            saida = os.path.join(os.path.dirname(f), "m" + os.path.basename(f)[1:].replace(".jpg", ".png"))
            if not cv2.imwrite(saida, (cv2.resize(p, (540, 960)) * 255).astype(np.uint8)):
                sys.exit(f"não gravou {saida}")
        json.dump(ts, open(os.path.join(q, "tempos.json"), "w"))

    def _ms(self):
        if not hasattr(self, "_mcache"):
            q = os.path.join(self.trab, "q")
            ts = json.load(open(os.path.join(q, "tempos.json")))
            self._mcache = (ts, {i: (cv2.imread(os.path.join(q, f"m{i:04d}.png"), 0) > 128).astype(np.float32) for i in range(len(ts))})
        return self._mcache

    def cobertura(self, cx, cy, w, h, a, b, folga=40):
        ts, ms = self._ms()
        f = 540 / W
        x0, x1 = int((cx - w / 2 - folga) * f), int((cx + w / 2 + folga) * f)
        y0, y1 = int((cy - h / 2 - folga) * f), int((cy + h / 2 + folga) * f)
        v = [ms[i][max(0, y0):y1, max(0, x0):x1].mean() for i, t in enumerate(ts) if a <= t <= b]
        return float(max(v)) if v else 0.0

    def topo_cabeca(self, a, b):
        ts, ms = self._ms()
        out = []
        for i, t in enumerate(ts):
            if a <= t <= b:
                rows = np.where(ms[i][:, 100:440].max(1) > 0)[0]
                out.append(rows.min() / 960 if len(rows) else 1.0)
        return min(out) if out else 1.0

    def livre_lado(self, w, h, a, b, lado, margem, ys=range(440, 1700, 40)):
        return [cy for cy in ys if self.cobertura(margem + w / 2 if lado == "esq" else W - margem - w / 2, cy, w, h, a, b) <= 0.004]

    # cenas
    def cena(self, nome, ini, fim, faz, trilha="Motion graphics (Concat)"):
        self.cenas[nome] = dict(ini=ini, fim=fim, faz=faz, trilha=trilha)

    def broll(self, nome, fotos, trilha="B-roll molduras (Concat)"):
        self.cena(nome, fotos[0][1], fotos[-1][2], lambda t, f=fotos: quadro_broll(f, t), trilha)

    def arquivo(self, nome):
        return os.path.join(self.saida, f"{nome} alpha 4k.mov")

    def render(self, nomes=None):
        os.makedirs(self.saida, exist_ok=True)
        for nome in nomes or list(self.cenas):
            c = self.cenas[nome]
            n = int(round((c["fim"] - c["ini"]) * FPS))
            p = subprocess.Popen(["ffmpeg", "-v", "error", "-y", "-f", "rawvideo", "-pix_fmt", "rgba", "-s", f"{W}x{H}", "-r", str(FPS), "-i", "-",
                                  "-c:v", "prores_ks", "-profile:v", "4", "-pix_fmt", "yuva444p10le", "-vendor", "apl0", self.arquivo(nome)],
                                 stdin=subprocess.PIPE)
            for k in range(n):
                p.stdin.write(para_rgba8(c["faz"](c["ini"] + (k + 0.5) / FPS)).tobytes())
            p.stdin.close()
            p.wait()
            print(f"{nome}: {n} quadros ({c['ini']:.3f}-{c['fim']:.3f})")

    def folha(self, saida, ts):
        tks = self.takes()
        w, h = 540, 960
        tiles = []
        for t in ts:
            base = self.quadro(tks, t, w, h).astype(np.float32) / 255
            for c in self.cenas.values():
                if c["ini"] <= t < c["fim"]:
                    pm = cv2.resize(c["faz"](t), (w, h), interpolation=cv2.INTER_AREA)
                    base = pm[..., :3] + base * (1 - pm[..., 3:4])
            img = cv2.cvtColor((np.clip(base, 0, 1) * 255).astype(np.uint8), cv2.COLOR_RGB2BGR)
            cv2.rectangle(img, (80, int(0.55 * h)), (460, int(0.72 * h)), (0, 255, 255), 1)
            cv2.putText(img, f"{t:.2f}", (8, h - 12), cv2.FONT_HERSHEY_SIMPLEX, 0.8, (0, 255, 255), 2)
            tiles.append(img)
        vazio = np.zeros_like(tiles[0])
        linhas = [np.hstack(tiles[i:i + 6] + [vazio] * (6 - len(tiles[i:i + 6]))) for i in range(0, len(tiles), 6)]
        cv2.imwrite(saida, np.vstack(linhas), [cv2.IMWRITE_JPEG_QUALITY, 88])

    # escrita no CapCut
    def inserir(self, sfx_plano, molde_audio):
        """Troca as trilhas nossas (motions, B-rolls, SFX) e os keyframes dos zooms suaves; o resto do projeto fica como ela deixou."""
        if subprocess.run(["pgrep", "-x", "CapCut"], capture_output=True).returncode == 0:
            sys.exit("feche o CapCut")
        P = self.P
        alvos = [p for p in [os.path.join(P, "draft_info.json"), os.path.join(P, "template-2.tmp")] + glob.glob(os.path.join(P, "Timelines", "*", "draft_info.json"))
                 + glob.glob(os.path.join(P, "Timelines", "*", "template-2.tmp")) if os.path.exists(p)]
        bk = os.path.expanduser(f"~/Desktop/Claude Code Skills/backup-capcut/{os.path.basename(P)} {time.strftime('%Y-%m-%d %H%M%S')} (antes dos motions)")
        for p in alvos + glob.glob(os.path.join(P, "*.json")):
            dst = os.path.join(bk, os.path.relpath(p, P))
            os.makedirs(os.path.dirname(dst), exist_ok=True)
            shutil.copy2(p, dst)
        d = json.load(open(alvos[0], encoding="utf-8"))

        def mats(D):
            return {m["id"]: (k, m) for k, v in D["materials"].items() if isinstance(v, list) for m in v if isinstance(m, dict) and "id" in m}
        NOMES = ("Motion graphics (Concat)", "B-roll molduras (Concat)", "SFX motions (Concat)")
        velhas = [t for t in d["tracks"] if t.get("name", "").startswith(NOMES)]
        ids = {s["material_id"] for t in velhas for s in t["segments"]} | {r for t in velhas for s in t["segments"] for r in s.get("extra_material_refs", [])}
        d["tracks"] = [t for t in d["tracks"] if t not in velhas]
        for k, v in d["materials"].items():
            if isinstance(v, list):
                d["materials"][k] = [m for m in v if not (isinstance(m, dict) and m.get("id") in ids)]
        M = mats(d)
        principal = next(t for t in d["tracks"] if t["type"] == "video")
        sv = sorted(principal["segments"], key=lambda s: s["target_timerange"]["start"])[0]
        mv = M[sv["material_id"]][1]
        MANTER = ("speeds", "canvases", "material_colors", "placeholder_infos", "sound_channel_mappings", "vocal_separations")

        def refs(seg):
            out = []
            for r in seg.get("extra_material_refs", []):
                k, m = M.get(r, (None, None))
                if m is None or k not in MANTER:
                    continue
                m2 = dict(copy.deepcopy(m), id=nid())
                if k == "speeds":
                    m2["speed"] = 1.0
                d["materials"].setdefault(k, []).append(m2)
                out.append(m2["id"])
            return out
        base_tr = {k: v for k, v in principal.items() if k != "segments"}
        trilhas = {}
        for nome, c in self.cenas.items():
            dur = int(round((c["fim"] - c["ini"]) * FPS)) / FPS
            arq = self.arquivo(nome)
            m = dict(copy.deepcopy(mv), id=nid(), path=VISTA(arq), width=W, height=H, duration=us(dur), material_name=os.path.basename(arq),
                     local_material_id=str(uuid.uuid4()), md5="", unique_id=uuid.uuid4().hex, type="video", category_name="local", has_audio=False,
                     has_sound_separated=False, extra_type_option=0)
            if isinstance(m.get("matting"), dict):
                m["matting"].update(flag=0, path="", custom_matting_id="")
            d["materials"]["videos"].append(m)
            s = copy.deepcopy(sv)
            s.update(id=nid(), material_id=m["id"], extra_material_refs=refs(sv), speed=1.0, volume=0.0, last_nonzero_volume=1.0,
                     source_timerange={"start": 0, "duration": us(dur)}, target_timerange={"start": us(c["ini"]), "duration": us(dur)},
                     common_keyframes=[], keyframe_refs=[], render_index=1)
            s["clip"] = dict(copy.deepcopy(sv["clip"]), scale={"x": 1.0, "y": 1.0}, transform={"x": 0.0, "y": 0.0}, rotation=0.0, alpha=1.0,
                             flip={"vertical": False, "horizontal": False})
            s["uniform_scale"] = {"on": True, "value": 1.0}
            trilhas.setdefault(c["trilha"], []).append(s)
        novas = [dict(copy.deepcopy(base_tr), id=nid(), flag=2, name=n, segments=sorted(trilhas[n], key=lambda s: s["target_timerange"]["start"]))
                 for n in ("Motion graphics (Concat)", "B-roll molduras (Concat)") if n in trilhas]
        i_txt = next((i for i, t in enumerate(d["tracks"]) if t["type"] == "text"), len(d["tracks"]))
        d["tracks"][i_txt:i_txt] = novas
        # SFX (molde de áudio de outro projeto)
        B = json.load(open(os.path.join(molde_audio, "draft_info.json"), encoding="utf-8"))
        MB = mats(B)
        ta = next(t for t in B["tracks"] if t["type"] == "audio" and t["segments"])
        sa = ta["segments"][0]
        ma = MB[sa["material_id"]][1]
        sfx = json.load(open(sfx_plano))
        fila = []
        for e in sorted(sfx["efeitos"], key=lambda e: e["em"]):
            m = copy.deepcopy(ma)
            m.update(id=nid(), path=e["arquivo"], name=e["nome"], duration=us(e["duracao"]), type="extract_music", category_name="local", category_id="",
                     music_id=nid(), unique_id=uuid.uuid4().hex, resource_id="", third_resource_id="", effect_id="", source_platform=0, wave_points=[],
                     check_flag=1, local_material_id="", copyright_limit_type="none")
            d["materials"].setdefault("audios", []).append(m)
            rr = []
            for r in sa.get("extra_material_refs", []):
                k, mm = MB.get(r, (None, None))
                if mm is None:
                    continue
                m2 = dict(copy.deepcopy(mm), id=nid())
                if k == "speeds":
                    m2["speed"] = 1.0
                d["materials"].setdefault(k, []).append(m2)
                rr.append(m2["id"])
            vol = e.get("volume", 1.0)
            s = copy.deepcopy(sa)
            s.update(id=nid(), material_id=m["id"], extra_material_refs=rr, source_timerange={"start": 0, "duration": us(e["duracao"])},
                     target_timerange={"start": us(e["em"]), "duration": us(e["duracao"])}, volume=vol, last_nonzero_volume=vol, speed=1.0,
                     common_keyframes=[], keyframe_refs=[])
            livre = next((k for k, (f, _) in enumerate(fila) if f <= e["em"] + 1e-6), None)
            if livre is None:
                fila.append([0.0, dict(copy.deepcopy({k: v for k, v in ta.items() if k != "segments"}), id=nid(), segments=[],
                                       name=f"SFX motions (Concat) {len(fila) + 1}")])
                livre = len(fila) - 1
            fila[livre][0] = e["em"] + e["duracao"]
            fila[livre][1]["segments"].append(s)
        d["tracks"] += [t for _, t in fila]
        # zooms suaves (keyframes de curva exponencial)
        tks = self.takes()
        nk = 0
        for s in principal["segments"]:
            ini = s["target_timerange"]["start"] / 1e6
            tk = next(x for x in tks if abs(x["ini"] - ini) < 1e-3)
            k = self.chave(tk)
            if k is None:
                continue
            s1, rampa = self.zooms[k]
            sc0, tx0, ty0 = self.enquadramento(tk, tk["ini"])
            sc1, tx1, ty1 = self.enquadramento(tk, tk["ini"] + rampa + 1)
            a = s["source_timerange"]["start"]
            b = a + us(rampa * s.get("speed", 1.0))
            dt = b - a

            def par(prop, v0, v1):
                return {"id": nid(), "material_id": "", "property_type": prop, "keyframe_list": [
                    {"id": nid(), "curveType": "FreeCurveInOut", "time_offset": a, "left_control": {"x": 0.0, "y": 0.0},
                     "right_control": {"x": 0.16 * dt, "y": 1.0 * (v1 - v0)}, "values": [v0], "string_value": "", "graphID": ""},
                    {"id": nid(), "curveType": "FreeCurveInOut", "time_offset": b, "left_control": {"x": -0.70 * dt, "y": 0.0},
                     "right_control": {"x": 0.0, "y": 0.0}, "values": [v1], "string_value": "", "graphID": ""}]}
            s["common_keyframes"] = [par("KFTypeScaleX", sc0, sc1), par("KFTypePositionX", tx0, tx1), par("KFTypePositionY", ty0, ty1)]
            s["clip"]["scale"] = {"x": sc1, "y": sc1}
            s["clip"]["transform"] = {"x": tx1, "y": ty1}
            nk += 1
        if d.get("render_index_track_mode_on"):
            for i, t in enumerate(d["tracks"]):
                for s in t["segments"]:
                    s["track_render_index"] = i
        txt = json.dumps(d, ensure_ascii=False, separators=(",", ":"))
        for p in alvos:
            open(p, "w", encoding="utf-8").write(txt)
        print(f"{len(self.cenas)} vídeos, {len(sfx['efeitos'])} SFX, {nk} zooms suaves; backup {bk}")


def principal(v, argv):
    """Comandos: rostos | mascaras | livres a b | folha saida.jpg t1,t2 | render [nome] | inserir sfx_plano molde"""
    cmd = argv[1]
    if cmd == "rostos":
        print(v.detectar_rostos())
    elif cmd == "mascaras":
        v.mascaras()
    elif cmd == "folha":
        v.folha(argv[2], [float(x) for x in argv[3].split(",")])
    elif cmd == "render":
        v.render(argv[2:] or None)
    elif cmd == "inserir":
        v.inserir(argv[2], argv[3])
