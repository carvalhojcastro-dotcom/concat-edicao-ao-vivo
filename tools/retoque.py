#!/usr/bin/env python3
"""Retoque de rosto (o "Retoque" do CapCut), aplicado no vídeo bruto antes da edição.

Rode com o python do venv (mediapipe + opencv-contrib < 5):
  tools/.venv/bin/python tools/retoque.py <video> <saida.mov>            processa o vídeo todo
  tools/.venv/bin/python tools/retoque.py <video> <pasta> --quadros "20 45.5"   antes/depois em JPG
  tools/.venv/bin/python tools/retoque.py <video> <saida.mov> --projeto <projeto>
      processa e troca a mídia no projeto do Concat (cortes, legendas e zoom ficam como estão)

Os valores padrão copiam a predefinição do usuário no CapCut (Pele: remover rugas 13, uniforme 12,
remover linhas do sorriso 93, olheiras 17; Maquiagem "Naturais" 56). Mude com --rugas= --uniforme=
--sorriso= --olheiras= --maquiagem= (0 a 100).

Como funciona: o MediaPipe acha 478 pontos do rosto em cada quadro (suavizados no tempo para a máscara
não tremer). Com eles saem as máscaras de pele (oval do rosto sem olhos, sobrancelhas e boca), das
linhas do sorriso, das olheiras, dos lábios e das maçãs do rosto. Rugas e linhas são "vales" de
luminância: o retoque os preenche e alisa a pele com filtro guiado, que preserva bordas (óculos,
cabelo) e devolve parte da textura fina para a pele não ficar de plástico.
"""
import json
import os
import subprocess
import sys

import cv2
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import plataforma  # noqa: E402  (HEVC no codificador da máquina)
import numpy as np

AQUI = os.path.dirname(os.path.abspath(__file__))
MODELO = os.path.join(AQUI, "modelos", "face_landmarker.task")
URL_MODELO = ("https://storage.googleapis.com/mediapipe-models/face_landmarker/"
              "face_landmarker/float16/1/face_landmarker.task")

PADRAO = {"rugas": 13, "uniforme": 12, "sorriso": 93, "olheiras": 17, "maquiagem": 56}

OVAL = [10, 338, 297, 332, 284, 251, 389, 356, 454, 323, 361, 288, 397, 365, 379, 378, 400, 377, 152,
        148, 176, 149, 150, 136, 172, 58, 132, 93, 234, 127, 162, 21, 54, 103, 67, 109]
OLHO_A = [33, 7, 163, 144, 145, 153, 154, 155, 133, 173, 157, 158, 159, 160, 161, 246]
OLHO_B = [263, 249, 390, 373, 374, 380, 381, 382, 362, 398, 384, 385, 386, 387, 388, 466]
PALPEBRA_A = [33, 7, 163, 144, 145, 153, 154, 155, 133]
PALPEBRA_B = [263, 249, 390, 373, 374, 380, 381, 382, 362]
SOBRANCELHA_A = [70, 63, 105, 66, 107, 55, 65, 52, 53, 46]
SOBRANCELHA_B = [300, 293, 334, 296, 336, 285, 295, 282, 283, 276]
LABIOS = [61, 146, 91, 181, 84, 17, 314, 405, 321, 375, 291, 409, 270, 269, 267, 0, 37, 39, 40, 185]
NARINAS = [98, 97, 2, 326, 327, 294, 278, 344, 440, 275, 4, 45, 220, 115, 48, 64]
# linha nariz-boca (sulco nasogeniano) de cada lado: asa do nariz -> canto da boca, por fora
SULCO_A = [129, 203, 206, 216, 212]
SULCO_B = [358, 423, 426, 436, 432]
MACA_A, MACA_B = 50, 280


def _poli(mask, pts, idx, valor=1.0):
    cv2.fillPoly(mask, [np.round(pts[idx]).astype(np.int32)], valor, cv2.LINE_AA)


def _linha(mask, pts, idx, esp):
    cv2.polylines(mask, [np.round(pts[idx]).astype(np.int32)], False, 1.0, int(max(2, esp)), cv2.LINE_AA)


def _suave(m, s):
    k = int(s * 3) | 1
    return cv2.GaussianBlur(m, (k, k), s)


