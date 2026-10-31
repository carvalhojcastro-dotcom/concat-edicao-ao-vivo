# Planos de exemplo

Formatos que as ferramentas leem. Os índices são das legendas simples, na ordem da timeline
(`tools/reel.py listar <projeto>`).

- `blocos.json` → `capcut_legendas_ig.py`: os blocos dinâmicos; cada um tem `linhas` (índices contíguos do
  words.json, agrupados por linha), `chave` (os índices em destaque) e, na frase de fecho, `"fecho": true`.
  A legenda simples sai sozinha das outras palavras.
- `zoom.json` → `zoom_cortes.py`: `trechos` = `[índice da 1ª palavra da frase, escala]`; vale até o
  próximo trecho. Depois rode `centralizar_zoom.py`.
- `broll.json` → `broll_higgsfield.py` / `broll_imagens.py`: `inicio` e `fim` na timeline (segundos),
  `nome` (vira o arquivo) e `prompt` (inglês, só descrição positiva).
- `sfx_motion.json` → `sfx_motion.py`: efeitos sonoros dos motions. Por cena, `inicio`/`dur` na timeline e
  `eventos` (um por elemento que entra), cada um com `camadas` (`t` dentro da cena, `som` de `sfx_sintese.py`
  e os argumentos dele). Como escolher e variar: skill `sfx-motion`.

Os planos reais de cada vídeo ficam fora do Git (`tools/planos/`).
