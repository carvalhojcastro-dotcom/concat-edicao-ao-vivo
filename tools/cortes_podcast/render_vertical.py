"""Renderiza o vertical limpo (sem legenda) de um corte já enquadrado.

Uso: render_vertical.py <corte.json> <saida.mp4> [--prev]   (--prev: 540x960 rápido para conferir)
Cada peça vira um crop fixo 9:16 em quem fala (altura cheia; zoom z>1 aperta em volta do rosto).
O áudio sai dos segmentos (mesmas bordas de quadro), sem ajuste.
"""
import json, os, subprocess, sys, tempfile

FPS = 30
SW, SH = 1920, 1080


def crop(p):
    z = p.get("z", 1.0)
    h = SH / z
    w = h * 9 / 16
    cx = p["cx"] * SW
    x = min(max(cx - w / 2, 0), SW - w)
    # com zoom, mantém o rosto na mesma altura relativa que teria no crop cheio
    cy = p["cy"] * SH
    y = min(max(cy - (cy / SH) * h, 0), SH - h)
    return int(round(w / 2) * 2), int(round(h / 2) * 2), int(round(x)), int(round(y))


def main():
    cfg = json.load(open(sys.argv[1]))
    out = os.path.abspath(sys.argv[2])
    prev = "--prev" in sys.argv
    OW, OH = (540, 960) if prev else (1080, 1920)
    tmp = tempfile.mkdtemp(prefix="vert_", dir=os.path.dirname(out))
    lista = []
    for n, p in enumerate(cfg["pecas"]):
        nq = int(round((p["e"] - p["s"]) * FPS))
        if nq <= 0:
            continue
        w, h, x, y = crop(p)
        arq = os.path.join(tmp, f"{n:03d}.mp4")
        vf = f"crop={w}:{h}:{x}:{y},scale={OW}:{OH}:flags=lanczos,setsar=1,format=yuv420p"
        if p.get("wide"):
            fh = int(OW * 9 / 16) // 2 * 2
            vf = (f"split[a][b];[a]scale={OW}:{OH}:force_original_aspect_ratio=increase,crop={OW}:{OH},boxblur=24:2,eq=brightness=-0.08[bg];"
                  f"[b]scale={OW}:{fh}:flags=lanczos[fg];[bg][fg]overlay=0:{int((OH - fh) * 0.36)},setsar=1,format=yuv420p")
        enc = (["-c:v", "libx264", "-preset", "ultrafast", "-crf", "23"] if prev else
               ["-c:v", "h264_videotoolbox", "-b:v", "30M", "-maxrate", "40M", "-profile:v", "high"])
        subprocess.run(["ffmpeg", "-v", "error", "-y", "-nostdin", "-ss", f"{p['s']:.4f}", "-i", cfg["src"],
                        "-frames:v", str(nq), "-an", "-vf", vf, "-r", str(FPS), *enc,
                        "-color_primaries", "bt709", "-color_trc", "bt709", "-colorspace", "bt709",
                        arq], check=True)
        lista.append(arq)
    with open(os.path.join(tmp, "lista.txt"), "w") as f:
        for a in lista:
            f.write(f"file '{a}'\n")
    video = os.path.join(tmp, "video.mp4")
    subprocess.run(["ffmpeg", "-v", "error", "-y", "-f", "concat", "-safe", "0", "-i", os.path.join(tmp, "lista.txt"),
                    "-c", "copy", video], check=True)
    # áudio: atrim dos segmentos e concat
    segs = cfg["segmentos"]
    fc = "".join(f"[0:a]atrim={s:.4f}:{e:.4f},asetpts=PTS-STARTPTS,afade=t=in:d=0.01,afade=t=out:st={max(0, e - s - 0.012):.4f}:d=0.012[a{i}];"
                 for i, (s, e) in enumerate(segs))
    fc += "".join(f"[a{i}]" for i in range(len(segs))) + f"concat=n={len(segs)}:v=0:a=1[a]"
    audio = os.path.join(tmp, "audio.m4a")
    subprocess.run(["ffmpeg", "-v", "error", "-y", "-nostdin", "-i", cfg["src"], "-filter_complex", fc, "-map", "[a]",
                    "-c:a", "aac", "-b:a", "256k", "-ar", "48000", audio], check=True)
    subprocess.run(["ffmpeg", "-v", "error", "-y", "-i", video, "-i", audio, "-map", "0:v", "-map", "1:a",
                    "-c", "copy", "-shortest", "-movflags", "+faststart", out], check=True)
    subprocess.run(["rm", "-rf", tmp])
    print("ok", out)


if __name__ == "__main__":
    main()
