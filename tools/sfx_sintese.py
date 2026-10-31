#!/usr/bin/env python3
"""Efeitos sonoros sintetizados para motion graphics: sutis, de interface, sem "boing", sem "plim" de desenho.

Pedido de 2026-10-30 (Sabrina, vídeo 24/11): "colocar alguns sound effects, mas de uma forma profissional, sem
esses efeitos clichês ... cada vez que entra uma nova frase nos motions ... variar os efeitos ... sobrepô-los
... diminuir o som deles ... sutil, fluido, dinâmico". O CapCut da usuária só tinha whoosh, clique de mouse,
autofoco e obturador; aqui cada som é feito do zero (48 kHz, estéreo), com variação pela semente.

Paleta (todas as funções devolvem um array (n, 2) em float, já no nível final):
  ar       sopro de ar filtrado que varre (entrada de cartão, troca de cena)
  tique    toque digital curto e ressonante (checkbox, texto que aparece)
  nota     nota de vidro, suave, na escala pentatônica (pílula, número, barra)
  grave    impacto grave sentido mais que ouvido (título grande)
  traco    traço de caneta que risca (texto riscado), da esquerda para a direita
  papel    folha que desliza e assenta (documento)
  sobe     inchaço de ar que abre o filtro e pousa numa nota (coluna que cresce)
  toc      batida seca e abafada (algo que encaixa)
  rolo     sequência de tiques (lettering letra a letra)
Uso como biblioteca: import sfx_sintese as sfx; sfx.salvar(caminho, sfx.mix([(0.0, sfx.ar()), (0.1, sfx.nota("A5"))]))
"""
import math

import numpy as np
import scipy.io.wavfile as wavfile
import scipy.signal as sinal

SR = 48000
# pentatônica de Ré maior: soa bem sobre qualquer coisa e entre si
NOTAS = {"D5": 587.33, "E5": 659.26, "F#5": 739.99, "A5": 880.0, "B5": 987.77,
         "D6": 1174.66, "E6": 1318.51, "F#6": 1479.98, "A6": 1760.0, "B6": 1975.53}
_rng = np.random.default_rng(24)


def db(x):
    return 10 ** (x / 20)


def n_amostras(seg):
    return max(1, int(round(seg * SR)))


def ruido_rosa(n, rng=None):
    rng = rng or _rng
    b = rng.standard_normal(n)
    f = np.fft.rfft(b)
    k = np.arange(len(f))
    k[0] = 1
    r = np.fft.irfft(f / np.sqrt(k), n)
    return r / (np.abs(r).max() + 1e-9)


def svf(x, corte, q):
    """Filtro de estado variável (TPT) passa-banda com corte que varia por amostra."""
    corte = np.broadcast_to(np.asarray(corte, dtype=float), x.shape)
    k = 1.0 / q
    s1 = s2 = 0.0
    y = np.empty_like(x)
    g_all = np.tan(np.pi * np.clip(corte, 20, SR * 0.45) / SR)
    for i in range(len(x)):
        g = g_all[i]
        a1 = 1.0 / (1.0 + g * (g + k))
        v3 = x[i] - s2
        v1 = a1 * s1 + g * a1 * v3
        v2 = s2 + g * v1
        s1 = 2 * v1 - s1
        s2 = 2 * v2 - s2
        y[i] = v1 * k   # passa-banda normalizado (ganho 1 no centro)
    return y


def passa(x, tipo, f, ordem=2):
    sos = sinal.butter(ordem, f, btype=tipo, fs=SR, output="sos")
    return sinal.sosfilt(sos, x)


