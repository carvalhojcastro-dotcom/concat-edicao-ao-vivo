"""Monta um corte a partir de trechos [in, out] da fonte.

Uso: montar_corte.py <nomeado.json> <audio16k.wav> <src.mp4> <saida_dir> "in-out,in-out" [--pausa 0.6]
Gera em saida_dir:
  corte.json  {"src", "segmentos", "falas"}  (tempos da fonte, bordas no quadro)
  words.json  palavras no tempo do corte (para legendas_estilos.py)
  texto.txt   texto corrido com índice de cada palavra
Bordas: 1ª/última batida de voz acima de -30 dB perto da 1ª/última palavra; pausas internas
maiores que --pausa viram 0,25 s (0,12 s de cada lado).
"""
import json, os, sys, wave
import numpy as np

FPS = 30
JAN = 0.025


def rms_db(wav):
    w = wave.open(wav); sr = w.getframerate()
    x = np.frombuffer(w.readframes(w.getnframes()), dtype=np.int16).astype(np.float32) / 32768
    h = int(sr * JAN); n = len(x) // h
    return 20 * np.log10(np.sqrt((x[:n * h].reshape(n, h) ** 2).mean(1)) + 1e-9)


def q(t):
    return round(t * FPS) / FPS


def main():
    nomeado, wav, src, out, trechos = sys.argv[1:6]
    pausa = float(sys.argv[sys.argv.index("--pausa") + 1]) if "--pausa" in sys.argv else 0.6
    os.makedirs(out, exist_ok=True)
    d = json.load(open(nomeado))
    words = []
    for s in d["segments"]:
        for w in s.get("words", []):
            words.append({"word": w["word"], "start": w["start"], "end": w["end"], "speaker": s["speaker"]})
    words.sort(key=lambda w: w["start"])
    db = rms_db(wav)
    voz = lambda t: db[min(int(t / JAN), len(db) - 1)] > -30

    segs, falas, wout = [], [], []
    for tr in trechos.split(","):
        a, b = map(float, tr.split("-"))
        ws = [w for w in words if w["start"] >= a - 0.05 and w["end"] <= b + 0.05]
        if not ws:
            continue
        # agrupa por pausas
        grupos = [[ws[0]]]
        for w in ws[1:]:
            if w["start"] - grupos[-1][-1]["end"] > pausa:
                grupos.append([w])
            else:
                grupos[-1].append(w)
        for g in grupos:
            i0 = words.index(g[0]); i1 = words.index(g[-1])
            ant_fim = words[i0 - 1]["end"] if i0 > 0 else 0
            prox_ini = words[i1 + 1]["start"] if i1 + 1 < len(words) else g[-1]["end"] + 1
            # bordas por folga nas palavras do Whisper (o áudio de podcast é baixo: limiar de energia comia palavras)
            ini = min(max(g[0]["start"] - 0.15, ant_fim + 0.05), g[0]["start"])
            fim = min(g[-1]["end"] + 0.35, prox_ini - 0.05)
            fim = max(fim, g[-1]["end"])
            segs.append([q(ini), q(fim)])
    # encaixa cada borda na pausa real da voz (o Whisper às vezes desloca as palavras e o corte caía no meio da fala)
    PAUSA, FRACO = -34, -30
    def e(t):
        return db[max(0, min(int(t / JAN), len(db) - 1))]
    def grade(a, b):
        return [a + k * JAN for k in range(int((b - a) / JAN) + 1)]
    def fim_pausa(b, depois):
        for t in grade(b - 0.1, b + depois):
            if e(t) < PAUSA:
                return t
        for t in reversed(grade(b - 0.4, b - 0.1)):
            if e(t) < PAUSA:
                return t
        t = min(grade(b - 0.1, b + depois), key=e)
        return t if e(t) < FRACO else b
    def ini_pausa(a):
        for t in reversed(grade(a - 0.6, a + 0.1)):
            if e(t) < PAUSA:
                return t
        t = min(grade(a - 0.6, a + 0.1), key=e)
        return t if e(t) < FRACO else a
    for i in range(len(segs)):
        a, b = segs[i]
        na = ini_pausa(a)
        nb = fim_pausa(b, 0.25 if i == len(segs) - 1 else 0.6)
        if i and na < segs[i - 1][1]:
            na = segs[i - 1][1]
        segs[i] = [q(na), q(max(nb, na + 0.1))]
    # junta segmentos encostados
    jn = []
    for s in segs:
        if jn and s[0] <= jn[-1][1] + 1e-6:
            jn[-1][1] = max(jn[-1][1], s[1])
        else:
            jn.append(s)
    segs = jn
    fx = os.path.join(out, "fixos.json")   # bordas conferidas à mão: substituem as calculadas
    if os.path.exists(fx):
        segs = [[q(a), q(b)] for a, b in json.load(open(fx))]
    fj = os.path.join(out, "fim.json")   # final forçado (fala que emenda na do outro)
    if os.path.exists(fj):
        segs[-1][1] = q(json.load(open(fj))["fim"])
    # palavras e falas no tempo do corte
    off = 0.0
    for a, b in segs:
        for w in words:
            if w["start"] >= a - 0.12 and w["start"] < b - 0.03 and w["end"] <= b + 0.3:
                wout.append({"word": w["word"].strip(), "start": round(max(0, w["start"] - a) + off, 3),
                             "end": round(min(w["end"], b) - a + off, 3), "speaker": w["speaker"], "src": w["start"]})
        off += b - a
    for s in d["segments"]:
        for a, b in segs:
            t0, t1 = max(s["start"], a), min(s["end"], b)
            if t1 - t0 > 0.2:
                v = "F" if s["speaker"] in ("IVE", "ISABELA_CONVIDADA") or s["speaker"].endswith("_F") else "M"
                falas.append({"t0": t0, "t1": t1, "voz": v, "quem": s["speaker"]})
    json.dump({"src": src, "segmentos": segs, "falas": falas}, open(os.path.join(out, "corte.json"), "w"), ensure_ascii=False, indent=1)
    json.dump(wout, open(os.path.join(out, "words.json"), "w"), ensure_ascii=False, indent=1)
    with open(os.path.join(out, "texto.txt"), "w") as f:
        quem = None
        for i, w in enumerate(wout):
            if w["speaker"] != quem:
                quem = w["speaker"]; f.write(f"\n[{quem}] ")
            f.write(f"{i}:{w['word']} ")
    dur = sum(b - a for a, b in segs)
    print(f"{len(segs)} segmentos, {dur:.1f}s, {len(wout)} palavras")


if __name__ == "__main__":
    main()
