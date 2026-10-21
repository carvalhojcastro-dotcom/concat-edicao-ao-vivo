"""Enquadramento sem pulo no eixo X (pedido do usuário, 2026-10-20).

Uso: estabilizar.py <corte.json> [zoom=1.12]
- Cada pessoa (câmera + posição) tem UM X no plano normal (z=1): a mediana ponderada do corte inteiro.
  Assim, de um take para o outro, a pessoa não muda de lugar.
- Nas trocas de take da mesma pessoa, alterna um zoom leve (z=1 <-> z=zoom). Só no plano com zoom o X
  segue o rosto daquele take (o zoom disfarça o reenquadramento).
- Peças curtas (< 1 s) herdam o zoom da anterior, para não piscar.
"""
import json, sys

cam = sys.argv[1]
ZOOM = float(sys.argv[2]) if len(sys.argv) > 2 else 1.12
cfg = json.load(open(cam))
ps = cfg["pecas"]


def chave(p):
    return (p["layout"], p["quem"])


base = {}
for k in {chave(p) for p in ps if not p.get("wide")}:
    xs = sorted((p["cx"], p["e"] - p["s"]) for p in ps if chave(p) == k and not p.get("wide"))
    tot, acc = sum(d for _, d in xs), 0
    for x, d in xs:
        acc += d
        if acc >= tot / 2:
            base[k] = x
            break
ultimo_z, ant = {}, None
for p in ps:
    if p.get("wide"):
        ant = None
        continue
    k = chave(p)
    p["cx_face"] = p.get("cx_face", p["cx"])
    if p["e"] - p["s"] < 1.0 and ant is not None and chave(ant) == k:
        z = ant["z"]
    elif k in ultimo_z:
        z = 1.0 if ultimo_z[k] > 1.0 else ZOOM
    else:
        z = 1.0
    if z == 1.0 and abs(p["cx_face"] - base[k]) > 0.035:   # rosto longe do X fixo: entra com zoom e recentraliza
        z = ZOOM
    p["z"] = z
    p["cx"] = base[k] if z == 1.0 else p["cx_face"]
    ultimo_z[k] = z
    ant = p
json.dump(cfg, open(cam, "w"), ensure_ascii=False, indent=1)
for p in ps:
    print(f'{p["s"]:9.2f}-{p["e"]:9.2f} {p["layout"]:6s} {p["quem"]:5s} z={p.get("z", 1):.2f} cx={p["cx"]:.3f}')
