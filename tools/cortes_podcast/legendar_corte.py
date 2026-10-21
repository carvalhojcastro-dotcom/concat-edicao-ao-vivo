"""Legendas dinâmicas do Concat num corte vertical, exporta 4K30 SDR e não deixa projeto para trás.

Uso: legendar_corte.py <vertical.mp4> <words.json> <plano.json> <saida.mp4> [--manter] [--quadros "t1 t2 ..." folha.jpg]
Projeto temporário em <repositório>/dist/verificacao/_cortes/<nome>: criado, legendado, exportado,
fechado, apagado e tirado do recents.json. --manter deixa o projeto (para depurar).
"""
import json, os, shutil, subprocess, sys, time

TOOLS = os.path.abspath(os.path.join(os.path.dirname(os.path.abspath(__file__)), ".."))
sys.path.insert(0, TOOLS)
from concat_api import Concat, timeline  # noqa: E402
from render_projeto import tirar_dos_recentes  # noqa: E402
import plataforma  # noqa: E402

PY = plataforma.python_venv()
BASE = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "..", "dist", "verificacao", "_cortes")


def main():
    vert, words, plano, saida = [os.path.abspath(a) for a in sys.argv[1:5]]
    nome = os.path.splitext(os.path.basename(saida))[0][:40].replace(" ", "_")
    proj = os.path.join(BASE, nome)
    if os.path.exists(proj):
        shutil.rmtree(proj)
    os.makedirs(BASE, exist_ok=True)
    rec = plataforma.recentes()
    rec_antes = open(rec).read() if os.path.exists(rec) else None
    api = Concat(proj); api.sock.settimeout(3600)
    try:
        api.call("project.create", location=BASE, name=nome,
                 video={"width": 1080, "height": 1920, "rateNum": 30, "rateDen": 1})
        api.call("project.open", path=proj)
        # cópia com nome único: o Concat reaproveita mídia em cache pelo caminho (export saía com o vídeo antigo)
        unico = os.path.join(proj, f"vertical_{int(time.time() * 1000)}.mp4")
        shutil.copyfile(vert, unico)
        api.call("media.import", path=proj, file=unico)
        v = api.view(); tl = timeline(v)
        api.edit({"op": "addClip", "mediaId": v["project"]["media"][0]["id"], "trackId": tl["tracks"][0]["id"], "start": 0.0})
        api.call("project.save", path=proj)
        api.call("project.close", path=proj)
        r = subprocess.run([PY, os.path.join(TOOLS, "legendas_estilos.py"), proj, words, plano], capture_output=True, text=True)
        print(r.stdout[-3000:], r.stderr[-3000:])
        if r.returncode:
            sys.exit("legendas_estilos falhou")
        if "--quadros" in sys.argv:
            i = sys.argv.index("--quadros")
            subprocess.run([PY, os.path.join(TOOLS, "quadros.py"), proj, sys.argv[i + 2], sys.argv[i + 1]], check=True)
        api = Concat(proj); api.sock.settimeout(3600)
        api.call("project.open", path=proj)
        job = api.call("export.run", path=proj, output=saida, width=1080, height=1920, crf=18, preset="medium", hdr=False)
        while True:
            ev = json.loads(api.file.readline())
            m, p = ev.get("method", ""), ev.get("params", {})
            if m == "export.done":
                break
            if m == "export.failed":
                sys.exit(f"export falhou: {p}")
        api.call("project.close", path=proj)
        print("exportado", saida)
    finally:
        if "--manter" not in sys.argv:
            try:
                Concat(proj).call("project.close", path=proj)
            except Exception:
                pass
            shutil.rmtree(proj, ignore_errors=True)
            subprocess.run([sys.executable, os.path.join(os.path.dirname(os.path.abspath(__file__)), "recentes.py")])


if __name__ == "__main__":
    main()