def estereo(m, pan=0.0, largura=0.0, rng=None):
    """Mono -> estéreo com pan (de -1 a 1, constante ou por amostra) e um pouco de largura (atraso Haas)."""
    pan = np.broadcast_to(np.asarray(pan, dtype=float), m.shape)
    ang = (pan + 1) * np.pi / 4
    esq, dir_ = m * np.cos(ang), m * np.sin(ang)
    if largura > 0:
        d = int(largura * 0.012 * SR)
        dir_ = 0.7 * dir_ + 0.3 * np.concatenate([np.zeros(d), dir_[:len(dir_) - d]])
    return np.stack([esq, dir_], 1)


_ir = {}


def sala(x, molhado=0.2, tempo=0.55):
    """Reverb curto de sala (resposta ao impulso sintética, estéreo e descorrelacionada)."""
    if molhado <= 0:
        return x
    if tempo not in _ir:
        n = n_amostras(tempo)
        t = np.arange(n) / SR
        rng = np.random.default_rng(7)
        ir = rng.standard_normal((n, 2)) * np.exp(-6.9 * t / tempo)[:, None]
        ir = np.stack([passa(ir[:, c], "lowpass", 5500) for c in range(2)], 1)
        pre = n_amostras(0.012)
        ir = np.concatenate([np.zeros((pre, 2)), ir])
        _ir[tempo] = ir / np.sqrt((ir ** 2).sum(0, keepdims=True))
    ir = _ir[tempo]
    if x.ndim == 1:
        x = np.stack([x, x], 1)
    pad = np.concatenate([x, np.zeros((len(ir), 2))])
    w = np.stack([sinal.fftconvolve(pad[:, c], ir[:, c])[:len(pad)] for c in range(2)], 1)
    return pad * (1 - molhado * 0.5) + w * molhado


def fecha(m, seg=0.04):
    """Rampa de saída no fim do som seco (seno cortado a 3% ainda estala)."""
    k = min(len(m), n_amostras(seg))
    m = m.copy()
    m[-k:] *= np.cos(np.linspace(0, np.pi / 2, k)) ** 2
    return m


def nivel(x, pico_db):
    return x * db(pico_db) / (np.abs(x).max() + 1e-9)


def apara(x, lim=-70):
    """Tira o silêncio do fim (o reverb deixa uma cauda longa)."""
    a = np.abs(x).max(1) if x.ndim == 2 else np.abs(x)
    vivos = np.nonzero(a > db(lim))[0]
    fim = (vivos[-1] + n_amostras(0.02)) if len(vivos) else len(x)
    y = x[:fim].copy()
    m = min(len(y), n_amostras(0.015))
    y[-m:] *= np.linspace(1, 0, m)[:, None] if y.ndim == 2 else np.linspace(1, 0, m)
    return y


# ── sons ──
def ar(dur=0.35, f0=700, f1=3200, pico=0.62, q=1.3, pan0=-0.35, pan1=0.35, db_pico=-26, corpo=0.25, sem=None):
    """Sopro: ruído rosa num passa-banda que varre f0 -> f1, envelope suave com pico em `pico` (fração)."""
    rng = np.random.default_rng(sem)
    n = n_amostras(dur)
    t = np.linspace(0, 1, n)
    env = np.where(t < pico, np.sin(np.pi / 2 * np.minimum(t / pico, 1)) ** 2,
                   np.clip(np.cos(np.pi / 2 * np.clip((t - pico) / (1 - pico), 0, 1)), 0, 1) ** 1.5)
    corte = f0 * (f1 / f0) ** (np.sin(np.pi / 2 * t) ** 1.2)
    r = ruido_rosa(n, rng)
    m = svf(r, corte, q) + corpo * passa(r, "lowpass", 700)
    m = passa(m, "highpass", 120) * env
    return apara(nivel(sala(estereo(fecha(m), np.linspace(pan0, pan1, n), 0.6), 0.18), db_pico))


