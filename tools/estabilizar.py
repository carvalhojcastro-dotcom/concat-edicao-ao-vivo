#!/usr/bin/env python3
"""Estabilização leve de vídeo de celular (ex.: gravado no carro em movimento), sem efeito geleia.

Pedido de 2026-11-01 (Dra. Luciana, "45 dias depois da cirurgia"): "tente dar um pouco de estabilização pois filmamos
com o carro em movimento ... evite distorções na estabilização ou efeito geleia".
- Mede o movimento da câmera quadro a quadro (pontos + fluxo óptico, transformação de similaridade por RANSAC: o
  interior do carro manda, a rua na janela fica de fora).
- Corrige só deslocamento e giro, sem cisalhamento nem perspectiva, que deformam e dão o efeito geleia, seguindo o
  caminho suavizado (gaussiano, SIGMA quadros).
- Usa um corte fixo de ZOOM, sem zoom pulsando. Onde não há margem, reduz primeiro o giro e depois o deslocamento,
  para nunca mostrar borda.
- Trabalha em yuv420p, mantém o áudio original e grava <saida>.info.json com os quadros limitados.
No 45 dias: tremor de 17/14,5 px para 12,8/8,4 px (x/y em 540x960), giro de 1,13° para 0,86°.
Uso: estabilizar.py <bruto> <saida.mov> [--sigma=10] [--zoom=1.10]
"""
import subprocess, sys, json
import numpy as np, cv2
from scipy.ndimage import gaussian_filter1d
args = [a for a in sys.argv[1:] if not a.startswith("--")]
opc = dict(a[2:].split("=", 1) for a in sys.argv[1:] if a.startswith("--") and "=" in a)
raw, saida = args[:2]
SIGMA, ZOOM, ROT_MAX = float(opc.get("sigma", 10)), float(opc.get("zoom", 1.10)), np.radians(0.9)
def medir(video, w=540, h=960):
    """dx, dy, giro de um quadro para o outro, em 540x960."""
    p = subprocess.Popen(["ffmpeg", "-v", "error", "-i", video, "-vf", f"scale={w}:{h}", "-f", "rawvideo", "-pix_fmt", "gray", "-"], stdout=subprocess.PIPE)
    ant, mov = None, []
    while len(b := p.stdout.read(w * h)) == w * h:
        g = np.frombuffer(b, np.uint8).reshape(h, w)
        if ant is not None:
            pts = cv2.goodFeaturesToTrack(ant, 300, 0.01, 12)
            m = None
            if pts is not None:
                nxt, st, _ = cv2.calcOpticalFlowPyrLK(ant, g, pts, None)
                ok = st.ravel() == 1
                if ok.sum() >= 6:
                    m, _ = cv2.estimateAffinePartial2D(pts[ok], nxt[ok], method=cv2.RANSAC, ransacReprojThreshold=2.0)
            if m is None:
                m = np.array([[1, 0, 0], [0, 1, 0]], float)
            mov.append([m[0, 2], m[1, 2], np.arctan2(m[1, 0], m[0, 0])])
        ant = g
    return np.array(mov)


info = json.loads(subprocess.run(["ffprobe", "-v", "error", "-select_streams", "v:0", "-show_entries", "stream=width,height:stream_side_data=rotation",
                                  "-of", "json", raw], capture_output=True, text=True).stdout)["streams"][0]
W, H = info["width"], info["height"]
if any(abs(sd.get("rotation", 0)) == 90 for sd in info.get("side_data_list", [])):
    W, H = H, W
