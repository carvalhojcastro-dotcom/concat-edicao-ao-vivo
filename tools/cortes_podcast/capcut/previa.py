"""Folha de revisão de um corte já gravado no CapCut, sem abrir o CapCut: lê a trilha principal (escala, posição,
keyframes de X, velocidade), desenha o quadro do bruto como o CapCut, a headline (caixa branca aproximada) e as
legendas IG (capcut_legendas_ig.desenhar).
Uso: previa.py <pasta do projeto> <words_leg.json> <blocos.json> <saida.jpg> "t1,t2,..." """
import json, os, subprocess, sys, tempfile
import numpy as np
from PIL import Image, ImageDraw, ImageFont
TOOLS = os.path.abspath(os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", ".."))
sys.path.insert(0, TOOLS)
import capcut_legendas_ig as ig  # noqa: E402

FONTE = os.path.join(TOOLS, "..", "fonts", "Poppins-SemiBold.ttf")
pasta, words_arq, blocos_arq, saida, tempos = sys.argv[1:6]
D = json.load(open(os.path.join(pasta, "draft_info.json"), encoding="utf-8"))
mats = {m["id"]: m for m in D["materials"]["videos"]}
princ = next(t for t in D["tracks"] if t["type"] == "video")
segs = sorted(princ["segments"], key=lambda s: s["target_timerange"]["start"])
total = D["duration"] / 1e6
itens = ig.montar(json.load(open(words_arq, encoding="utf-8")), json.load(open(blocos_arq, encoding="utf-8")))
for it in itens:
    it["fim"] = min(it["fim"], total - 2 / 30)
head = next((t for t in D["tracks"] if t.get("name") == "Headline"), None)
txts = {m["id"]: m for m in D["materials"]["texts"]}
png = os.path.join(tempfile.mkdtemp(), "q.png")
quadros = []
for t in (float(x) for x in tempos.split(",")):
    s = next(s for s in segs if s["target_timerange"]["start"] / 1e6 <= t < (s["target_timerange"]["start"] + s["target_timerange"]["duration"]) / 1e6)
    src = s["source_timerange"]["start"] / 1e6 + (t - s["target_timerange"]["start"] / 1e6) * s.get("speed", 1.0)
    tx, ty, esc = s["clip"]["transform"]["x"], s["clip"]["transform"]["y"], s["clip"]["scale"]["x"]
    for kf in s.get("common_keyframes", []):
        if kf["property_type"] == "KFTypePositionX":
            ks = [(k["time_offset"] / 1e6, k["values"][0]) for k in kf["keyframe_list"]]
            tx = float(np.interp(src, [a for a, _ in ks], [b for _, b in ks]))
    video = mats[s["material_id"]]["path"].replace("/Library/Containers/com.lemon.lvoverseas/Data", "")
    subprocess.run(["ffmpeg", "-v", "error", "-y", "-ss", f"{src:.3f}", "-i", video, "-frames:v", "1", png], check=True)
    q = Image.open(png).convert("RGB")
    w = int(1080 * esc)
    h = int(w * q.height / q.width)
    img = Image.new("RGB", (1080, 1920))
    img.paste(q.resize((w, h)), (int(540 - w / 2 + tx * 540), int(960 - h / 2 - ty * 960)))
    if head:
        hs = head["segments"][0]
        if hs["target_timerange"]["start"] / 1e6 <= t < (hs["target_timerange"]["start"] + hs["target_timerange"]["duration"]) / 1e6:
            texto = json.loads(txts[hs["material_id"]]["content"])["text"]
            dr = ImageDraw.Draw(img)
            k = hs["clip"]["scale"]["x"] / 0.80
            f = ImageFont.truetype(FONTE, int(58 * k))
            linhas = texto.split("\n")
            lh = int(66 * k)
            larg = max(dr.textlength(l, font=f) for l in linhas)
            y0 = 960 - hs["clip"]["transform"]["y"] * 960 - lh * len(linhas) / 2
            dr.rectangle([540 - larg / 2 - 30 * k, y0 - 22 * k, 540 + larg / 2 + 30 * k, y0 + lh * len(linhas) + 22 * k], fill="white")
            for i, l in enumerate(linhas):
                dr.text((540 - dr.textlength(l, font=f) / 2, y0 + i * lh), l, font=f, fill="black")
    out = Image.fromarray(np.asarray(ig.desenhar(itens, t, np.array(img)))).convert("RGB").resize((270, 480))
    ImageDraw.Draw(out).text((6, 4), f"{t:.1f}s", fill="yellow")
    quadros.append(out)
col = 6
folha = Image.new("RGB", (270 * col, 480 * ((len(quadros) + col - 1) // col)))
for i, q in enumerate(quadros):
    folha.paste(q, (270 * (i % col), 480 * (i // col)))
folha.save(saida, quality=88)
print(saida)
