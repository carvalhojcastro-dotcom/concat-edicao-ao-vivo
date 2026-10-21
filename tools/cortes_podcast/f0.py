"""F0 mediano por trecho (autocorrelação), para rotular voz M/F."""
import numpy as np, wave
def carregar(wav):
    w = wave.open(wav); sr = w.getframerate()
    x = np.frombuffer(w.readframes(w.getnframes()), dtype=np.int16).astype(np.float32) / 32768
    return x, sr
def f0_trecho(x, sr, t0, t1, fmin=70, fmax=330):
    a, b = int(t0 * sr), int(t1 * sr)
    seg = x[a:b]
    win, hop = int(0.04 * sr), int(0.02 * sr)
    lmin, lmax = int(sr / fmax), int(sr / fmin)
    vals = []
    for i in range(0, len(seg) - win, hop):
        fr = seg[i:i + win]
        if np.sqrt((fr ** 2).mean()) < 0.01:
            continue
        fr = fr - fr.mean()
        ac = np.correlate(fr, fr, 'full')[win - 1:]
        if ac[0] <= 0: continue
        ac = ac / ac[0]
        k = lmin + np.argmax(ac[lmin:lmax])
        if ac[k] > 0.5:
            vals.append(sr / k)
    return (float(np.median(vals)), len(vals)) if vals else (None, 0)
