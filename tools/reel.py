#!/usr/bin/env python3
"""Etapas mecânicas da edição de reels (ver EDICAO.md), num lugar só.

Rode com o python do venv: tools/.venv/bin/python tools/reel.py <comando> ...

  novo <projeto> <video>                 cria o projeto 2160x3840 a 30 fps, importa o vídeo e o põe em T1
  transcrever <video> <trabalho>         áudio 16 kHz, Whisper (tempo por palavra), mapa de silêncios;
                                         imprime as frases com tempo, para escolher as tomadas
  cortes <trabalho> <trechos>            trechos = "ini-fim,ini-fim" (início da 1ª palavra e fim da
                                         última, tempos do Whisper, da tomada boa de cada trecho).
                                         Gera keep.json, words.json (legendas) e cortes.json
  aplicar <projeto> <trabalho>           corta, 1.05x sem folgas, alinha à grade de quadros e salva
  nitidez <projeto>                      camada concat.adjust (sharpen 20.23) em T3
  listar <projeto>                       legendas com índice (para montar os planos)
  fechar <projeto>                       salva e solta o projeto da API (senão a janela não abre)

Fica para quem edita (a skill/o editor): escolher as tomadas, os planos de dinâmicas, zoom e
B-roll, e conferir os quadros.
"""
import json
import os
import subprocess
import sys
import wave

AQUI = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, AQUI)
from concat_api import Concat, timeline  # noqa: E402

VELOCIDADE = 1.05
LIMIAR_PAUSA = -36.0   # dB RMS: abaixo disso por >= 0,15 s é pausa (respiração incluída)
LIMIAR_VOZ = -30.0     # dB RMS: a 1ª/última batida de voz de um trecho
JANELA = 0.025         # s
PAUSA_MIN = 0.21       # s de fonte (~0,2 s na timeline a 1.05x)
RESPIRO = 0.0525       # s deixados de cada lado de um corte de pausa
FOLGA_BORDA = 0.06     # s antes/depois da voz na borda de um trecho


def api_de(projeto):
    api = Concat(projeto)
    api.sock.settimeout(600)
    try:
        api.call("project.get", path=projeto)   # aberto na janela? então é ela que responde
    except RuntimeError:
        api.call("project.open", path=projeto)
    return api


def novo(projeto, video, largura=2160, altura=3840, fps=30):
    projeto = os.path.abspath(projeto)
    api = Concat(projeto); api.sock.settimeout(600)
    if not os.path.exists(os.path.join(projeto, "concat.json")):
        api.call("project.create", location=os.path.dirname(projeto), name=os.path.basename(projeto),
                 video={"width": largura, "height": altura, "rateNum": fps, "rateDen": 1})
    v = api.call("project.open", path=projeto)
    if not v["project"]["media"]:
        api.call("media.import", path=projeto, file=os.path.abspath(video))
    v = api.view()
    tl = timeline(v)
    if not tl["clips"]:
        api.edit({"op": "addClip", "mediaId": v["project"]["media"][0]["id"],
                  "trackId": tl["tracks"][0]["id"], "start": 0.0})
    api.call("project.save", path=projeto)
    m = api.view()["project"]["media"][0]
    print(f"projeto {projeto}: {m['width']}x{m['height']}, {m['duration']:.2f}s, {fps} fps na timeline")


def _rms(wav):
    import numpy as np
    w = wave.open(wav); sr = w.getframerate()
    x = np.frombuffer(w.readframes(w.getnframes()), dtype=np.int16).astype(np.float32) / 32768
    h = int(sr * JANELA); n = len(x) // h
    return 20 * np.log10(np.sqrt((x[:n * h].reshape(n, h) ** 2).mean(1)) + 1e-9)


