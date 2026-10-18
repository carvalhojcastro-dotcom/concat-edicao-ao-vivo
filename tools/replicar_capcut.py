"""Recria no projeto aberto do Concat a edição de um draft do CapCut.

Uso: replicar_capcut.py <pasta do projeto Concat> <draft_info.json do CapCut> <dados.json>

dados.json traz o que não sai do draft: caminhos de mídia preparados (cartão com
máscara), calibração de texto e o LUT importado. O draft é lido como dado.
"""
import json
import sys
import time

sys.path.insert(0, __import__("os").path.dirname(__file__))
from concat_api import Concat, timeline

FPS = 30
US = 1e6


def snap(t):
    return round(t * FPS) / FPS


def log(msg):
    print(msg, flush=True)


def main():
    path, draft_path, extra_path = sys.argv[1:4]
    draft = json.load(open(draft_path))
    extra = json.load(open(extra_path))
    mats = {}
    for kind, items in draft["materials"].items():
        if isinstance(items, list):
            for it in items:
                if isinstance(it, dict) and "id" in it:
                    mats[it["id"]] = (kind, it)
    api = Concat(path)
    view = api.call("project.open", path=path)

    # ── 0. limpa a timeline (uma edição só) ──
    tl = timeline(view)
    cmds = []
    if tl["clips"]:
        cmds.append({"op": "removeClips", "clipIds": [c["id"] for c in tl["clips"]], "ripple": False})
    base = [t["id"] for t in tl["tracks"]][:4]
    cmds += [{"op": "removeTrack", "trackId": t["id"]} for t in tl["tracks"][4:]]
    if cmds:
        tl = timeline(api.batch(cmds))
    log(f"timeline limpa; faixas {[t['id'] for t in tl['tracks']]}")
    T_MAIN, T_BROLL, T_CUT, T_ADJ1 = base

    def new_track(bottom=False):
        before = {t["id"] for t in timeline(api.view())["tracks"]}
        after = timeline(api.edit({"op": "addTrack", "bottom": bottom}))["tracks"]
        return next(t["id"] for t in after if t["id"] not in before)

    T_ADJ2 = new_track()
    T_TEXT = new_track()
    T_SFX = new_track(bottom=True)
    T_MUSIC = new_track(bottom=True)

    # ── mídia ──
    media_ids = {}

    def media(file):
        if file not in media_ids:
            v = api.call("media.import", path=path, file=file)
            media_ids[file] = next(m["id"] for m in v["project"]["media"] if m["path"] == file)
        return media_ids[file]

    parking = [300.0]

    def place(file, track, t0, src, dur, speed=1.0, still=False):
        """Coloca um trecho [src, src+dur*speed) do arquivo em t0 (timeline) na faixa."""
        mid = media(file)
        park = parking[0]
        parking[0] += 120.0
        cid = api.edit({"op": "addClip", "mediaId": mid, "trackId": track, "start": park, "ripple": False})["createdId"]
        c = next(c for c in timeline(api.view())["clips"] if c["id"] == cid)
        seq = []
        if abs(speed - 1.0) > 1e-9:
            seq.append({"op": "setClipSpeed", "clipId": cid, "speed": speed})
        cur = c["duration"] * c.get("speed", 1.0) / speed  # duração depois da velocidade
        if src > 1e-9 and not still:
            seq.append({"op": "trimClip", "clipId": cid, "edge": "start", "delta": src / speed, "ripple": False})
            cur -= src / speed
        seq.append({"op": "trimClip", "clipId": cid, "edge": "end", "delta": dur - cur, "ripple": False})
        seq.append({"op": "moveClips", "moves": [{"clipId": cid, "start": t0, "trackId": track}]})
        tl = timeline(api.batch(seq))
        c = next(c for c in tl["clips"] if c["id"] == cid)
        err = max(abs(c["start"] - t0), abs(c["duration"] - dur), 0 if still else abs(c.get("sourceStart", 0) - src))
        if err > 2e-3:
            raise RuntimeError(f"{file} em {t0}: ficou start {c['start']:.4f} dur {c['duration']:.4f} src {c.get('sourceStart')}")
        return cid

    def segs(track_index, d=draft):
        return d["tracks"][track_index]["segments"]

    def tr(s):
        a = s["target_timerange"]
        return snap(a["start"] / US), snap((a["start"] + a["duration"]) / US)

    def capcut_transform(s):
        clip = s.get("clip") or {}
        sc = clip.get("scale", {}).get("x", 1.0)
        tf = clip.get("transform", {})
        return sc, tf.get("x", 0.0) / 2, -tf.get("y", 0.0) / 2

    SRC = extra["source_video"]
    sub = extra["compound"]  # sequência de cortes dos clipes compostos
    cut_end = extra["compound_end"]

    # ── 1. doutora em tela cheia: 0–17,6 vem do composto, depois a faixa principal ──
    main = []
    comp_sc, comp_ox, comp_oy = capcut_transform(segs(0)[0])
    for s in sub:
        t0, t1 = s["t0"], s["t1"]
        if t0 >= cut_end - 1e-6:
            break
        cid = place(SRC, T_MAIN, t0, s["src"], min(t1, cut_end) - t0, speed=s["speed"])
        main.append((cid, comp_sc, comp_ox, comp_oy, None, None))
    for s in segs(0)[1:]:
        t0, t1 = tr(s)
        src = s["source_timerange"]["start"] / US
        cid = place(SRC, T_MAIN, t0, src, t1 - t0, speed=s.get("speed", 1.0))
        sc, ox, oy = capcut_transform(s)
        main.append((cid, sc, ox, oy, s, src))
    log(f"{len(main)} trechos da doutora na faixa principal")
    cmds = []
    for cid, sc, ox, oy, s, src in main:
        cmds.append({"op": "setClipTransform", "clipId": cid, "scale": sc, "offsetX": ox, "offsetY": oy})
    api.batch(cmds)

    # keyframes e transição da faixa principal
    tl = timeline(api.view())
    for cid, sc, ox, oy, s, src in main:
        if not s:
            continue
        c = next(c for c in tl["clips"] if c["id"] == cid)
        span = c["duration"] * c["speed"]
        for kf in s.get("common_keyframes", []):
            prop = {"KFTypeScaleX": ("scale", 1.0), "KFTypePositionX": ("offsetX", 0.5), "KFTypePositionY": ("offsetY", -0.5)}.get(kf["property_type"])
            if not prop:
                continue
            key, factor = prop
            seq = []
            for p in kf["keyframe_list"]:
                at = min(1.0, max(0.0, (p["time_offset"] / US - src) / span))
                seq.append({"op": "setClipKey", "clipId": cid, "property": key, "at": round(at, 4), "value": p["values"][0] * factor})
            api.batch(seq)
            log(f"keyframes {key} em {cid}: {[(x['at'], round(x['value'], 3)) for x in seq]}")
        for r in s.get("extra_material_refs", []):
            kind, it = mats.get(r, ("", {}))
            if kind == "transitions":
                # No CapCut a transição fica no clipe que sai; no Concat, no que entra.
                nxt = next(x for x in sorted(tl["clips"], key=lambda x: x["start"]) if x["trackId"] == T_MAIN and abs(x["start"] - (c["start"] + c["duration"])) < 1e-3)
                api.edit({"op": "updateClip", "clipId": nxt["id"], "patch": {"transitionIn": {"id": extra["transition"], "duration": round(it["duration"] / US, 4)}}})
                log(f"transição {it['name']} -> {extra['transition']} na entrada de {nxt['id']} ({nxt['start']:.3f}s)")

    # ── 2. B-roll e cartão ──
    for s in segs(1):
        t0, t1 = tr(s)
        kind, mat = mats[s["material_id"]]
        file = extra["media_map"].get(mat["path"], mat["path"])
        still = mat.get("type") == "photo"
        src = (s.get("source_timerange") or {}).get("start", 0) / US
        cid = place(file, T_BROLL, t0, src, t1 - t0, still=still)
        sc, ox, oy = capcut_transform(s)
        cmds = [{"op": "setClipTransform", "clipId": cid, "scale": sc, "offsetX": ox, "offsetY": oy}]
        if still:
            # Mini zoom de entrada (0,5 s) e fade-out de 0,5 s, como no CapCut.
            dur = t1 - t0
            cmds += [{"op": "setClipKey", "clipId": cid, "property": "scale", "at": 0.0, "value": sc * 0.92},
                     {"op": "setClipKey", "clipId": cid, "property": "scale", "at": round(0.5 / dur, 4), "value": sc, "ease": [0.0, 0.0, 0.58, 1.0]},
                     {"op": "updateClip", "clipId": cid, "patch": {"fadeOut": 0.5}}]
        else:
            cmds.append({"op": "updateClip", "clipId": cid, "patch": {"muted": True, "volume": 0.0}})
        api.batch(cmds)
        log(f"faixa 2: {file.split('/')[-1]} {t0:.3f}-{t1:.3f}")

    # ── 3. doutora recortada, menor, sobre o B-roll ──
    sc, ox, oy = capcut_transform(segs(2)[0])
    cut_ids = []
    for s in sub:
        if s["t0"] >= cut_end - 1e-6:
            break
        cid = place(SRC, T_CUT, s["t0"], s["src"], min(s["t1"], cut_end) - s["t0"], speed=s["speed"])
        cut_ids.append(cid)
    cmds = []
    for cid in cut_ids:
        cmds += [{"op": "setClipTransform", "clipId": cid, "scale": sc, "offsetX": ox, "offsetY": oy},
                 {"op": "updateClip", "clipId": cid, "patch": {"muted": True, "volume": 0.0}},
                 {"op": "setClipCutout", "clipId": cid, "cutout": {"mode": "auto", "subject": "person", "feather": 0.0}}]
    api.batch(cmds)
    log(f"{len(cut_ids)} trechos recortados na faixa 3")

    # ── 4. camadas de ajuste ──
    for track, seg, chain in ((T_ADJ1, segs(3)[0], extra["adjust1"]), (T_ADJ2, segs(4)[0], extra["adjust2"])):
        t0, t1 = tr(seg)
        lid = api.edit({"op": "addLayerClip", "trackId": track, "start": t0, "duration": t1 - t0,
                        "effectId": chain[0]["id"], "name": seg.get("name") or "Ajuste"})["createdId"]
        api.edit({"op": "updateClip", "clipId": lid, "patch": {"videoEffects": [dict(e, enabled=True) for e in chain]}})
        log(f"camada de ajuste {lid} {t0:.3f}-{t1:.3f}: {chain}")

    # ── 5. legendas ──
    texts = segs(5)
    cal = extra["text"]
    cmds = []
    for s in texts:
        t0, t1 = tr(s)
        kind, mat = mats[s["material_id"]]
        content = json.loads(mat["content"])
        size = content["styles"][0]["size"]
        k = size / cal["capcut_size"]
        cmds.append({"op": "addTextClip", "trackId": T_TEXT, "start": t0, "duration": t1 - t0,
                     "offsetY": -s["clip"]["transform"]["y"] / 2,
                     "style": {"content": content["text"], "fontFamily": "Helvetica", "fontSize": cal["font_size"] * k,
                               "fontWeight": 400, "color": "#ffffff", "tracking": cal["tracking"] * k,
                               "strokeWidth": cal["stroke"], "strokeColor": "#000000", "shadow": True}})
    for i in range(0, len(cmds), 25):
        api.batch(cmds[i:i + 25])
    log(f"{len(cmds)} legendas")

    # ── 6. música e efeitos sonoros ──
    for track, idx in ((T_MUSIC, 6), (T_SFX, 7)):
        for s in segs(idx):
            t0, t1 = tr(s)
            kind, mat = mats[s["material_id"]]
            src = s["source_timerange"]["start"] / US
            cid = place(mat["path"], track, t0, src, t1 - t0)
            patch = {"volume": round(s.get("volume", 1.0), 4), "name": mat.get("name", "")}
            for r in s.get("extra_material_refs", []):
                fk, f = mats.get(r, ("", {}))
                if fk == "audio_fades":
                    patch["fadeIn"] = f["fade_in_duration"] / US
                    patch["fadeOut"] = f["fade_out_duration"] / US
            api.edit({"op": "updateClip", "clipId": cid, "patch": patch})
            log(f"áudio {mat.get('name', '')[:30]:30} {t0:.3f}-{t1:.3f} vol {patch['volume']}")

    api.call("project.save", path=path)
    tl = timeline(api.view())
    end = max(c["start"] + c["duration"] for c in tl["clips"])
    log(f"pronto: {len(tl['clips'])} clipes, fim {end:.3f}s; salvo")


if __name__ == "__main__":
    main()
