# Cortes verticais de podcast (Reels 9:16) com legendas dinâmicas do Concat

Processo usado nos podcasts 10 e 11 do Dr. Rafael Almeida (outubro de 2026). As regras abaixo vieram das correções do usuário.

Python: `tools/.venv/bin/python -I`. Pasta de trabalho: variável `TRABALHO`.

## Estrutura da pasta de trabalho
```
$TRABALHO/p<EP>/audio.wav     áudio 16 kHz mono do episódio
$TRABALHO/p<EP>/nomeado.json  transcrição com locutor por segmento
$TRABALHO/p<EP>/fonte.txt     caminho do vídeo do episódio
$TRABALHO/p<EP>/saida.txt     pasta de saída (…/<EP>/Cortes)
$TRABALHO/c<EP>/<ID>/         um corte: corte.json, words.json, vertical.mp4, plano.json…
$TRABALHO/c<EP>/overrides.json   {"M03": "s-e,s-e"}: trechos no lugar dos do clip-builder
$TRABALHO/c<EP>/destaques.txt    frases de destaque por corte (formato do edit-director)
```

## Passo a passo
1. **Transcrição:** `transcrever.py turbo audio.wav turbo.json` (mlx-whisper large-v3-turbo; ~8 min para 90 min). O faster-whisper medium fica só para cada corte (`conferir.py`); no episódio inteiro ele leva horas.
2. **Quem fala:**
   - `rotular.py` mede o F0 de cada segmento: abaixo de 158 Hz é voz M, acima é F (o vale fica perto de 160 Hz).
   - A câmera no ar vem de quadros 32x18 a 4 fps, lidos com `ffmpeg -hwaccel videotoolbox`.
   - `nomear.py` junta voz + câmera e dá o nome (ex.: host M = Dr. Rafael).
   - Confira os nomes na abertura do episódio. No ep. 11, o convidado também se chamava Rafael.
3. **Seleção** com a skill corte-viral (`vch init <vídeo> nomeado.json --workspace $TRABALHO/runs`, `prepare`, `digest`):
   - context-mapper → clip-hunter → `vch digest --windows` → clip-builder → `vch audit` / `vch dedupe` (+ clip-deduplicator) → edit-director, que dá as frases de destaque.
   - Peça pelo menos 8 cortes e priorize as falas do cliente.
4. **Montagem + enquadramento:** `lote.sh <EP> <run> M01 M02 …` (montar_corte → enquadrar → estabilizar → render_vertical → conferir).
5. **Texto:** `corrigir.py <corte> '{"de": "para"}'` (por texto, não por índice) e revisão ortográfica do `words_leg.json`.
6. **Legenda + export:** `final_lote.sh <EP> "M01=01 - Título" …`:
   - plano_auto + destaques + legendar_corte;
   - projeto temporário em `dist/verificacao/_cortes`, apagado no fim;
   - export 1080x1920, 30 fps, SDR (`hdr=False`);
   - `recentes.py` limpa a lista de projetos.
7. **Volume:** `volume.sh *.mp4` faz loudnorm em 2 passadas para −14 LUFS / −1,5 dBTP (a fonte vem em −23 a −29 LUFS).
8. **Conferência:**
   - `folha_geral.py` monta 5 quadros por corte numa folha só;
   - a duração do MP4 tem que bater com a do `vertical.mp4`;
   - a transcrição do medium sobre o vídeo montado mostra as palavras em cada emenda.

## Regras do usuário
- **Nunca cortar no meio da fala.**
  - O Whisper erra os tempos (frase rápida "espremida") e às vezes pula palavras: "sem saber o que fazer" sumiu do turbo.
  - O `montar_corte` encaixa cada borda na pausa real (energia < −34 dB; procura até 0,6 s depois do fim e 0,6 s antes do início).
  - Se a fala emenda sem pausa, **não corte ali**: deixe o trecho contínuo. Bordas conferidas à mão vão em `<corte>/fixos.json`.
  - Final forçado em `<corte>/fim.json`.
  - **Sempre** transcreva o `vertical.mp4` com o medium e leia as palavras de cada emenda antes de exportar.
- **Nada de limiar absoluto de energia** para aparar palavra: o podcast é baixo e −30 dB comia palavras inteiras. A folha sobre o Whisper é −0,15 s / +0,35 s.
- **Deixar a pessoa concluir** a frase no fim do corte e no fim de cada trecho.
- **Enquadramento sem pulo no X:**
  - Cada pessoa tem um X fixo no plano normal, e nas trocas de take alterna zoom leve 100% ↔ 112%. Só o plano com zoom recentraliza no rosto (`estabilizar.py`).
  - Rosto a mais de 0,035 da largura longe do X fixo → esse take entra com zoom.
  - Câmera aberta (3 ou mais rostos) → quadro inteiro sobre fundo desfocado.
  - Não há tela dividida: o podcast já vem editado com uma câmera por vez.
- **Legenda:**
  - Branca. Composições (escada/chave) nas frases de destaque, com a chave em Scholar; amarelo #f4c430 em 1 ou 2 por corte. `sombra_suave` + contorno 0,02.
  - Primeira palavra do vídeo em maiúscula. No resto, maiúscula só depois de "?"/"!" e em nome próprio/sigla (lista `PROPRIOS` em plano_auto.py).
  - Revisão ortográfica sem mudar palavra nem ordem. Palavra que ninguém entende sai do corte (áudio e legenda).
  - A última legenda termina antes do fim do vídeo. O Concat exportava 1 quadro preto com a legenda; o `finalizar.sh` agora confere e tira.
- **Escopo:** quando ele comentar vídeos específicos, mexa **só** neles.
- **Formato:** 1080x1920 serve, sem B-roll, MP4 direto na pasta do podcast, sem projeto do Concat na lista.

## Armadilhas do Concat
- O app pode fechar no meio de um lote. Aí a API recusa a conexão e o MP4 antigo fica no lugar sem erro visível. Confira `nc -z 127.0.0.1 7420` e compare as durações depois de exportar.
- A lista de recentes guarda 12. O projeto temporário empurra um projeto do usuário para fora; `recentes.py` devolve (backup em `$TRABALHO/recents_backup.json`, criado no 1º export).
- O ffmpeg do Homebrew daqui não tem `drawtext`.
- No zsh, `$var:l…` vira modificador: use `${var}`.

## Lições do podcast 9 (2026-10-20)
- **Câmera piscando no início de uma resposta:** uma peça de enquadramento com menos de 0,4 s (ex.: 3 quadros da câmera dos apresentadores antes de virar para o convidado) aparece como um "pisco". Liste as peças curtas do `corte.json`, copie para elas o enquadramento da peça anterior (`cx`, `cy`, `fh`, `layout`, `quem`, `z`) e rode `render_vertical.py` + `finalizar.sh` + `volume.sh` só nesse corte.
- **Início do corte na fala de outra pessoa:** o `montar_corte` recua até 0,6 s procurando pausa e pode puxar o fim da pergunta ("também, né?"). Confira a 1ª palavra do `texto.txt` e, se precisar, grave o início certo em `fixos.json`.
- **Nomes do episódio:** acrescente na lista `PROPRIOS` do `plano_auto.py` (ex.: Simone, Farah, Rio, Janeiro, São, Paulo, Minas, Gerais).
- Ep. 9 levou ~25 min do bruto aos 8 MP4: transcrição turbo 6 min, lote de montagem 8 min, legendas + export no Concat 12 min.