def mascaras(pts, forma):
    """Máscaras float 0..1 na área recortada (forma = (h, w)); pts em pixels dessa área."""
    h, w = forma
    largura = np.ptp(pts[OVAL, 0])
    olho = np.ptp(pts[PALPEBRA_A, 0])
    m = {}
    pele = np.zeros((h, w), np.float32)
    _poli(pele, pts, OVAL)
    fora = np.zeros((h, w), np.float32)
    for idx in (OLHO_A, OLHO_B, SOBRANCELHA_A, SOBRANCELHA_B, LABIOS):
        _poli(fora, pts, idx)
    fora = cv2.dilate(fora, np.ones((int(olho * 0.12) | 1,) * 2, np.uint8))
    m["pele"] = _suave(np.clip(pele - fora, 0, 1), largura * 0.015)
    sulco = np.zeros((h, w), np.float32)
    _linha(sulco, pts, SULCO_A, largura * 0.07)
    _linha(sulco, pts, SULCO_B, largura * 0.07)
    m["sulco"] = _suave(sulco, largura * 0.03) * m["pele"]
    olheira = np.zeros((h, w), np.float32)
    for idx in (PALPEBRA_A, PALPEBRA_B):
        baixo = pts[idx].copy()
        baixo[:, 1] += olho * 0.42
        cv2.fillPoly(olheira, [np.round(np.vstack([pts[idx], baixo[::-1]])).astype(np.int32)], 1.0, cv2.LINE_AA)
    olheira = olheira * (1 - cv2.dilate(fora, np.ones((int(olho * 0.08) | 1,) * 2, np.uint8)))
    m["olheira"] = _suave(olheira, olho * 0.12)
    labios = np.zeros((h, w), np.float32)
    _poli(labios, pts, LABIOS)
    m["labios"] = _suave(labios, largura * 0.006)
    maca = np.zeros((h, w), np.float32)
    for i in (MACA_A, MACA_B):
        cv2.circle(maca, tuple(np.round(pts[i]).astype(int)), int(largura * 0.11), 1.0, -1, cv2.LINE_AA)
    m["maca"] = _suave(maca, largura * 0.07) * m["pele"]
    narinas = np.zeros((h, w), np.float32)
    _poli(narinas, pts, NARINAS)
    m["pele"] *= 1 - _suave(narinas, largura * 0.01) * 0.6
    return m, largura


def retocar(img, pts, v):
    """img BGR uint8 (área do rosto); pts 478x2 em pixels dessa área; v = valores 0..100."""
    pts = np.asarray(pts, np.float32)
    m, largura = mascaras(pts, img.shape[:2])
    # bordas fortes (armação de óculos, fios de cabelo na testa) ficam de fora do retoque;
    # ruga e sulco são suaves e não chegam a esse limiar
    cinza = cv2.GaussianBlur(cv2.cvtColor(img, cv2.COLOR_BGR2GRAY), (0, 0), max(1.0, largura * 0.002))
    borda = cv2.Canny(cinza, 45, 110).astype(np.float32) / 255
    borda = cv2.dilate(borda, np.ones((int(largura * 0.012) | 1,) * 2, np.uint8))
    livre = 1 - np.clip(_suave(borda, largura * 0.006) * 1.5, 0, 1)
    for nome in ("pele", "sulco", "olheira", "maca"):
        m[nome] = m[nome] * livre
    f = img.astype(np.float32) / 255.0
    lab = cv2.cvtColor(f, cv2.COLOR_BGR2LAB)  # L 0..100, a/b ~ -128..127
    L = lab[..., 0]

    # vales de luminância (rugas, sulcos, olheiras): quanto o ponto é mais escuro que a vizinhança
    def vale(sigma):
        return np.maximum(_suave(L, sigma) - L, 0)

    rugas = v["rugas"] / 100
    L += vale(largura * 0.012) * m["pele"] * min(1.0, rugas * 3.0)
    L += vale(largura * 0.04) * m["sulco"] * (v["sorriso"] / 100) * 0.9
    L += vale(largura * 0.05) * m["olheira"] * min(1.0, v["olheiras"] / 100 * 3.5)
    # olheira também é cor: puxa a/b para o tom da maçã do rosto
    for c in (1, 2):
        ref = _suave(lab[..., c], largura * 0.08)
        lab[..., c] += (ref - lab[..., c]) * m["olheira"] * min(1.0, v["olheiras"] / 100 * 2.5)
    lab[..., 0] = L

    # alisar a pele (filtro guiado preserva bordas) e devolver metade da textura fina
    rgb = cv2.cvtColor(lab, cv2.COLOR_LAB2BGR)
    r = max(4, int(largura * 0.025))
    liso = cv2.ximgproc.guidedFilter(rgb, rgb, r, 0.0016)
    fino = rgb - cv2.GaussianBlur(rgb, (0, 0), max(1.0, largura * 0.0025))
    liso = liso + fino * 0.55
    quanto = np.clip((rugas + v["uniforme"] / 100) * 1.6, 0, 0.9)
    k = (m["pele"] * quanto + m["sulco"] * (v["sorriso"] / 100) * 0.5)[..., None]
    k = np.clip(k, 0, 0.95)
    rgb = (rgb * (1 - k) + liso * k).astype(np.float32)

    # maquiagem "Naturais": pele uniforme e um pouco mais luminosa, lábio e maçã rosados de leve
    mq = v["maquiagem"] / 100
    lab = cv2.cvtColor(np.clip(rgb, 0, 1), cv2.COLOR_BGR2LAB)
    lab[..., 0] += m["pele"] * 1.5 * mq
    lab[..., 1] += m["labios"] * 5.0 * mq + m["maca"] * 2.5 * mq
    lab[..., 2] += m["labios"] * 0.5 * mq
    out = cv2.cvtColor(lab, cv2.COLOR_LAB2BGR)
    return np.clip(out * 255 + 0.5, 0, 255).astype(np.uint8)