def tique(freq=3600, db_pico=-30, dur=0.06, pan=0.0, molhado=0.12, sem=None):
    """Toque digital: um impulso num ressonador estreito + um segundo modo inarmônico."""
    rng = np.random.default_rng(sem)
    n = n_amostras(dur)
    exc = np.zeros(n)
    exc[0] = 1.0
    k = n_amostras(0.0025)
    exc[:k] += rng.standard_normal(k) * np.exp(-np.arange(k) / (k / 4)) * 0.6
    m = svf(exc, freq, 14) + 0.45 * svf(exc, freq * 1.47, 10) + 0.25 * svf(exc, freq * 0.5, 4)
    m = passa(m, "highpass", 500) * np.exp(-np.arange(n) / n_amostras(0.012))
    return apara(nivel(sala(estereo(fecha(m, 0.02), pan, 0.3), molhado, 0.4), db_pico))


def nota(nome="A5", db_pico=-30, decai=0.38, pan=0.0, molhado=0.32, brilho=1.0):
    """Nota de vidro: parciais 1, 2, 3 e um inarmônico, cada um decaindo mais rápido; ataque macio de 3 ms."""
    f = NOTAS.get(nome, nome) if isinstance(nome, str) else nome
    dur = decai * 3.2
    n = n_amostras(dur)
    t = np.arange(n) / SR
    m = np.zeros(n)
    for mult, amp, d in [(1.0, 1.0, decai), (2.0, 0.22 * brilho, decai * 0.55), (3.0, 0.07 * brilho, decai * 0.35), (4.17, 0.05 * brilho, decai * 0.2)]:
        m += amp * np.sin(2 * np.pi * f * mult * t + mult) * np.exp(-t / d)
    a = n_amostras(0.003)
    m[:a] *= np.sin(np.linspace(0, np.pi / 2, a)) ** 2
    m += 0.08 * passa(np.random.default_rng(int(f)).standard_normal(n), "highpass", 4000) * np.exp(-t / 0.004)
    return apara(nivel(sala(estereo(fecha(m, decai), pan, 0.4), molhado, 0.7), db_pico))


def grave(f0=96, f1=44, db_pico=-24, decai=0.2, clique=0.12):
    """Impacto grave: seno com queda de afinação, saturação leve e um clique abafado na frente."""
    n = n_amostras(decai * 3.5)
    t = np.arange(n) / SR
    freq = f1 + (f0 - f1) * np.exp(-t / 0.045)
    fase = 2 * np.pi * np.cumsum(freq) / SR
    m = np.sin(fase) * np.exp(-t / decai)
    m[:n_amostras(0.004)] *= np.linspace(0, 1, n_amostras(0.004))
    m = np.tanh(1.6 * m) / np.tanh(1.6)
    k = n_amostras(0.006)
    cl = np.zeros(n)
    cl[:k] = passa(np.random.default_rng(3).standard_normal(k), "lowpass", 1800) * np.linspace(1, 0, k)
    m += clique * cl / (np.abs(cl).max() + 1e-9)
    return apara(nivel(sala(estereo(fecha(m, decai), 0.0, 0.0), 0.06, 0.4), db_pico))


def traco(dur=0.32, db_pico=-31, pan0=-0.5, pan1=0.5, sem=None):
    """Caneta que risca: ruído agudo com textura (granulação) e varredura que desce um pouco."""
    rng = np.random.default_rng(sem)
    n = n_amostras(dur)
    t = np.linspace(0, 1, n)
    env = np.minimum(1, t / 0.05) * np.minimum(1, (1 - t) / 0.2)
    grao = 0.65 + 0.35 * np.abs(passa(rng.standard_normal(n), "lowpass", 45)) * 3
    r = rng.standard_normal(n)
    m = svf(r, 5200 - 1800 * t, 2.2) * env * np.clip(grao, 0, 1.4)
    m = passa(m, "highpass", 1500)
    return apara(nivel(sala(estereo(fecha(m), np.linspace(pan0, pan1, n), 0.3), 0.14), db_pico))


