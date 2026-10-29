#!/usr/bin/env python3
"""Caixinha de perguntas do Instagram e zoom por grupos de frases num projeto do CapCut já cortado.

Pedido de 2026-10-29 (Dr. Rafael, "11 - Caixinha de perguntas Reposição hormonal"): os cortes e a velocidade
já estão feitos e o médico já está centralizado (eixo X). Entram:
  - a caixinha com a pergunta que ele lê no começo, o vídeo todo, acima da cabeça (PNG do tamanho do quadro,
    numa trilha "Caixinha (Concat)" por cima do vídeo e abaixo das legendas);
  - zoom in / zoom out por grupos de cortes, sempre começando e terminando junto com uma frase. O
    enquadramento dela é o "aberto"; no zoom in o X acompanha a escala (o centro que ela escolheu continua no
    centro) e o Y vem do plano (a cabeça não pode subir até a caixinha).

O CapCut precisa estar FECHADO. Backup em ~/Desktop/Concat/backup-capcut/. Rodar de novo refaz os dois.
Uso: capcut_caixinha.py <pasta do projeto no CapCut> <plano.json>
plano.json: {"pergunta": "Reposição hormonal protege o coração?", "cabecalho": "Faça uma pergunta",
             "avatar": "<foto quadrada do rosto>", "base_caixinha": 470,      (px do quadro 1080x1920)
             "base": {"escala": 1.15, "x": -0.1218, "y": -0.0172},          (o enquadramento dela)
             "zoom": [{"inicio": 0, "fim": 2.47, "escala": 1.4, "y": -0.0958}, ...]}   (sem item: fica a base)
"""
import copy
import glob
import json
import os
import shutil
import subprocess
import sys
import time
import uuid

from PIL import Image, ImageDraw, ImageFilter, ImageFont

AQUI = os.path.dirname(os.path.abspath(__file__))
FONTES = os.path.abspath(os.path.join(AQUI, "..", "fonts"))
PASTA = os.path.expanduser("~/Movies/CapCut/User Data/Caixinhas Concat")       # o CapCut (sandbox) só lê daqui
PASTA_VISTA = os.path.expanduser("~/Library/Containers/com.lemon.lvoverseas/Data/Movies/CapCut/User Data/Caixinhas Concat")
RAIZ = os.path.expanduser("~/Movies/CapCut/User Data/Projects/com.lveditor.draft")
MODELO_FOTO = "5 - Braços definidos"     # projeto dela com foto numa trilha de cima (material e segmento de modelo)
NOME_TRILHA = "Caixinha (Concat)"
W, H, K = 1080, 1920, 2                  # quadro do CapCut; o PNG sai em 2x para ficar nítido no 4K
GRADIENTE = [(118, 56, 250), (211, 0, 197), (255, 0, 105), (255, 122, 0)]   # cores do Instagram

novo_id = lambda: str(uuid.uuid4()).upper()  # noqa: E731


def fonte(nome, px):
    return ImageFont.truetype(os.path.join(FONTES, nome), int(round(px * K)))


def quebrar(texto, f, largura):
    linhas, atual = [], ""
    for p in texto.split():
        teste = (atual + " " + p).strip()
        if atual and f.getlength(teste) > largura:
            linhas.append(atual)
            atual = p
        else:
            atual = teste
    return linhas + [atual]


