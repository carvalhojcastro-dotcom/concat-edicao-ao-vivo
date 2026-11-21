"""Headline no começo do corte, no molde da trilha "Headline" do "12 - Linda pro Natal" (caixa branca, Poppins SemiBold
preta), no lugar e no tamanho em que o usuário deixou as dos cortes da Dra. Daniella (y 0 = centro da tela, escala ~0,80).
Sem blocos dinâmicos de legenda enquanto ela está na tela.
Uso: headline.py <pasta do projeto> "<texto, \\n quebra a linha>" <duração s> [y] [escala]   (CapCut FECHADO)"""
import copy, json, os, sys
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "..")))
import capcut_simples as C  # noqa: E402

RAIZ = os.path.expanduser("~/Movies/CapCut/User Data/Projects/com.lveditor.draft/")
NOME = "Headline"
pasta, texto, dur = sys.argv[1], sys.argv[2].replace("\\n", "\n"), float(sys.argv[3])
y = float(sys.argv[4]) if len(sys.argv) > 4 else 0.0
escala = float(sys.argv[5]) if len(sys.argv) > 5 else 0.80
M = json.load(open(RAIZ + "12 - Linda pro Natal/draft_info.json", encoding="utf-8"))
TM = next(t for t in M["tracks"] if t.get("name") == "Headline")
SM = TM["segments"][0]

C.backup(pasta, "antes da headline")
N = json.load(open(C.alvos(pasta)[0], encoding="utf-8"))
C.tirar_trilhas(N, [NOME])
k, mat = C.material_de(M, SM["material_id"])
mat = copy.deepcopy(mat)
cont = json.loads(mat["content"])
cont["styles"] = [dict(cont["styles"][0], range=[0, len(texto)])]
cont["text"] = texto
mat.update(id=C.novo_id(), content=json.dumps(cont, ensure_ascii=False), name="")
N["materials"].setdefault(k, []).append(mat)
refs = []
for r in SM["extra_material_refs"]:
    kr, mr = C.material_de(M, r)
    if mr is None:
        continue
    mr = dict(copy.deepcopy(mr), id=C.novo_id())
    N["materials"].setdefault(kr, []).append(mr)
    refs.append(mr["id"])
s = copy.deepcopy(SM)
s.update(id=C.novo_id(), material_id=mat["id"], extra_material_refs=refs,
         target_timerange={"start": 0, "duration": C.us(round(dur * 30) / 30)},
         render_index=max(x.get("render_index", 0) for t in N["tracks"] for x in t["segments"]) + 1,
         common_keyframes=[], keyframe_refs=[])
s["clip"] = dict(copy.deepcopy(SM["clip"]), scale={"x": escala, "y": escala}, transform={"x": 0.0, "y": y})
N["tracks"].append(dict(copy.deepcopy({kk: v for kk, v in TM.items() if kk != "segments"}), id=C.novo_id(), name=NOME, segments=[s]))
C.reindexar(N)
C.gravar(pasta, N)
print(os.path.basename(pasta), "| headline:", repr(texto), f"0-{dur}s y={y} escala={escala}")
