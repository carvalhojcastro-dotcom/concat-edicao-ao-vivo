#!/usr/bin/env python3
"""Confere se a instalação está pronta para editar (Mac ou Windows). Rode com o Python do venv:
  tools/.venv/bin/python tools/testar_instalacao.py          (Mac)
  tools\\.venv\\Scripts\\python.exe tools\\testar_instalacao.py   (Windows)
  ... --quadro <saida.png>   também guarda o quadro de teste renderizado pelo Concat

Confere: ffmpeg; bibliotecas do venv (transcrição, imagem, rosto); fontes em fonts/; token da API;
e, com o Concat aberto, cria um projeto temporário, põe uma legenda dinâmica em cada fonte, renderiza um
quadro e apaga o projeto (tirando-o da lista de recentes). Sai com 0 se tudo passou.
"""
import importlib
import os
import shutil
import sys
import tempfile
import time

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import plataforma  # noqa: E402

ok = True


def item(nome, passou, detalhe=""):
    global ok
    ok = ok and passou
    print(f"  [{'ok' if passou else 'FALHOU'}] {nome}{(' - ' + detalhe) if detalhe else ''}", flush=True)


def main():
    print(f"Sistema: {'Mac' if plataforma.MAC else 'Windows' if plataforma.WINDOWS else sys.platform}")
    item("ffmpeg e ffprobe no PATH", plataforma.ffmpeg_ok())
    libs = ["PIL", "fontTools", "numpy", "cv2", "mediapipe", "dotenv", "higgsfield_client", "df"]
    libs.append("mlx_whisper" if plataforma.MAC else "faster_whisper")
    for lib in libs:
        try:
            importlib.import_module(lib)
            item(f"python: {lib}", True)
        except Exception as e:  # noqa: BLE001
            item(f"python: {lib}", False, str(e)[:120])

    falso = tempfile.mkdtemp()  # legendas_dinamicas lê o fps do projeto em argv[1]: um projeto de mentira a 30 fps
    with open(os.path.join(falso, "concat.json"), "w") as f:
        f.write('{"timelines": [{"video": {"rateNum": 30, "rateDen": 1}}]}')
    sys.argv = [sys.argv[0], falso] + sys.argv[1:]
    try:
        import legendas_dinamicas as ld
    except Exception as e:  # noqa: BLE001
        item("legendas_dinamicas importa", False, str(e)[:160])
        return 1
    faltam = sorted({os.path.basename(v[3]) for v in ld.FACES.values() if not os.path.exists(v[3])})
    item("fontes das legendas em fonts/", not faltam, ", ".join(faltam))
    item(".concat-token", os.path.exists(os.path.join(plataforma.RAIZ, ".concat-token")))

    from concat_api import Concat, timeline
    from render_projeto import tirar_dos_recentes
    # o Concat só grava dentro da pasta do usuário: o projeto de teste vai para lá (o repositório pode estar fora)
    base = os.path.join(os.path.expanduser("~"), ".concat-teste-instalacao")
    os.makedirs(base, exist_ok=True)
    nome = "_teste_instalacao"
    proj = os.path.join(base, nome)
    shutil.rmtree(proj, ignore_errors=True)
    api = None
    for _ in range(30):  # o Concat pode estar abrindo
        try:
            api = Concat(proj)
            break
        except OSError:
            time.sleep(2)
    if api is None:
        item("API do Concat na porta 7420", False, "abra o Concat (com a API ligada pelo setup) e rode de novo")
        return 1
    item("API do Concat na porta 7420", True)
    api.sock.settimeout(300)
    try:
        api.call("project.create", location=base, name=nome,
                 video={"width": 1080, "height": 1920, "rateNum": 30, "rateDen": 1})
        api.call("project.open", path=proj)
        for familia, arquivo in ld.REGISTRAR:
            if os.path.exists(os.path.join(ld.FONTES, arquivo)):
                api.edit({"op": "addFont", "family": familia, "path": os.path.abspath(os.path.join(ld.FONTES, arquivo))})
        ld.FONTE_CHAVE = "serifa"
        palavras = ld.montar("serifa", [[0, 1], [2, 3, 4], [5], [6]], {5},
                             ["e", "começar", "a", "usar", "essas", "legendas", "aqui"])
        cmds = [{"op": "addTextClip", "above": True, "start": 0.0, "duration": 2.0, "offsetY": 0.0, "style": p["style"]}
                for p in palavras]
        tl = timeline(api.batch(cmds))
        novos = sorted([c for c in tl["clips"] if c["kind"] == "text"], key=lambda c: int("".join(ch for ch in c["id"] if ch.isdigit()) or 0))  # c10 depois de c9
        api.batch([{"op": "setClipTransform", "clipId": c["id"], "offsetX": p["ox"], "offsetY": p["oy"]}
                   for c, p in zip(novos, palavras)])
        saida = sys.argv[sys.argv.index("--quadro") + 1] if "--quadro" in sys.argv else os.path.join(base, "teste_instalacao.png")
        quadro = os.path.join(base, "quadro.png")
        api.call("preview.frame", path=proj, time=1.0, output=quadro, width=540, height=960)
        if os.path.exists(quadro):
            shutil.move(quadro, saida)
        item("Concat renderiza a legenda dinâmica", os.path.exists(saida) and os.path.getsize(saida) > 1000, saida)
    except Exception as e:  # noqa: BLE001
        item("Concat renderiza a legenda dinâmica", False, str(e)[:200])
    finally:
        try:
            api.call("project.close", path=proj, save=False)
        except Exception:  # noqa: BLE001
            pass
        tirar_dos_recentes(proj)
        shutil.rmtree(proj, ignore_errors=True)
    if not os.path.exists(os.path.join(plataforma.RAIZ, ".env.local")):
        print("  [aviso] sem .env.local: rode tools/configurar_chave_higgsfield (.ps1/.sh) para o B-roll")
    print("TUDO PRONTO" if ok else "HÁ ITENS COM FALHA")
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main())