def caixinha_png(pergunta, cabecalho, avatar, base_y, saida):
    """Figurinha de pergunta respondida: foto redonda no topo, faixa em gradiente com o cabeçalho e a pergunta
    em preto sobre branco. Centrada em X; base_y é a borda de baixo, em px do quadro 1080x1920."""
    larg, raio, topo_h, av = 660, 34, 100, 96
    f_cab, f_perg = fonte("HelveticaNeue-Medium.ttf", 31), fonte("Helvetica-Bold.ttf", 44)
    linhas = quebrar(pergunta, f_perg, (larg - 90) * K)
    entre = 54
    alt = topo_h + 50 + entre * (len(linhas) - 1) + 50
    x0, y0 = (W - larg) / 2, base_y - alt

    img = Image.new("RGBA", (W * K, H * K), (0, 0, 0, 0))
    # sombra suave sob o cartão
    sombra = Image.new("L", img.size, 0)
    ImageDraw.Draw(sombra).rounded_rectangle([x0 * K, (y0 + 10) * K, (x0 + larg) * K, (base_y + 10) * K], raio * K, fill=110)
    img.putalpha(0)
    img = Image.composite(Image.new("RGBA", img.size, (0, 0, 0, 255)), img, sombra.filter(ImageFilter.GaussianBlur(18 * K)))

    cartao = Image.new("RGBA", (larg * K, alt * K), (255, 255, 255, 255))
    grad = Image.new("RGBA", (larg * K, topo_h * K))
    gd = ImageDraw.Draw(grad)
    n = len(GRADIENTE) - 1
    for x in range(larg * K):
        t = x / (larg * K - 1) * n
        i = min(int(t), n - 1)
        a, b = GRADIENTE[i], GRADIENTE[i + 1]
        gd.line([(x, 0), (x, topo_h * K)], fill=tuple(int(a[c] + (b[c] - a[c]) * (t - i)) for c in range(3)) + (255,))
    cartao.paste(grad, (0, 0))
    d = ImageDraw.Draw(cartao)
    d.text((larg * K / 2, (topo_h - 25) * K), cabecalho, font=f_cab, fill="white", anchor="mm")
    y = topo_h + 50
    for ln in linhas:
        d.text((larg * K / 2, y * K), ln, font=f_perg, fill=(38, 38, 38), anchor="mm")
        y += entre
    mascara = Image.new("L", cartao.size, 0)
    ImageDraw.Draw(mascara).rounded_rectangle([0, 0, cartao.size[0] - 1, cartao.size[1] - 1], raio * K, fill=255)
    img.paste(cartao, (int(x0 * K), int(y0 * K)), mascara)

    # foto redonda com aro branco, metade para fora do cartão
    if avatar:
        aro = 6
        foto = Image.open(avatar).convert("RGB").resize((av * K, av * K), Image.LANCZOS)
        disco = Image.new("L", (av * K, av * K), 0)
        ImageDraw.Draw(disco).ellipse([0, 0, av * K - 1, av * K - 1], fill=255)
        cx, cy = W / 2, y0
        ImageDraw.Draw(img).ellipse([(cx - av / 2 - aro) * K, (cy - av / 2 - aro) * K, (cx + av / 2 + aro) * K, (cy + av / 2 + aro) * K],
                                    fill="white")
        img.paste(foto, (int((cx - av / 2) * K), int((cy - av / 2) * K)), disco)
    img.save(saida)
    return y0 - (av / 2 + 6 if avatar else 0)


def material(d, mid):
    for k, v in d["materials"].items():
        if isinstance(v, list):
            for m in v:
                if isinstance(m, dict) and m.get("id") == mid:
                    return k, m
    return None, None


