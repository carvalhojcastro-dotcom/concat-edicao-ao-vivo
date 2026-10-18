"""Encurta 1 quadro do fim do clipe de vídeo que termina em `fim` (s) e puxa tudo o que vem depois."""
import sys
sys.path.insert(0, __import__("os").path.dirname(__file__))
from concat_api import Concat, timeline


def fix(api, end_at, frame=1 / 30):
    tl = timeline(api.view())
    clip = next(c for c in tl["clips"] if c["kind"] == "video" and abs(c["start"] + c["duration"] - end_at) < 1e-3)
    cut = clip["start"] + clip["duration"]
    later = [c for c in tl["clips"] if c["kind"] in ("text",) and c["start"] >= cut - 1e-6]
    spans = [c for c in tl["clips"] if c["kind"] in ("layer", "audio")]
    cmds = [{"op": "trimClip", "clipId": clip["id"], "edge": "end", "delta": -frame, "ripple": True}]
    if later:
        cmds.append({"op": "moveClips", "moves": [
            {"clipId": c["id"], "start": c["start"] - frame, "trackId": c["trackId"]}
            for c in sorted(later, key=lambda c: c["start"])]})
    for c in spans:
        cmds.append({"op": "trimClip", "clipId": c["id"], "edge": "end", "delta": -frame, "ripple": False})
    return timeline(api.batch(cmds)), clip["id"], len(later)


if __name__ == "__main__":
    api = Concat(sys.argv[1])
    api.call("project.open", path=api.path)
    tl, cid, n = fix(api, float(sys.argv[2]))
    print(f"clipe {cid} encurtado 1 quadro; {n} legendas puxadas")
