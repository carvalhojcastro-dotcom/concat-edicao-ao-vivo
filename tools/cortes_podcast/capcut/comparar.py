"""Onde o turbo e o medium discordam num corte (palavra errada, ou trecho que um deles pulou em fala sobreposta).
Uso: comparar.py <W> <id>"""
import difflib, json, os, re, sys
W, cid = sys.argv[1], sys.argv[2]
d = os.path.join(W, f"c{cid}")
a = json.load(open(os.path.join(d, "words_tl.json")))
b = json.load(open(os.path.join(d, "words_med.json")))
n = lambda w: re.sub(r"[^\wà-úç]", "", w.lower())  # noqa: E731
A, B = [n(w["word"]) for w in a], [n(w["word"]) for w in b]
for op, i1, i2, j1, j2 in difflib.SequenceMatcher(a=A, b=B, autojunk=False).get_opcodes():
    if op == "equal":
        continue
    ctx = " ".join(w["word"] for w in a[max(0, i1 - 3):i1])
    t = a[i1]["start"] if i1 < len(a) else a[-1]["end"]
    print(f"[{i1}-{i2 - 1}] {t:.1f}s …{ctx} | turbo: {' '.join(w['word'] for w in a[i1:i2])!r}  medium: {' '.join(w['word'] for w in b[j1:j2])!r}")
