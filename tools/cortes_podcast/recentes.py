"""Limpa a lista de projetos do Concat: tira os temporários de _cortes e devolve os do backup que foram empurrados."""
import json, os, sys
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), ".."))
import plataforma  # noqa: E402
REC = plataforma.recentes()
BK = os.path.join(os.environ.get("TRABALHO", os.path.dirname(os.path.abspath(__file__))), "recents_backup.json")
cur = json.load(open(REC)); bk = json.load(open(BK)) if os.path.exists(BK) else []
fica = [x for x in cur if "_cortes" not in x.get("path", "").replace("\\", "/").split("/")]
caminhos = {x.get("path") for x in fica}
fica += [x for x in bk if x.get("path") not in caminhos]
if fica != cur:
    json.dump(fica, open(REC, "w"), ensure_ascii=False, indent=2)
