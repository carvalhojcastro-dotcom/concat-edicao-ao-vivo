#!/usr/bin/env python3
"""Liga a API do Concat (porta 7420) nas preferências e grava o mesmo token em .concat-token.

Uso: ligar_api.py            liga (rode com o Concat FECHADO: aberto, ele regrava as preferências ao sair)
     ligar_api.py --checar   só confere: sai com 0 se a API já está ligada e o .concat-token bate

Funciona no Mac e no Windows (as preferências ficam onde o Concat as procura: ver plataforma.py).
O token nunca é impresso.
"""
import json
import os
import secrets
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import plataforma  # noqa: E402

ARQ = os.path.join(plataforma.pasta_concat_app(), "settings.json")
TOKEN = os.path.join(plataforma.RAIZ, ".concat-token")


def ler():
    try:
        return json.load(open(ARQ, encoding="utf-8"))
    except (OSError, ValueError):
        return {}


def pronto():
    srv = ler().get("server") or {}
    try:
        gravado = open(TOKEN, encoding="utf-8").read().strip()
    except OSError:
        return False
    return bool(srv.get("enabled") and srv.get("token") and srv["token"] == gravado)


def main():
    if "--checar" in sys.argv:
        return 0 if pronto() else 1
    os.makedirs(os.path.dirname(ARQ), exist_ok=True)
    prefs = ler()
    srv = prefs.get("server") or {}
    if not srv.get("token"):
        srv["token"] = secrets.token_hex(24)
    srv["enabled"] = True
    srv.setdefault("listen", "127.0.0.1:7420")
    prefs["server"] = srv
    json.dump(prefs, open(ARQ, "w", encoding="utf-8"), indent=2)
    fd = os.open(TOKEN, os.O_WRONLY | os.O_CREAT | os.O_TRUNC, 0o600)
    os.write(fd, srv["token"].encode())
    os.close(fd)
    print("  API ligada; token em .concat-token (fora do Git)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
