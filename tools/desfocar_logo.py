#!/usr/bin/env python3
"""Desfoque redondo, com borda em degradê, que segue um logo na roupa ao longo do vídeo bruto inteiro.

Pedido de 2026-11-01 (Dra. Luciana, "16 - Suspenção de medicações antes da cirurgia"): "crie um blur redondo
em cima da logo que está na camisa da doutora ... que esse blur siga o movimento da doutora" e "coloque um
degradê nas bordas do blur para não ficar extremamente marcada a divisão".

Por que no bruto: o arquivo novo tem os mesmos quadros, então basta trocar o caminho no projeto do CapCut.
Cortes, zooms, retoque e legendas ficam como estão, e o desfoque acompanha qualquer zoom.

Rastreio (em 540x960):
- O logo é procurado por correspondência de modelo, perto de onde estava no quadro anterior, e só vale com
  correspondência forte (a mão que passa na frente enganava um rastreador simples).
- Sem o logo, a posição vem de uma segunda âncora no peito (ex.: o botão da camisa) mais o deslocamento entre as duas.
- Sem a âncora, vem do rosto; se nada aparece, fica onde estava.
- Depois, média móvel de 7 quadros.

O desfoque é gaussiano, aplicado nos planos yuv420p (sem passar por RGB), e mantém o áudio original.

Uso: desfocar_logo.py <bruto> <saida.mov> --t=<s de um quadro limpo> --logo=x,y --ancora=x,y [--raio=150] [--degrade=270]
  x,y em pixels do quadro reduzido a 540x960 (orientação de exibição); --raio e --degrade em pixels do vídeo cheio.
  Confira os quadros depois (o JSON da trilha fica ao lado da saída).
"""
import json
import subprocess
import sys

import cv2
import numpy as np


def ler_quadros(bruto, w, h):
    p = subprocess.Popen(["ffmpeg", "-v", "error", "-i", bruto, "-vf", f"scale={w}:{h}", "-f", "rawvideo", "-pix_fmt", "bgr24", "-"],
                         stdout=subprocess.PIPE)
    qs = []
    while True:
        b = p.stdout.read(w * h * 3)
        if len(b) < w * h * 3:
            return qs
        qs.append(np.frombuffer(b, np.uint8).reshape(h, w, 3))


def rastrear(qs, k0, logo, ancora, w, h):
    tpl = lambda img, x, y, a, b: img[y - b:y + b, x - a:x + a].copy()  # noqa: E731
    T_logo, T_anc = tpl(qs[k0], *logo, 24, 38), tpl(qs[k0], *ancora, 16, 16)
    cas = cv2.CascadeClassifier(cv2.data.haarcascades + "haarcascade_frontalface_default.xml")

    def busca(img, T, x, y, raio=14):
        th, tw = T.shape[0] // 2, T.shape[1] // 2
        x0, y0, x1, y1 = max(0, x - tw - raio), max(0, y - th - raio), min(w, x + tw + raio), min(h, y + th + raio)
        _, mx, _, loc = cv2.minMaxLoc(cv2.matchTemplate(img[y0:y1, x0:x1], T, cv2.TM_CCOEFF_NORMED))
        return x0 + loc[0] + tw, y0 + loc[1] + th, mx

    def rosto(img):
        fs = [f for f in cas.detectMultiScale(cv2.cvtColor(img, cv2.COLOR_BGR2GRAY), 1.1, 5, minSize=(80, 80)) if f[1] + f[3] / 2 < 0.55 * h]
        if not len(fs):
            return None
        x, y, fw, fh = max(fs, key=lambda f: f[2])
        return np.array([x + fw / 2, y + fh / 2])

    def passada(ordem):
        L, A, F = np.array(logo, float), np.array(ancora, float), rosto(qs[k0])
        off_la = L - A
        off_lf = L - F if F is not None else None
        out = {}
        for k in ordem:
            lx, ly, ls = busca(qs[k], T_logo, int(L[0]), int(L[1]))
            ax, ay, as_ = busca(qs[k], T_anc, int(A[0]), int(A[1]))
            if as_ >= 0.6:
                A = np.array([ax, ay], float)
            if ls >= 0.6:
                L = np.array([lx, ly], float)
                if as_ >= 0.6:
                    off_la = 0.9 * off_la + 0.1 * (L - A)
                if k % 10 == 0 and (f := rosto(qs[k])) is not None:
                    off_lf = (L - f) if off_lf is None else 0.8 * off_lf + 0.2 * (L - f)
            elif as_ >= 0.6:
                L = A + off_la
            elif off_lf is not None and (f := rosto(qs[k])) is not None:
                L = f + off_lf
                A = L - off_la
            out[k] = L.copy()
        return out

    a, b = passada(range(k0, len(qs))), passada(range(k0, -1, -1))
    pts = np.array([(a if k >= k0 else b)[k] for k in range(len(qs))])
    ker = np.ones(7) / 7
    return np.stack([np.convolve(np.pad(pts[:, i], 3, mode="edge"), ker, "valid") for i in range(2)], 1)