def transcrever(video, trabalho):
    import numpy as np
    os.makedirs(trabalho, exist_ok=True)
    wav = os.path.join(trabalho, "audio.wav")
    subprocess.run(["ffmpeg", "-v", "error", "-y", "-i", video, "-vn", "-ac", "1", "-ar", "16000", wav], check=True)
    import mlx_whisper
    r = mlx_whisper.transcribe(wav, path_or_hf_repo="mlx-community/whisper-large-v3-turbo", language="pt",
                               word_timestamps=True, condition_on_previous_text=False)
    json.dump(r, open(os.path.join(trabalho, "transcript.json"), "w"), ensure_ascii=False)
    rms = _rms(wav)
    np.save(os.path.join(trabalho, "rms.npy"), rms)
    quieto = rms < LIMIAR_PAUSA; sil = []; i = 0
    while i < len(rms):
        if quieto[i]:
            j = i
            while j < len(rms) and quieto[j]:
                j += 1
            if (j - i) * JANELA >= 0.15:
                sil.append((i * JANELA, j * JANELA))
            i = j
        else:
            i += 1
    json.dump(sil, open(os.path.join(trabalho, "sil_rms.json"), "w"))
    dur = float(subprocess.run(["ffprobe", "-v", "error", "-show_entries", "format=duration", "-of", "csv=p=0", video],
                               capture_output=True, text=True).stdout.strip())
    json.dump({"duracao": dur, "video": os.path.abspath(video)}, open(os.path.join(trabalho, "info.json"), "w"))
    for s in r["segments"]:
        print(f"{s['start']:7.2f}-{s['end']:7.2f} {s['text'].strip()}")


def cortes(trabalho, trechos):
    import numpy as np
    r = json.load(open(os.path.join(trabalho, "transcript.json")))
    palavras = [w for s in r["segments"] for w in s["words"]]
    sil = json.load(open(os.path.join(trabalho, "sil_rms.json")))
    rms = np.load(os.path.join(trabalho, "rms.npy"))
    dur = json.load(open(os.path.join(trabalho, "info.json")))["duracao"]
    escolhas = [tuple(float(x) for x in t.split("-")) for t in trechos.split(",")]
    keep = []
    for a, b in escolhas:
        # não invade a palavra de antes nem a de depois (outra tomada), mesmo que o Whisper erre
        antes = [w["end"] for w in palavras if w["end"] <= a + 0.05]
        depois = [w["start"] for w in palavras if w["start"] >= b - 0.05]
        ini_busca = max(a - 0.4, (max(antes) + 0.02) if antes else 0.0)
        fim_busca = min(b + 0.5, (min(depois) - 0.02) if depois else b + 0.5)
        i = int(ini_busca / JANELA)
        while i < len(rms) and rms[i] <= LIMIAR_VOZ:
            i += 1
        j = min(int(fim_busca / JANELA), len(rms) - 1)
        while j > i and rms[j] <= LIMIAR_VOZ:
            j -= 1
        keep.append([round(i * JANELA - FOLGA_BORDA, 3), round((j + 1) * JANELA + FOLGA_BORDA, 3)])
    # palavras que cruzam os trechos; a 1ª costuma vir marcada cedo, então o corte de borda vale
    kw = []
    for w in palavras:
        for s, e in keep:
            if w["end"] > s + 0.1 and w["start"] < e - 0.05:
                kw.append(dict(w, start=max(w["start"], s + 0.06), end=min(w["end"], e - 0.06)))
                break
    # junta pedaços com hífen ("sente" + "-se") e põe maiúscula em início de frase
    junto = []
    for w in kw:
        t = w["word"].strip()
        if t.startswith("-") and junto:
            junto[-1] = dict(junto[-1], word=" " + junto[-1]["word"].strip() + t, end=w["end"])
        else:
            junto.append(w)
    for i, w in enumerate(junto):
        t = w["word"].strip()
        if t and (i == 0 or junto[i - 1]["word"].strip().endswith((".", "?", "!"))):
            w["word"] = " " + t[0].upper() + t[1:]
    json.dump(keep, open(os.path.join(trabalho, "keep.json"), "w"))
    json.dump(junto, open(os.path.join(trabalho, "words.json"), "w"), ensure_ascii=False)
    corte, prev = [], 0.0
    for s, e in keep:
        if s - prev > 0.01:
            corte.append([round(prev, 4), round(s, 4)])
        for a, b in sil:
            lo, hi = max(a, s), min(b, e)
            if hi - lo >= PAUSA_MIN and lo > s + 0.05 and hi < e - 0.05:
                corte.append([round(lo + RESPIRO, 4), round(hi - RESPIRO, 4)])
        prev = e
    corte.append([round(prev, 4), dur])
    json.dump(corte, open(os.path.join(trabalho, "cortes.json"), "w"))
    fica = dur - sum(b - a for a, b in corte)
    print("trechos:", keep)
    print(f"{len(junto)} palavras: " + " ".join(w["word"].strip() for w in junto))
    print(f"{len(corte)} cortes; fica {fica:.2f}s -> {fica / VELOCIDADE:.2f}s a {VELOCIDADE}x")
    print("confira o texto: erros do Whisper se corrigem editando words.json antes das legendas")


