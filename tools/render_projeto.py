"""Renderizar quadros de um projeto sem bagunçar a lista de projetos do Concat.

O Concat não renderiza (preview.frame) um projeto aberto na janela. Nesse caso usamos uma cópia
temporária - e, ao terminar, a cópia é fechada, apagada e tirada da lista "Projects" (recents.json),
porque todo projeto aberto pela API entra nela e o usuário via cards repetidos.

    with projeto_para_render(path, tirar_textos=False) as (api, alvo):
        api.call("preview.frame", path=alvo, time=1.0, output=..., width=540, height=960)
"""
import contextlib
import json
import os
import shutil

from concat_api import Concat
import plataforma

RECENTES = plataforma.recentes()
TEMP = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "dist", "verificacao", "_temp_render")


def tirar_dos_recentes(caminho):
    try:
        d = json.load(open(RECENTES))
    except (OSError, ValueError):
        return
    fica = [x for x in d if os.path.realpath(x.get("path", "")) != os.path.realpath(caminho)]
    if len(fica) != len(d):
        json.dump(fica, open(RECENTES, "w"), ensure_ascii=False, indent=2)


@contextlib.contextmanager
def projeto_para_render(path, tirar_textos=False, transformar=None):
    """transformar(doc): muda o concat.json da cópia (ex.: tirar efeitos de imagem para medir)."""
    path = os.path.abspath(path)
    try:  # a lista "Projects" como estava: volta igualzinha no fim (a cópia empurraria o 12º para fora)
        antes = open(RECENTES, encoding="utf-8").read()
    except OSError:
        antes = None
    api = Concat(path); api.sock.settimeout(600)
    teste = os.path.join(os.path.dirname(TEMP), "_teste_render.png")
    os.makedirs(os.path.dirname(TEMP), exist_ok=True)
    try:
        api.call("project.get", path=path); aberto = True
    except RuntimeError:
        api.call("project.open", path=path); aberto = False
    na_janela = False
    if aberto:
        try:
            api.call("preview.frame", path=path, time=0.0, output=teste, width=64, height=114)
        except RuntimeError as e:
            na_janela = "open in the window" in str(e)
    if not na_janela and not tirar_textos and transformar is None:
        try:
            yield api, path
        finally:
            if not aberto:
                api.call("project.close", path=path, save=False)
        return
    # cópia temporária (projeto na janela, ou sem legendas para medir)
    shutil.rmtree(TEMP, ignore_errors=True); os.makedirs(TEMP)
    d = json.load(open(os.path.join(path, "concat.json")))
    if tirar_textos:
        for t in d.get("timelines", []):
            t["clips"] = [c for c in t["clips"] if c["kind"] != "text"]
    if transformar:
        transformar(d)
    json.dump(d, open(os.path.join(TEMP, "concat.json"), "w"))
    if not aberto and not na_janela:
        api.call("project.close", path=path, save=False)
    api.call("project.open", path=TEMP)
    try:
        yield api, TEMP
    finally:
        try:
            api.call("project.close", path=TEMP, save=False)
        except RuntimeError:
            pass
        shutil.rmtree(TEMP, ignore_errors=True)
        if antes is not None:
            open(RECENTES, "w", encoding="utf-8").write(antes)
        else:
            tirar_dos_recentes(TEMP)
