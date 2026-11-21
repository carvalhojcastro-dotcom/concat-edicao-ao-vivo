"""Para onde cada apresentador olha no plano dos dois (pedido de 2026-11-10: "momentos em que eu estou falando, mas
eu olho para a Myrian ou vice-versa ... enquadrasse ela também"). Mede, a 5 fps, o giro da cabeça de cada um pelos
pontos do YuNet: (nariz - meio dos olhos) / distância entre os olhos. Negativo = nariz para a esquerda da imagem.
Uso: olhar.py <W> <id>   -> c<id>/olhar.json  {"amostras": [[t, {"esq": giro|null, "dir": giro|null}], ...]}"""
import json, os, subprocess, sys
import cv2
import numpy as np
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from comum import config, FPS  # noqa: E402

YUNET = "/Users/joaopedro/.claude/plugins/cache/edit-labs-ai/edit-labs-ai/1.0.0/skills/corte-viral/models/face_detection_yunet_2023mar.onnx"
W, cid = sys.argv[1], sys.argv[2]
cfg = config(W)
plano = json.load(open(os.path.join(W, f"c{cid}", "plano.json")))
AW, AH = 960, 540
det = cv2.FaceDetectorYN.create(YUNET, "", (AW, AH), score_threshold=0.6, nms_threshold=0.3, top_k=10)
saida = []
for p in plano["pecas"]:
    if p["cam"] != "H":
        continue
    s, d = p["fonte"], p["fonte_dur"]
    cmd = ["ffmpeg", "-v", "error", "-nostdin", "-hwaccel", "videotoolbox", "-ss", f"{s - 0.001:.4f}", "-i", cfg["fonte"],
           "-t", f"{d:.3f}", "-vf", f"fps=5,scale={AW}:{AH}", "-f", "rawvideo", "-pix_fmt", "bgr24", "-"]
    raw = subprocess.run(cmd, capture_output=True, check=True).stdout
    fr = np.frombuffer(raw, np.uint8).reshape(-1, AH, AW, 3)
    for k in range(len(fr)):
        _, faces = det.detect(np.ascontiguousarray(fr[k]))
        lados = {"esq": None, "dir": None}
        for f in (faces if faces is not None else []):
            x, y, w, h = f[:4]
            if h < 0.12 * AH:
                continue
            rex, ley, lex = f[4], f[7], f[6]
            olhos = abs(lex - rex) or 1.0
            giro = (f[8] - (f[4] + f[6]) / 2) / olhos
            lado = "esq" if (x + w / 2) / AW < 0.5 else "dir"
            lados[lado] = round(float(giro), 3)
        saida.append([round(s + k / 5, 2), lados])
json.dump({"amostras": saida}, open(os.path.join(W, f"c{cid}", "olhar.json"), "w"))
print(cid, len(saida), "amostras no plano dos apresentadores")