def aplicar(projeto, trabalho):
    subprocess.run([sys.executable, os.path.join(AQUI, "cortar_ao_vivo.py"), projeto,
                    os.path.join(trabalho, "cortes.json"), "--pausa", "0"], check=True)
    api = api_de(projeto)
    clips = sorted([c for c in timeline(api.view())["clips"] if c["kind"] == "video"], key=lambda c: c["start"])
    cmds, t, moves = [{"op": "setClipSpeed", "clipId": c["id"], "speed": VELOCIDADE} for c in clips], 0.0, []
    for c in clips:
        moves.append({"clipId": c["id"], "start": t, "trackId": c["trackId"]}); t += c["duration"] / VELOCIDADE
    cmds.append({"op": "moveClips", "moves": moves})
    api.batch(cmds)
    api.call("project.save", path=projeto)
    subprocess.run([sys.executable, os.path.join(AQUI, "alinhar_quadros.py"), projeto], check=True)
    api.call("project.save", path=projeto)
    v = sorted([c for c in timeline(api.view())["clips"] if c["kind"] == "video"], key=lambda c: c["start"])
    print(f"{len(v)} clipes a {VELOCIDADE}x; duração {v[-1]['start'] + v[-1]['duration']:.2f}s")


def nitidez(projeto):
    api = api_de(projeto)
    tl = timeline(api.view())
    fim = max(c["start"] + c["duration"] for c in tl["clips"] if c["kind"] == "video")
    for c in [c for c in tl["clips"] if c["kind"] == "layer"]:
        api.edit({"op": "removeClips", "clipIds": [c["id"]], "ripple": False})
    tl = timeline(api.edit({"op": "addLayerClip", "trackId": "T3", "start": 0.0, "duration": fim,
                            "effectId": "concat.adjust", "name": "Ajuste"}))
    camada = next(c for c in tl["clips"] if c["kind"] == "layer")
    api.edit({"op": "updateClip", "clipId": camada["id"], "patch": {"videoEffects": [
        {"enabled": True, "id": "concat.adjust", "params": {"sharpen": 20.23}}]}})
    api.call("project.save", path=projeto)
    print(f"nitidez 20.23 em T3, 0 a {fim:.2f}s")


def listar(projeto):
    api = api_de(projeto)
    t = sorted([c for c in timeline(api.view())["clips"] if c["kind"] == "text"], key=lambda c: c["start"])
    print(" ".join(f"{i}:{c['text']['content']}" for i, c in enumerate(t)))
    print("tempos:", " ".join(f"{i}@{c['start']:.2f}" for i, c in enumerate(t)))


def fechar(projeto):
    api = Concat(projeto)
    try:
        api.call("project.close", path=projeto, save=True)
        print("projeto salvo e solto da API")
    except RuntimeError as e:
        print("nada a fechar:", e)


if __name__ == "__main__":
    if len(sys.argv) < 3:
        sys.exit(__doc__)
    cmd, args = sys.argv[1], sys.argv[2:]
    {"novo": novo, "transcrever": transcrever, "cortes": cortes, "aplicar": aplicar,
     "nitidez": nitidez, "listar": listar, "fechar": fechar}[cmd](*args)
