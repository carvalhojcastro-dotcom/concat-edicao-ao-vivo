"""Renderiza quadros de um projeto (que NÃO esteja aberto na janela) e junta numa folha.

Uso: quadros.py <pasta do projeto> <saida.jpg> t1 t2 ...  (segundos da timeline)
"""
import os, subprocess, sys, tempfile
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from concat_api import Concat

path, out, times = sys.argv[1], sys.argv[2], [float(t) for a in sys.argv[3:] for t in a.split()]
api = Concat(path); api.sock.settimeout(300)
api.call("project.open", path=path)
base = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "dist", "verificacao")
os.makedirs(base, exist_ok=True)
d = tempfile.mkdtemp(dir=base)
files = []
for n, t in enumerate(times):
    f = os.path.join(d, f"q{n:02d}.png")
    api.call("preview.frame", path=path, time=t, output=f, width=540, height=960)
    files.append(f)
api.call("project.close", path=path, save=False)
cols = min(len(files), 4)
args = sum([["-i", f] for f in files], [])
labels = "".join(f"[{i}]scale=360:-1[v{i}];" for i in range(len(files)))
pad = (-len(files)) % cols
filt = labels + "".join(f"[v{i}]" for i in range(len(files))) + f"xstack=inputs={len(files)}:layout=" + "|".join(
    f"{(i % cols) * 360}_{(i // cols) * 640}" for i in range(len(files))) + ":fill=black"
subprocess.run(["ffmpeg", "-v", "error", "-y", *args, "-filter_complex", filt, out], check=True)
for f in files: os.remove(f)
os.rmdir(d)
print(out)