class Rosto:
    """Pontos do rosto quadro a quadro, com suavização temporal."""

    def __init__(self, fps):
        if not os.path.exists(MODELO):
            os.makedirs(os.path.dirname(MODELO), exist_ok=True)
            subprocess.run(["curl", "-sSfL", "-o", MODELO, URL_MODELO], check=True)
        import mediapipe as mp
        from mediapipe.tasks.python import BaseOptions, vision
        self.mp = mp
        self.det = vision.FaceLandmarker.create_from_options(vision.FaceLandmarkerOptions(
            base_options=BaseOptions(model_asset_path=MODELO), running_mode=vision.RunningMode.VIDEO,
            num_faces=1, min_face_detection_confidence=0.4, min_tracking_confidence=0.4))
        self.fps, self.n, self.ant = fps, 0, None

    def pontos(self, frame):
        h, w = frame.shape[:2]
        esc = 720 / max(h, w)
        peq = cv2.cvtColor(cv2.resize(frame, (int(w * esc), int(h * esc)), interpolation=cv2.INTER_AREA),
                           cv2.COLOR_BGR2RGB)
        r = self.det.detect_for_video(self.mp.Image(image_format=self.mp.ImageFormat.SRGB, data=peq),
                                      int(self.n * 1000 / self.fps))
        self.n += 1
        if not r.face_landmarks:
            self.ant = None
            return None
        p = np.array([[q.x * w, q.y * h] for q in r.face_landmarks[0]], np.float32)
        if self.ant is not None:
            # parado treme menos (média forte); mexendo acompanha rápido
            mov = np.median(np.linalg.norm(p - self.ant, axis=1)) / max(1.0, np.ptp(p[:, 0]))
            a = 0.35 if mov < 0.004 else 0.8
            p = self.ant * (1 - a) + p * a
        self.ant = p
        return p


def quadro(frame, pts, v):
    if pts is None:
        return frame
    h, w = frame.shape[:2]
    larg = np.ptp(pts[:, 0])
    x0, y0 = np.maximum(pts.min(0) - larg * 0.15, 0).astype(int)
    x1, y1 = np.minimum(pts.max(0) + larg * 0.15, [w, h]).astype(int)
    out = frame.copy()
    out[y0:y1, x0:x1] = retocar(frame[y0:y1, x0:x1], pts - [x0, y0], v)
    return out


def info(video):
    s = json.loads(subprocess.run(["ffprobe", "-v", "error", "-select_streams", "v:0", "-show_entries",
                                   "stream=width,height,r_frame_rate:stream_side_data=rotation", "-of", "json",
                                   video], capture_output=True, text=True).stdout)["streams"][0]
    w, h = s["width"], s["height"]
    rot = next((d.get("rotation", 0) for d in s.get("side_data_list", [])), 0)
    if abs(rot) in (90, 270):
        w, h = h, w
    n, d = s["r_frame_rate"].split("/")
    return w, h, s["r_frame_rate"], float(n) / float(d)


