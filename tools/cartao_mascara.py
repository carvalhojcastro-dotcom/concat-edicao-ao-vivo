"""Aplica a máscara de cartão (retângulo de cantos arredondados) do kit a uma imagem.

Uso: cartao_mascara.py <entrada> <saida.png> [largura=0.898] [altura=0.691] [centroY=0.092] [cantos=0.23]
Os valores são os do CapCut: frações da imagem, centroY para cima, cantos como fração da metade do lado menor.
"""
import sys

from PIL import Image, ImageDraw

src, out = sys.argv[1], sys.argv[2]
w_f, h_f, cy_f, round_f = (float(x) for x in (sys.argv[3:7] + ["0.898", "0.691", "0.092", "0.23"][len(sys.argv[3:7]):]))
im = Image.open(src).convert("RGBA")
W, H = im.size
mw, mh = w_f * W, h_f * H
cx, cy = W / 2, H / 2 - cy_f * H / 2
r = round_f * min(mw, mh) / 2
SS = 4
mask = Image.new("L", (W * SS, H * SS), 0)
ImageDraw.Draw(mask).rounded_rectangle([(cx - mw / 2) * SS, (cy - mh / 2) * SS, (cx + mw / 2) * SS, (cy + mh / 2) * SS], radius=r * SS, fill=255)
mask = mask.resize((W, H), Image.LANCZOS)
im.putalpha(Image.composite(im.getchannel("A"), Image.new("L", (W, H), 0), mask))
im.save(out)
print(out)
