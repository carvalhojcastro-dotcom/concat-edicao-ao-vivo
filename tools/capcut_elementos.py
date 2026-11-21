#!/usr/bin/env python3
"""Põe elementos gráficos em PNG (lower third, selo de localização, cartão...) num projeto do CapCut, cada um na sua
trilha, para a usuária poder copiar e colar o elemento sozinho em outros vídeos.

Pedido de 2026-11-13 (anúncios da Dra. Daniella Varela): "um lower third com 'Dra. Daniella Varela' e embaixo
'Cirurgiã Plástica'" e "um elemento separado, com fundo branco, com um pin de localização e 'Barra da Tijuca'. Ele
tem que ser um elemento próprio, que eu consiga copiar e colar em outros vídeos".
Segue o cartão de nome aprovado do Dr. Leonardo: PNG de tela cheia (mesma proporção do quadro, escala 1, sem
deslocamento; colado em outro projeto 9:16 ele cai no mesmo lugar), foto local (material_id "" e source 0: com o id
da biblioteca o CapCut troca a foto por uma imagem branca ao exportar) e as animações nativas "Fade-in"/"Fade-out" do
CapCut dela.

Uso: capcut_elementos.py <pasta do projeto no CapCut> <plano.json>
  plano.json: {"elementos": [{"png": "<arquivo>", "trilha": "Lower third", "inicio": 0.3, "fim": 4.9,
                              "ty": 0.0, "fade_in": 0.5, "fade_out": 0.4}, ...]}
  ty: deslocamento vertical no padrão do CapCut (meia altura do quadro = 1, positivo para cima), ex. -0.04 desce 2%.
  Opcionais: "tx" (idem, na horizontal), "escala" (1 = cobre o quadro), "trechos": [[ini, fim], ...] no lugar de
  inicio/fim (vários pedaços na mesma trilha, ex. sumir nos B-rolls), "fade_in_retorno" (fade de volta, padrão 0,3).
O CapCut precisa estar FECHADO. Backup em ~/Desktop/Claude Code Skills/backup-capcut/. Rodar de novo troca os
elementos das mesmas trilhas.
"""
import copy
import glob
import json
import os
import shutil
import subprocess
import sys
import time

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from capcut_montar import material, segmento_de, novo_id, us  # noqa: E402

RAIZ = os.path.expanduser("~/Movies/CapCut/User Data/Projects/com.lveditor.draft")
PASTA = os.path.expanduser("~/Movies/CapCut/User Data/Broll Concat")
PASTA_VISTA = os.path.expanduser("~/Library/Containers/com.lemon.lvoverseas/Data/Movies/CapCut/User Data/Broll Concat")
MODELO_FOTO = "3 - Efeitos colaterais graves do Mounjaro"     # cartão de nome do Dr. Leonardo (foto com Fade-in)


def animacao_nativa(nome, tipo):
    """Uma animação de vídeo do CapCut que já está no cache dela (procura nos projetos)."""
    for f in glob.glob(os.path.join(RAIZ, "*", "draft_info.json")):
        try:
            d = json.load(open(f, encoding="utf-8"))
        except (OSError, ValueError):
            continue
        for m in d.get("materials", {}).get("material_animations", []):
            for a in m.get("animations", []):
                if a.get("name") == nome and a.get("type") == tipo and a.get("panel") == "video" and os.path.exists(a.get("path", "")):
                    return copy.deepcopy(a)
    sys.exit(f"animação \"{nome}\" não encontrada no cache do CapCut")


