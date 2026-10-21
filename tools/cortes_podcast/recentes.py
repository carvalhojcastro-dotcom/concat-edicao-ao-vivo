"""Limpa a lista de projetos do Concat: tira os temporários de _cortes e devolve os do backup que foram empurrados."""
import json, os, sys
REC = os.path.expanduser("~/Library/Application Support/app.concat.editor/recents.json")
BK = os.path.join(os.environ.get("TRABALHO", os.path.dirname(os.path.abspath(__file__))), "recents_backup.json")
cur = json.load(open(REC)); bk = json.load(open(BK)) if os.path.exists(BK) else []
fica = [x for x in cur if "/dist/verificacao/_cortes/" not in x.get("path", "")]
caminhos = {x.get("path") for x in fica}
fica += [x for x in bk if x.get("path") not in caminhos]
if fica != cur:
    json.dump(fica, open(REC, "w"), ensure_ascii=False, indent=2)