def papel(db_pico=-31, pan=0.0, sem=None):
    """Folha que desliza (sopro agudo curto) e assenta (toque grave abafado)."""
    rng = np.random.default_rng(sem)
    n = n_amostras(0.22)
    t = np.arange(n) / SR
    r = ruido_rosa(n, rng)
    desliza = svf(r, 2600 + 2200 * np.exp(-t / 0.05), 1.1) * np.minimum(1, t / 0.015) * np.exp(-t / 0.05)
    assenta = np.sin(2 * np.pi * 165 * t) * np.exp(-np.maximum(t - 0.05, 0) / 0.03) * (t > 0.05)
    m = passa(desliza, "highpass", 900) + 0.55 * assenta
    return apara(nivel(sala(estereo(fecha(m), pan, 0.4), 0.15), db_pico))


def sobe(dur=0.5, final="A5", db_pico=-29, pan=0.0, sem=None):
    """Inchaço: ruído num passa-baixa que abre (300 -> 3500 Hz) e pousa numa nota curta."""
    rng = np.random.default_rng(sem)
    n = n_amostras(dur)
    t = np.linspace(0, 1, n)
    r = ruido_rosa(n, rng)
    m = svf(r, 300 * (3500 / 300) ** (t ** 1.6), 0.9) * (t ** 1.8) * np.minimum(1, (1 - t) / 0.06)
    swell = estereo(m, pan, 0.6)
    pouso = nota(final, 0, decai=0.22, pan=pan, molhado=0.3)
    out = np.zeros((n + len(pouso), 2))
    out[:n] += nivel(swell, -4)
    out[n - n_amostras(0.01):n - n_amostras(0.01) + len(pouso)] += nivel(pouso, -2)
    return apara(nivel(sala(out, 0.12), db_pico))


def toc(freq=210, db_pico=-30, pan=0.0):
    """Batida seca de madeira abafada: dois modos que somem em ~30 ms e um clique."""
    n = n_amostras(0.12)
    t = np.arange(n) / SR
    m = np.sin(2 * np.pi * freq * t) * np.exp(-t / 0.028) + 0.5 * np.sin(2 * np.pi * freq * 2.3 * t) * np.exp(-t / 0.012)
    k = n_amostras(0.002)
    m[:k] += np.random.default_rng(5).standard_normal(k) * 0.5
    m = passa(m, "lowpass", 3500)
    return apara(nivel(sala(estereo(fecha(m), pan, 0.2), 0.1, 0.4), db_pico))


def rolo(tempos, db_pico=-33, f=(3300, 4600), sem=None):
    """Tiques em sequência (um por letra), afinação variando e intensidade caindo devagar."""
    rng = np.random.default_rng(sem)
    partes = []
    for i, t0 in enumerate(tempos):
        fr = rng.uniform(*f) * (1 + 0.04 * i / max(1, len(tempos) - 1))
        partes.append((t0, tique(fr, db_pico - 3 * i / max(1, len(tempos) - 1) - rng.uniform(0, 2.5),
                                  pan=rng.uniform(-0.3, 0.3), molhado=0.1, sem=int(fr))))
    return mix(partes)


# ── montagem ──
def mix(partes):
    """[(tempo, som)] -> um som só (tempos relativos ao primeiro, que pode ser negativo)."""
    t0 = min(t for t, _ in partes)
    fim = max(n_amostras(t - t0) + len(s) for t, s in partes)
    out = np.zeros((fim, 2))
    for t, s in partes:
        i = n_amostras(t - t0)
        out[i:i + len(s)] += s
    return out


def salvar(caminho, x):
    """WAV 48 kHz 16 bits estéreo (com dither); nada passa de -1 dBFS."""
    pico = np.abs(x).max()
    if pico > db(-1):
        x = x * db(-1) / pico
    d = (_rng.random(x.shape) - _rng.random(x.shape)) / 32768
    wavfile.write(caminho, SR, np.clip(np.round((x + d) * 32767), -32768, 32767).astype(np.int16))
