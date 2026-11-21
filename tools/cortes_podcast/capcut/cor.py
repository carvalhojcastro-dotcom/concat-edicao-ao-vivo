"""Correção de cor e filtro no vídeo inteiro de um corte (pedido de 2026-11-13, podcasts Dra Márcia e JFIT:
"Correção de cor com +15 nitidez e +2 exposição; Filtro 'crepusculo dos sonhos' em 20%; Sem filtros de correção de
rosto ou maquiagens").
- Camada de ajuste (trilha "adjust") no molde da do projeto "Bastio": só nitidez e exposição (valor = número da tela/100;
  todos os parâmetros do ajuste usam o mesmo pacote de efeito do CapCut, muda só o "type").
- Filtro (trilha "filter") no molde do "Crepúsculo dos sonhos" que o usuário pôs no "EP01C11 - Câncer não é sentença de
  morte", com a intensidade pedida.
As duas ficam logo acima das trilhas de vídeo (embaixo da headline e das legendas), do começo ao fim.
Rodar de novo troca as duas (nomes "Ajuste (Concat)" e "Filtro (Concat)"). CapCut FECHADO.
Uso: cor.py <pasta do projeto> [--nitidez 15] [--exposicao 2] [--filtro 20]"""
import copy, json, os, sys
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "..")))
import capcut_simples as C  # noqa: E402

RAIZ = os.path.expanduser("~/Movies/CapCut/User Data/Projects/com.lveditor.draft/")
MOLDE_AJUSTE = RAIZ + "Bastio/draft_info.json"
MOLDE_FILTRO = RAIZ + "EP01C11 - Câncer não é sentença de morte/draft_info.json"
args = sys.argv[1:]
pasta = args[0]
opc = lambda nome, padrao: float(args[args.index(nome) + 1]) if nome in args else padrao  # noqa: E731
nitidez, exposicao, filtro = opc("--nitidez", 15), opc("--exposicao", 2), opc("--filtro", 20)


def copia_seg(Mo, trilha, N, total, nome):
    s = copy.deepcopy(trilha["segments"][0])
    k, m = C.material_de(Mo, s["material_id"])
    m = dict(copy.deepcopy(m), id=C.novo_id())
    N["materials"].setdefault(k, []).append(m)
    s.update(id=C.novo_id(), material_id=m["id"], extra_material_refs=[],
             target_timerange={"start": 0, "duration": total})
    t = dict(copy.deepcopy({kk: v for kk, v in trilha.items() if kk != "segments"}), id=C.novo_id(), name=nome,
             is_default_name=False, segments=[s])
    return t, s, m


C.backup(pasta, "antes da cor")
N = json.load(open(C.alvos(pasta)[0], encoding="utf-8"))
C.tirar_trilhas(N, ["Ajuste (Concat)", "Filtro (Concat)"])
total = N["duration"]

# ajuste: nitidez + exposição
Ma = json.load(open(MOLDE_AJUSTE, encoding="utf-8"))
ta = next(t for t in Ma["tracks"] if t["type"] == "adjust")
trilha_aj, seg_aj, _ = copia_seg(Ma, ta, N, total, "Ajuste (Concat)")
base = next(m for r in ta["segments"][0]["extra_material_refs"] for k, m in [C.material_de(Ma, r)] if k == "effects" and m.get("type") == "brightness")
for tipo, valor in (("sharpen", nitidez / 100), ("exposure", exposicao / 100)):
    m = dict(copy.deepcopy(base), id=C.novo_id(), type=tipo, value=valor)
    N["materials"].setdefault("effects", []).append(m)
    seg_aj["extra_material_refs"].append(m["id"])

# filtro
Mf = json.load(open(MOLDE_FILTRO, encoding="utf-8"))
tf = next(t for t in Mf["tracks"] if t["type"] == "filter")
trilha_fi, seg_fi, mat_fi = copia_seg(Mf, tf, N, total, "Filtro (Concat)")
mat_fi["value"] = filtro / 100

# logo acima da última trilha de vídeo
ult = max(i for i, t in enumerate(N["tracks"]) if t["type"] == "video")
N["tracks"][ult + 1:ult + 1] = [trilha_aj, trilha_fi]
C.reindexar(N)
C.gravar(pasta, N)
print(os.path.basename(pasta), f"| ajuste: nitidez +{nitidez:g}, exposição +{exposicao:g} | filtro {mat_fi['name']} {filtro:g}%")
