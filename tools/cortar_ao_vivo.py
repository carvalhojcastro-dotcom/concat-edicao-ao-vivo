#!/usr/bin/env python3
"""Corta trechos de um clipe no projeto aberto na janela do Concat, ao vivo.

Fala com a API JSON-RPC do Concat (Settings > API). Os trechos são dados em
segundos do arquivo de origem; cada um vira dois splits + um ripple delete,
do último para o primeiro, com uma pausa entre eles para dar para ver.

Uso:
  CONCAT_TOKEN=... cortar_ao_vivo.py <pasta do projeto> <cortes.json> [--porta 7420] [--pausa 0.6]

cortes.json: [[inicio, fim], ...] em segundos da mídia de origem.
"""
import argparse
import json
import os
import socket
import sys
import time

EPS = 1e-3


class Concat:
    def __init__(self, host, port, token):
        self.sock = socket.create_connection((host, port), timeout=30)
        self.file = self.sock.makefile("rw", encoding="utf-8", newline="\n")
        self.next_id = 0
        self.call("auth", token=token)

    def call(self, method, **params):
        self.next_id += 1
        line = json.dumps({"jsonrpc": "2.0", "id": self.next_id, "method": method, "params": params})
        self.file.write(line + "\n")
        self.file.flush()
        while True:
            reply = json.loads(self.file.readline())
            if reply.get("id") == self.next_id:
                break  # eventos (sem id) ficam de fora
        if "error" in reply:
            raise RuntimeError(f"{method}: {reply['error']['message']}")
        return reply["result"]


def clips_of(view):
    project = view["project"]
    timeline = next(t for t in project["timelines"] if t["id"] == project["activeTimelineId"])
    return timeline["clips"]


def source_end(clip):
    return clip["sourceStart"] + clip["duration"] * clip.get("speed", 1.0)


def at_source(clips, media_id, src):
    """O clipe que mostra o instante `src` da mídia, e esse instante na timeline."""
    for clip in clips:
        if clip.get("mediaId") == media_id and clip["sourceStart"] - EPS <= src <= source_end(clip) + EPS:
            return clip, clip["start"] + (src - clip["sourceStart"]) / clip.get("speed", 1.0)
    return None, None


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("projeto")
    ap.add_argument("cortes")
    ap.add_argument("--host", default="127.0.0.1")
    ap.add_argument("--porta", type=int, default=7420)
    ap.add_argument("--pausa", type=float, default=0.6)
    ap.add_argument("--fechar-inicio", action="store_true",
                    help="encosta o primeiro clipe no zero da timeline no fim")
    args = ap.parse_args()
    token = os.environ.get("CONCAT_TOKEN") or sys.exit("defina CONCAT_TOKEN")
    cuts = sorted(json.load(open(args.cortes)), reverse=True)

    api = Concat(args.host, args.porta, token)
    path = args.projeto
    view = api.call("project.open", path=path)
    clips = clips_of(view)
    media_ids = {c.get("mediaId") for c in clips if c.get("mediaId")}
    if len(media_ids) != 1:
        sys.exit(f"esperava clipes de uma única mídia, achei {media_ids}")
    media_id = media_ids.pop()

    def edit(command):
        return clips_of(api.call("edit.apply", path=path, command=command))

    for n, (a, b) in enumerate(cuts, 1):
        clip, tb = at_source(clips, media_id, b)
        if clip and source_end(clip) - b > EPS:
            clips = edit({"op": "splitClips", "clipIds": [clip["id"]], "time": tb})
        clip, ta = at_source(clips, media_id, a)
        if clip is None:
            print(f"[{n}/{len(cuts)}] {a:.2f}-{b:.2f}s: fora do clipe, pulei")
            continue
        if a - clip["sourceStart"] > EPS:
            clips = edit({"op": "splitClips", "clipIds": [clip["id"]], "time": ta})
        piece = next(c for c in clips if c.get("mediaId") == media_id and abs(c["sourceStart"] - a) < 0.02)
        clips = edit({"op": "removeClips", "clipIds": [piece["id"]], "ripple": True})
        print(f"[{n}/{len(cuts)}] cortado {a:.2f}-{b:.2f}s da origem", flush=True)
        time.sleep(args.pausa)

    if args.fechar_inicio and clips:
        first = min(c["start"] for c in clips)
        if first > EPS:
            clips = edit({"op": "moveClips", "moves": [
                {"clipId": c["id"], "start": c["start"] - first, "trackId": c["trackId"]} for c in clips
            ]})
            print(f"timeline encostada no zero (andou {first:.2f}s)")

    api.call("project.save", path=path)
    total = max(c["start"] + c["duration"] for c in clips)
    print(f"pronto: {len(clips)} clipes, {total:.2f}s; projeto salvo")


if __name__ == "__main__":
    main()