def desfocar(bruto, saida, trilha, raio, degrade, sigma=38):
    info = json.loads(subprocess.run(["ffprobe", "-v", "error", "-select_streams", "v:0", "-show_entries", "stream=width,height:stream_side_data=rotation",
                                      "-of", "json", bruto], capture_output=True, text=True).stdout)["streams"][0]
    W, H = info["width"], info["height"]
    if any(abs(s.get("rotation", 0)) == 90 for s in info.get("side_data_list", [])):
        W, H = H, W
    esc = W / 540
    yy, xx = np.mgrid[-degrade:degrade + 1, -degrade:degrade + 1]
    t = np.clip((degrade - np.hypot(xx, yy)) / (degrade - raio), 0, 1)
    M = (t * t * (3 - 2 * t)).astype(np.float32)      # degradê suave (smoothstep), sem degrau na borda
    M2 = cv2.resize(M, (M.shape[1] // 2 + 1, M.shape[0] // 2 + 1), interpolation=cv2.INTER_AREA)
    dec = subprocess.Popen(["ffmpeg", "-v", "error", "-i", bruto, "-f", "rawvideo", "-pix_fmt", "yuv420p", "-"], stdout=subprocess.PIPE, bufsize=10 ** 8)
    enc = subprocess.Popen(["ffmpeg", "-v", "error", "-y", "-f", "rawvideo", "-pix_fmt", "yuv420p", "-s", f"{W}x{H}", "-r", "30", "-i", "-",
                            "-i", bruto, "-map", "0:v", "-map", "1:a?", "-c:a", "copy", "-c:v", "hevc_videotoolbox", "-b:v", "45M", "-tag:v", "hvc1",
                            "-color_primaries", "bt709", "-color_trc", "bt709", "-colorspace", "bt709", "-shortest", saida],
                           stdin=subprocess.PIPE, bufsize=10 ** 8)

    def aplica(plano, cx, cy, mask, s):
        h, w = plano.shape
        rr = mask.shape[0] // 2
        x0c, y0c, x1c, y1c = max(0, cx - rr), max(0, cy - rr), min(w, cx + rr + 1), min(h, cy + rr + 1)
        if x1c <= x0c or y1c <= y0c:
            return
        pad = int(3 * s)
        a0, b0, a1, b1 = max(0, x0c - pad), max(0, y0c - pad), min(w, x1c + pad), min(h, y1c + pad)
        roi = plano[b0:b1, a0:a1].astype(np.float32)
        bl = cv2.GaussianBlur(roi, (0, 0), s)
        sub = (slice(y0c - b0, y1c - b0), slice(x0c - a0, x1c - a0))
        m = mask[y0c - (cy - rr):y1c - (cy - rr), x0c - (cx - rr):x1c - (cx - rr)]
        plano[y0c:y1c, x0c:x1c] = np.clip(roi[sub] * (1 - m) + bl[sub] * m + 0.5, 0, 255).astype(np.uint8)

    tam, k = W * H * 3 // 2, 0
    while len(buf := dec.stdout.read(tam)) == tam:
        f = np.frombuffer(buf, np.uint8).copy()
        Y = f[:W * H].reshape(H, W)
        U = f[W * H:W * H * 5 // 4].reshape(H // 2, W // 2)
        V = f[W * H * 5 // 4:].reshape(H // 2, W // 2)
        x, y = trilha[min(k, len(trilha) - 1)]
        cx, cy = int(round(x * esc)), int(round(y * esc))
        aplica(Y, cx, cy, M, sigma)
        aplica(U, cx // 2, cy // 2, M2, sigma / 2)
        aplica(V, cx // 2, cy // 2, M2, sigma / 2)
        enc.stdin.write(f.tobytes())
        k += 1
    enc.stdin.close()
    enc.wait()
    return k


def main():
    args = [a for a in sys.argv[1:] if not a.startswith("--")]
    opc = dict(a[2:].split("=", 1) for a in sys.argv[1:] if a.startswith("--") and "=" in a)
    bruto, saida = args
    k0 = int(round(float(opc["t"]) * 30))
    logo = tuple(int(v) for v in opc["logo"].split(","))
    ancora = tuple(int(v) for v in opc["ancora"].split(","))
    qs = ler_quadros(bruto, 540, 960)
    trilha = rastrear(qs, k0, logo, ancora, 540, 960)
    json.dump(trilha.round(1).tolist(), open(saida + ".trilha.json", "w"))
    n = desfocar(bruto, saida, trilha.tolist(), int(opc.get("raio", 150)), int(opc.get("degrade", 270)))
    print(f"{n} quadros; trilha em {saida}.trilha.json")


if __name__ == "__main__":
    main()
