# Planos de exemplo

Formatos que as ferramentas leem. Os índices são das legendas simples, na ordem da timeline
(`tools/reel.py listar <projeto>`).

- `dinamicas.json` → `legendas_dinamicas.py`: cada bloco tem `estilo`, `linhas` (índices contíguos,
  agrupados por linha) e `chave` (os índices em destaque).
- `zoom.json` → `zoom_cortes.py`: `trechos` = `[índice da 1ª palavra da frase, escala]`; vale até o
  próximo trecho. Depois rode `centralizar_zoom.py`.
- `broll.json` → `broll_higgsfield.py` / `broll_imagens.py`: `inicio` e `fim` na timeline (segundos),
  `nome` (vira o arquivo) e `prompt` (inglês, só descrição positiva).

Os planos reais de cada vídeo ficam fora do Git (`tools/planos/`).
