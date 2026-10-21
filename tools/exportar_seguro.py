#!/usr/bin/env python3
"""Exporta um projeto mesmo se ele estiver aberto na janela do Concat (via cópia temporária que é apagada
e tirada da lista de projetos no fim - ver render_projeto.py).
Uso: exportar_seguro.py <projeto> <saida.mp4> [largura altura]   (padrão 4K 2160x3840, crf 18)"""
import json, os, sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from render_projeto import projeto_para_render  # noqa: E402

path, out = sys.argv[1], os.path.abspath(sys.argv[2])
w, h = (int(sys.argv[3]), int(sys.argv[4])) if len(sys.argv) > 4 else (2160, 3840)
with projeto_para_render(path) as (api, alvo):
    api.sock.settimeout(3600)
    job = api.call("export.run", path=alvo, output=out, width=w, height=h, crf=18, preset="medium", hdr=False)  # SDR como a prévia (vídeo de iPhone é HLG; HDR deixa legenda e B-roll cinza)
    print("exportando", os.path.basename(path), "de", "cópia temporária" if alvo != os.path.abspath(path) else "projeto", flush=True)
    ultimo = -1
    while True:
        ev = json.loads(api.file.readline())
        m, p = ev.get("method", ""), ev.get("params", {})
        if m == "export.progress":
            pct = int(100 * (p.get("progress") or p.get("fraction") or 0))
            if pct // 25 != ultimo // 25:
                print(f"  {pct}%", flush=True); ultimo = pct
        elif m == "export.done":
            print("pronto:", out); break
        elif m == "export.failed":
            sys.exit(f"falhou: {p}")