def processar(video, saida, v):
    w, h, taxa, fps = info(video)
    ler = subprocess.Popen(["ffmpeg", "-v", "error", "-i", video, "-f", "rawvideo", "-pix_fmt", "bgr24", "-"],
                           stdout=subprocess.PIPE)
    gravar = subprocess.Popen(["ffmpeg", "-v", "error", "-y", "-f", "rawvideo", "-pix_fmt", "bgr24",
                               "-s", f"{w}x{h}", "-r", taxa, "-i", "-", "-i", video, "-map", "0:v", "-map", "1:a",
                               *plataforma.hevc("80M"), "-pix_fmt", "yuv420p",
                               "-c:a", "copy", "-shortest", saida], stdin=subprocess.PIPE)
    rosto, tam, n, sem = Rosto(fps), w * h * 3, 0, 0
    while True:
        buf = ler.stdout.read(tam)
        if len(buf) < tam:
            break
        f = np.frombuffer(buf, np.uint8).reshape(h, w, 3)
        p = rosto.pontos(f)
        sem += p is None
        gravar.stdin.write(quadro(f, p, v).tobytes())
        n += 1
        if n % 300 == 0:
            print(f"  {n / fps:6.1f}s", flush=True)
    gravar.stdin.close()
    gravar.wait(); ler.wait()
    if gravar.returncode:
        sys.exit("falha ao gravar " + saida)
    print(f"{n} quadros; sem rosto em {sem}; -> {saida}")


def amostras(video, pasta, tempos, v):
    os.makedirs(pasta, exist_ok=True)
    w, h, _, fps = info(video)
    for t in tempos:
        # alguns quadros antes, para o rastreio e a suavização chegarem como no vídeo
        ler = subprocess.Popen(["ffmpeg", "-v", "error", "-ss", f"{max(0, t - 0.3):.3f}", "-i", video, "-frames:v",
                                "10", "-f", "rawvideo", "-pix_fmt", "bgr24", "-"], stdout=subprocess.PIPE)
        rosto, f, p = Rosto(fps), None, None
        while True:
            buf = ler.stdout.read(w * h * 3)
            if len(buf) < w * h * 3:
                break
            f = np.frombuffer(buf, np.uint8).reshape(h, w, 3)
            p = rosto.pontos(f)
        ler.wait()
        if p is None:
            print(f"{t}s: sem rosto"); continue
        larg = np.ptp(p[:, 0])
        x0, y0 = np.maximum(p.min(0) - larg * 0.1, 0).astype(int)
        x1, y1 = np.minimum(p.max(0) + larg * 0.1, [w, h]).astype(int)
        antes, depois = f[y0:y1, x0:x1], quadro(f, p, v)[y0:y1, x0:x1]
        lado = np.hstack([antes, depois])
        cv2.imwrite(os.path.join(pasta, f"retoque_{t:06.2f}.jpg"), lado, [cv2.IMWRITE_JPEG_QUALITY, 92])
        print(f"{t}s: {os.path.join(pasta, f'retoque_{t:06.2f}.jpg')}")


def trocar_midia(projeto, saida):
    sys.path.insert(0, AQUI)
    from concat_api import timeline
    from reel import api_de
    api = api_de(projeto)
    antes = {m["id"] for m in api.view()["project"]["media"]}
    api.call("media.import", path=projeto, file=os.path.abspath(saida))
    midias = api.view()["project"]["media"]
    alvo = os.path.abspath(saida)
    novo = next((m for m in midias if m["id"] not in antes), None) or next(m for m in midias if m["path"] == alvo)
    campos = ("path", "name", "duration", "kind", "width", "height", "frameRate", "frameRateFraction",
              "videoCodec", "audioCodec", "hasAudio", "audioTracks", "colorSpace")
    item = {k: novo[k] for k in campos if k in novo}
    velhos = [c for c in timeline(api.view())["clips"] if c["kind"] == "video" and c["mediaId"] != novo["id"]]
    # como "Enhance": o clipe guarda o original e dá para voltar a ele (setClipEnhanced)
    api.batch([{"op": "replaceClipMedia", "clipId": c["id"], "item": item, "enhanced": True} for c in velhos])
    api.call("project.save", path=projeto)
    print(f"{len(velhos)} clipes agora usam {os.path.basename(saida)} ({novo['id']})")


if __name__ == "__main__":
    args = [a for a in sys.argv[1:] if not a.startswith("--")]
    opc = dict(a[2:].split("=", 1) for a in sys.argv[1:] if a.startswith("--") and "=" in a)
    if len(args) < 2:
        sys.exit(__doc__)
    if "--quadros" in sys.argv:
        i = sys.argv.index("--quadros")
        opc["quadros"] = sys.argv[i + 1]
        args = [a for a in args if a != opc["quadros"]]
    if "--projeto" in sys.argv:
        i = sys.argv.index("--projeto")
        opc["projeto"] = sys.argv[i + 1]
        args = [a for a in args if a != opc["projeto"]]
    v = {k: float(opc.get(k, d)) for k, d in PADRAO.items()}
    video, saida = args[0], args[1]
    if "quadros" in opc:
        amostras(video, saida, [float(t) for t in opc["quadros"].split()], v)
    else:
        processar(video, saida, v)
        if "projeto" in opc:
            trocar_midia(opc["projeto"], saida)
