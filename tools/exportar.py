#!/usr/bin/env python3
"""Exporta um projeto do Concat pela API e espera terminar.
Uso: exportar.py <projeto> <saida.mp4> [largura altura]   (padrão 4K 2160x3840, crf 18)"""
import json, os, sys, time
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from concat_api import Concat

path, out = sys.argv[1], os.path.abspath(sys.argv[2])
w, h = (int(sys.argv[3]), int(sys.argv[4])) if len(sys.argv) > 4 else (2160, 3840)  # sempre 4K (pedido do usuário)
api = Concat(path); api.sock.settimeout(3600)
api.call("project.open", path=path)
job = api.call("export.run", path=path, output=out, width=w, height=h, crf=18, preset="medium", hdr=False)  # SDR como a prévia (vídeo de iPhone é HLG; HDR deixa legenda e B-roll cinza)
print("exportando", job, flush=True)
ultimo = -1
while True:
    ev = json.loads(api.file.readline())
    m, p = ev.get("method", ""), ev.get("params", {})
    if m == "export.progress":
        pct = int(100 * (p.get("progress") or p.get("fraction") or 0))
        if pct // 10 != ultimo // 10:
            print(f"  {pct}%", flush=True); ultimo = pct
    elif m == "export.done":
        print("pronto:", out); break
    elif m == "export.failed":
        sys.exit(f"falhou: {p}")