def main():
    pasta, plano = os.path.abspath(sys.argv[1]), json.load(open(sys.argv[2], encoding="utf-8"))
    if not os.environ.get("CAPCUT_TESTE") and subprocess.run(["pgrep", "-x", "CapCut"], capture_output=True).returncode == 0:
        sys.exit("feche o CapCut antes (ele regrava o projeto aberto por cima)")
    alvos = [p for p in [os.path.join(pasta, "draft_info.json")] + glob.glob(os.path.join(pasta, "Timelines", "*", "draft_info.json"))
             if os.path.exists(p)]
    N = json.load(open(alvos[0], encoding="utf-8"))
    B = json.load(open(os.path.join(RAIZ, MODELO_FOTO, "draft_info.json"), encoding="utf-8"))
    copia = os.path.expanduser(f"~/Desktop/Claude Code Skills/backup-capcut/{os.path.basename(pasta)} {time.strftime('%Y-%m-%d %H%M%S')}")
    while os.path.exists(copia):
        copia += "+"
    for p in glob.glob(os.path.join(pasta, "*.json")) + glob.glob(os.path.join(pasta, "*.tmp")) + glob.glob(os.path.join(pasta, "Timelines", "**", "*"), recursive=True):
        if os.path.isfile(p):
            destino = os.path.join(copia, os.path.relpath(p, pasta))
            os.makedirs(os.path.dirname(destino), exist_ok=True)
            shutil.copy2(p, destino)

    trilha_mod, foto_seg = next((t, s) for t in B["tracks"] if t["type"] == "video" for s in t["segments"]
                                if "cartao" in (material(B, s["material_id"])[1] or {}).get("path", "").lower())
    _, foto_mat = material(B, foto_seg["material_id"])
    anim_mod = next(m for r in foto_seg["extra_material_refs"] for k, m in [material(B, r)] if k == "material_animations")
    fade_in, fade_out = animacao_nativa("Fade-in", "in"), animacao_nativa("Fade-out", "out")

    nomes = {e["trilha"] for e in plano["elementos"]}
    velhas = [t for t in N["tracks"] if t.get("name") in nomes]
    ids = {s["material_id"] for t in velhas for s in t["segments"]} | {r for t in velhas for s in t["segments"] for r in s.get("extra_material_refs", [])}
    N["tracks"] = [t for t in N["tracks"] if t not in velhas]
    for k, v in N["materials"].items():
        if isinstance(v, list):
            N["materials"][k] = [m for m in v if not (isinstance(m, dict) and m.get("id") in ids)]

    destino = os.path.join(PASTA, os.path.basename(pasta)[:60])
    os.makedirs(destino, exist_ok=True)
    render = max([s.get("render_index", 0) for t in N["tracks"] for s in t["segments"]] + [0]) + 1
    from PIL import Image
    for e in plano["elementos"]:
        arq = os.path.join(destino, os.path.basename(e["png"]))
        shutil.copy2(e["png"], arq)
        larg, alt = Image.open(arq).size
        m = dict(copy.deepcopy(foto_mat), id=novo_id(), path=os.path.join(PASTA_VISTA, os.path.basename(destino), os.path.basename(arq)),
                 width=larg, height=alt, material_name=os.path.basename(arq), material_id="", source=0, source_platform=0,
                 category_id="", category_name="local", local_material_id=novo_id().lower(), md5="")
        N["materials"].setdefault("videos", []).append(m)
        # "trechos": o elemento em pedaços na mesma trilha, ex. o lower third que some nos B-rolls e volta quando a
        # doutora reaparece (2026-11-13). Entra com fade no 1º pedaço (fade_in) e mais curto nas voltas
        # (fade_in_retorno); sai com fade só no último (os outros cortam junto com o corte para o B-roll).
        trechos = e.get("trechos") or [[e["inicio"], e["fim"]]]
        esc = e.get("escala", 1.0)
        tr = dict(copy.deepcopy({k: v for k, v in trilha_mod.items() if k != "segments"}), id=novo_id(), name=e["trilha"],
                  is_default_name=False, segments=[])
        for n, (ini, fim) in enumerate(trechos):
            ini, fim = round(ini * 30) / 30, round(fim * 30) / 30
            dur = fim - ini
            s = segmento_de(foto_seg, B, N, m["id"], 0.0, dur, ini, dur)
            s["extra_material_refs"] = [r for r in s["extra_material_refs"] if material(N, r)[0] != "material_animations"]
            anims = []
            f_in = e.get("fade_in", 0.5) if n == 0 else e.get("fade_in_retorno", 0.3)
            f_out = e.get("fade_out", 0.4) if n == len(trechos) - 1 else 0.0
            if f_in > 0:
                anims.append(dict(copy.deepcopy(fade_in), start=0, duration=us(f_in)))
            if f_out > 0:
                anims.append(dict(copy.deepcopy(fade_out), start=us(dur) - us(f_out), duration=us(f_out)))
            anim = dict(copy.deepcopy(anim_mod), id=novo_id(), animations=anims)
            N["materials"].setdefault("material_animations", []).append(anim)
            s["extra_material_refs"].append(anim["id"])
            s["clip"] = {"scale": {"x": esc, "y": esc}, "rotation": 0.0, "alpha": 1.0, "flip": {"vertical": False, "horizontal": False},
                         "transform": {"x": e.get("tx", 0.0), "y": e.get("ty", 0.0)}}
            s["uniform_scale"] = {"on": True, "value": 1.0}
            s["volume"] = 1.0
            s["render_index"] = render
            tr["segments"].append(s)
        render += 1
        N["tracks"].append(tr)
    if N.get("render_index_track_mode_on"):
        for i, t in enumerate(N["tracks"]):
            for seg in t["segments"]:
                seg["track_render_index"] = i
    texto = json.dumps(N, ensure_ascii=False, separators=(",", ":"))
    for p in alvos:
        open(p, "w", encoding="utf-8").write(texto)
        tmp = os.path.join(os.path.dirname(p), "template-2.tmp")
        if os.path.exists(tmp):
            open(tmp, "w", encoding="utf-8").write(texto)
    print(f"{len(plano['elementos'])} elementos ({', '.join(e['trilha'] for e in plano['elementos'])}); backup em {copia}")


if __name__ == "__main__":
    main()