E = W / 540.0
mov = medir(raw)                          # dx, dy, giro por quadro (540x960)
traj = np.vstack([[0, 0, 0], np.cumsum(mov[:, :3], 0)])
c = gaussian_filter1d(traj, SIGMA, axis=0) - traj      # correção por quadro
c[:, 2] = np.clip(c[:, 2], -ROT_MAX, ROT_MAX)
def cobre(dx, dy, a):
    """O quadro corrigido (com zoom) cobre a saída inteira? Confere os 4 cantos dentro da imagem fonte."""
    M = cv2.getRotationMatrix2D((W / 2, H / 2), -np.degrees(a), ZOOM); M[0, 2] += dx; M[1, 2] += dy
    Mi = cv2.invertAffineTransform(M)
    for x, y in ((0, 0), (W, 0), (0, H), (W, H)):
        u, v = Mi @ np.array([x, y, 1.0])
        if not (0 <= u <= W and 0 <= v <= H): return False
    return True
# sem margem: primeiro some a rotação (menos visível), depois a translação
fr, ft = np.ones(len(c)), np.ones(len(c))
for k in range(len(c)):
    dx, dy, a = c[k, 0] * E, c[k, 1] * E, c[k, 2]
    while fr[k] > 0 and not cobre(dx, dy, a * fr[k]): fr[k] = max(0.0, fr[k] - 0.1)
    while ft[k] > 0 and not cobre(dx * ft[k], dy * ft[k], a * fr[k]): ft[k] = max(0.0, ft[k] - 0.05)
fr, ft = gaussian_filter1d(fr, 2), gaussian_filter1d(ft, 2)   # sem degrau
c[:, 2] *= fr; c[:, :2] *= ft[:, None]
fat = np.minimum(fr, ft)
json.dump({"limitados": int((fat < 0.99).sum()), "quadros": len(c)}, open(saida + ".info.json", "w"))
dec = subprocess.Popen(["ffmpeg", "-v", "error", "-i", raw, "-f", "rawvideo", "-pix_fmt", "yuv420p", "-"], stdout=subprocess.PIPE, bufsize=10**8)
enc = subprocess.Popen(["ffmpeg", "-v", "error", "-y", "-f", "rawvideo", "-pix_fmt", "yuv420p", "-s", f"{W}x{H}", "-r", "30", "-i", "-",
                        "-i", raw, "-map", "0:v", "-map", "1:a", "-c:a", "copy", "-c:v", "hevc_videotoolbox", "-b:v", "45M", "-tag:v", "hvc1",
                        "-color_primaries", "bt709", "-color_trc", "bt709", "-colorspace", "bt709", "-shortest", saida], stdin=subprocess.PIPE, bufsize=10**8)
tam = W * H * 3 // 2; k = 0
while len(buf := dec.stdout.read(tam)) == tam:
    f = np.frombuffer(buf, np.uint8)
    dx, dy, a = c[min(k, len(c) - 1)]; dx *= E; dy *= E
    M = cv2.getRotationMatrix2D((W / 2, H / 2), -np.degrees(a), ZOOM); M[0, 2] += dx; M[1, 2] += dy
    Y = cv2.warpAffine(f[:W * H].reshape(H, W), M, (W, H), flags=cv2.INTER_CUBIC, borderMode=cv2.BORDER_REFLECT)
    M2 = M.copy(); M2[:, 2] /= 2
    M2c = cv2.getRotationMatrix2D((W / 4, H / 4), -np.degrees(a), ZOOM); M2c[0, 2] += dx / 2; M2c[1, 2] += dy / 2
    U = cv2.warpAffine(f[W * H:W * H * 5 // 4].reshape(H // 2, W // 2), M2c, (W // 2, H // 2), flags=cv2.INTER_CUBIC, borderMode=cv2.BORDER_REFLECT)
    V = cv2.warpAffine(f[W * H * 5 // 4:].reshape(H // 2, W // 2), M2c, (W // 2, H // 2), flags=cv2.INTER_CUBIC, borderMode=cv2.BORDER_REFLECT)
    enc.stdin.write(Y.tobytes() + U.tobytes() + V.tobytes()); k += 1
    if k % 1000 == 0: print(k, "quadros", flush=True)
enc.stdin.close(); enc.wait(); print("pronto:", k, "quadros")