def main():
    pasta, plano = os.path.abspath(sys.argv[1]), json.load(open(sys.argv[2], encoding="utf-8"))
    if not os.environ.get("CAPCUT_TESTE") and subprocess.run(["pgrep", "-x", "CapCut"], capture_output=True).returncode == 0:
        sys.exit("feche o CapCut antes (ele regrava o projeto aberto por cima)")
    alvos = [p for p in [os.path.join(pasta, "draft_info.json")] + glob.glob(os.path.join(pasta, "Timelines", "*", "draft_info.json"))
             if os.path.exists(p)]
    d = json.load(open(alvos[0], encoding="utf-8"))
    copia = os.path.expanduser(f"~/Desktop/Concat/backup-capcut/{os.path.basename(pasta)} {time.strftime('%Y-%m-%d %H%M%S')}")
    while os.path.exists(copia):   # duas ferramentas no mesmo segundo não podem dividir a pasta do backup
        copia += "+"
    for p in glob.glob(os.path.join(pasta, "*.json")) + glob.glob(os.path.join(pasta, "*.tmp")) + glob.glob(os.path.join(pasta, "Timelines", "**", "*"), recursive=True):
        if os.path.isfile(p):
            destino = os.path.join(copia, os.path.relpath(p, pasta))
            os.makedirs(os.path.dirname(destino), exist_ok=True)
            shutil.copy2(p, destino)

    # zoom: cada corte da trilha principal pega o enquadramento do grupo em que começa
    principal = next(t for t in d["tracks"] if t["type"] == "video")
    base = plano["base"]
    trocas = 0
    for s in principal["segments"]:
        ini = s["target_timerange"]["start"] / 1e6
        g = next((z for z in plano.get("zoom", []) if z["inicio"] - 0.02 <= ini < z["fim"] - 0.02), None)
        esc = g["escala"] if g else base["escala"]
        y = g.get("y", base["y"]) if g else base["y"]
        s["clip"]["scale"] = {"x": esc, "y": esc}
        s["clip"]["transform"] = {"x": round(base["x"] * esc / base["escala"], 6), "y": y}
        trocas += bool(g)

    # caixinha: foto do tamanho do quadro numa trilha por cima do vídeo, o vídeo todo
    d["tracks"] = [t for t in d["tracks"] if t.get("name") != NOME_TRILHA]
    os.makedirs(PASTA, exist_ok=True)
    nome = os.path.basename(pasta)[:60] + ".png"
    topo = caixinha_png(plano["pergunta"], plano.get("cabecalho", "Faça uma pergunta"), plano.get("avatar"),
                        plano.get("base_caixinha", 470), os.path.join(PASTA, nome))
    M = json.load(open(os.path.join(RAIZ, MODELO_FOTO, "draft_info.json"), encoding="utf-8"))
    tr_mod, seg_mod = next((t, s) for t in M["tracks"] if t["type"] == "video" for s in t["segments"]
                           if material(M, s["material_id"])[1].get("type") == "photo")
    _, mat_mod = material(M, seg_mod["material_id"])
    m = dict(copy.deepcopy(mat_mod), id=novo_id(), path=os.path.join(PASTA_VISTA, nome), width=W * K, height=H * K,
             material_name=nome, category_name="local", local_material_id="")
    d["materials"]["videos"].append(m)
    refs = []
    for r in seg_mod["extra_material_refs"]:
        k, mm = material(M, r)
        if mm is None or k == "material_animations":
            continue
        mm = dict(copy.deepcopy(mm), id=novo_id())
        d["materials"].setdefault(k, []).append(mm)
        refs.append(mm["id"])
    s = copy.deepcopy(seg_mod)
    s.update(id=novo_id(), material_id=m["id"], extra_material_refs=refs, common_keyframes=[], keyframe_refs=[],
             source_timerange={"start": 0, "duration": d["duration"]}, target_timerange={"start": 0, "duration": d["duration"]},
             render_index=0, volume=1.0)
    s["clip"] = {"scale": {"x": 1.0, "y": 1.0}, "rotation": 0.0, "transform": {"x": 0.0, "y": 0.0},
                 "flip": {"vertical": False, "horizontal": False}, "alpha": 1.0}
    tr = dict(copy.deepcopy({k: v for k, v in tr_mod.items() if k != "segments"}), id=novo_id(), name=NOME_TRILHA,
              is_default_name=False, segments=[s])
    d["tracks"].insert(d["tracks"].index(principal) + 1, tr)
    if d.get("render_index_track_mode_on"):   # o CapCut empilha pela ordem das trilhas
        for i, t in enumerate(d["tracks"]):
            for seg in t["segments"]:
                seg["track_render_index"] = i

    texto = json.dumps(d, ensure_ascii=False, separators=(",", ":"))
    for p in alvos:
        open(p, "w", encoding="utf-8").write(texto)
        tmp = os.path.join(os.path.dirname(p), "template-2.tmp")
        if os.path.exists(tmp):
            open(tmp, "w", encoding="utf-8").write(texto)
    print(f"zoom em {trocas} de {len(principal['segments'])} cortes; caixinha {nome} (topo em {topo:.0f}px); backup em {copia}")


if __name__ == "__main__":
    main()
