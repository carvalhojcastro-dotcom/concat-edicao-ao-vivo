# Cortes verticais de podcast (Reels 9:16) com as legendas padrão (estilo IG)

Processo usado nos podcasts 10 e 11 do Dr. Rafael Almeida (outubro de 2026). As regras abaixo vieram das correções do usuário.

Python: `tools/.venv/bin/python -I`. Pasta de trabalho: variável `TRABALHO`.

## Estrutura da pasta de trabalho
```
$TRABALHO/p<EP>/audio.wav     áudio 16 kHz mono do episódio
$TRABALHO/p<EP>/nomeado.json  transcrição com locutor por segmento
$TRABALHO/p<EP>/fonte.txt     caminho do vídeo do episódio
$TRABALHO/p<EP>/saida.txt     pasta de saída (…/<EP>/Cortes)
$TRABALHO/c<EP>/<ID>/         um corte: corte.json, words.json, words_leg.json, vertical.mp4, blocos.json…
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
   - plano_auto (texto: correções e maiúsculas → words_leg.json) + destaques (frases de destaque → blocos.json)
     + legendar_corte (`capcut_legendas_ig.py --concat=`: legenda simples + blocos);
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
  - O estilo único das legendas (EDICAO.md seção 2, desde 2026-10-29): Poppins branca, simples de 1 a 4 palavras +
    blocos dinâmicos nas frases de destaque (chave grande), sombra suave, sem contorno, sem animação, sem cor. Os
    estilos antigos (escada/chave/sanduíche, serifada, amarelo) foram apagados.
  - Primeira palavra do vídeo em maiúscula. No resto, maiúscula só depois de "?"/"!"/ponto final e em nome próprio/sigla (lista `PROPRIOS` em plano_auto.py).
  - Sem ponto final na tela (2026-11-01): o `capcut_legendas_ig.py` não desenha o ponto, mas ele continua separando as legendas e dando a maiúscula da frase seguinte.
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

## Windows
Os `.sh` deste processo (lote, finalizar, final_lote, volume) são do Mac (zsh). No Windows, rode os
passos Python um a um; transcrição, codificador e lista de recentes já passam por `tools/plataforma.py`.

## Escopo
Quando o usuário aponta um corte, mexa **só nele** ("só mude o vídeo que eu mencionei"); não refaça os
outros por iniciativa própria.

## Cortes no CapCut (desde o Podcast 12 do Dr. Rafael, 2026-11-10)
Projetos editáveis no CapCut em vez de MP4 do Concat, com os scripts de `capcut/`. Pasta de trabalho `W` com
`config.json` (ver `capcut/comum.py`), `audio.wav`, `turbo.json` → `rotulado.json` (rotular.py) e `cortes.txt`.
1. **Seleção:** da pergunta até o fim da resposta, sem cortar pausas nem respirações. In/out em silêncio: use
   `capcut/bordas.py W palavras a b` e `capcut/bordas.py W energia a-b`. O foco é quem o usuário pedir (no Humman 01,
   o convidado). Fala ininteligível no fim sai.
2. **Enquadramento:** `capcut/analisar.py W id in out`, depois `capcut/enquadrar.py W id in out volume`, que grava
   `c<id>/plano.json`. Regras:
   - Corte seco só na troca de câmera ou de pessoa.
   - X fixo por pessoa e câmera, com o corpo centrado.
   - Keyframes de X só quando a pessoa se desloca e fica no novo lugar.
3. **Volume:** ganho = mín(−16 − LUFS, −1 − pico), com o ebur128 no trecho do bruto. Cabe no `plano.json` como
   `volume`.
4. **Texto:** `capcut/transcrever_cortes.py W` gera o turbo e o medium. `capcut/comparar.py W id` mostra onde eles
   divergem. Grave as correções em `c<id>/correcoes_tl.json`, depois rode
   `capcut/preparar_legenda.py W id duração` para gerar `words_leg.json`, e `destaques.py` para gerar `blocos.json`.
   - Nenhum bloco enquanto a headline está na tela, nos primeiros 7 s.
5. **Projeto:**
   - `capcut_novo.py "<EP02C01 …>" "<nome>" <bruto>`
   - `capcut_podcast.py <pasta> plano.json`
   - `capcut/headline.py <pasta> "Linha 1\nLinha 2" 7.0 0.0 0.80`
   - `capcut_legendas_ig.py <pasta> words_leg.json blocos.json`
   - Cor e filtro, quando pedirem (Dra Márcia e JFIT, 2026-11-13): `capcut/cor.py <pasta> --nitidez 15 --exposicao 2
     --filtro 20` (camada de ajuste + "Crepúsculo dos sonhos"). O modelo EP02C01 não tem retoque de rosto nem
     maquiagem; confira isso antes de trocar de modelo quando pedirem "sem filtros de rosto".
   - CapCut FECHADO.
6. **Conferência:**
   - `capcut/emendas.py <bruto> <pastas…>`: nenhum pedaço pode mostrar quadro de outro plano.
   - `capcut/previa.py`: folha com enquadramento, headline e legendas.
- **Armadilhas (Humman 01, 2026-11-10):**
  - Num `while read` de vários projetos, passe `</dev/null` para cada ferramenta. O ffmpeg do `capcut_novo.py` lê a
    entrada e come o 1º caractere da linha seguinte (o "0" de "02").
  - Câmeras pela cor do canto (`camera_por_cor` no config) quando um plano aberto tem só um rosto detectado.
  - Plano aberto com escala 5 (`escala_mesa`) e o rosto do convidado a ~36% da altura.
- **Dois convidados no mesmo plano (JFIT, 2026-11-13):** a voz M/F não separa (o Jonas sai "F"), então
  `decide_pela_boca: ["G"]` escolhe pela boca. Ela erra quando quem escuta ri ou acena: a Renata contava a história e o
  Jonas ficava na tela por 23 s. Depois do `enquadrar.py`, leia o texto de cada pedaço G (quem está contando?) e
  force pelo conteúdo com `"falantes": {"<id>": [[t0 do bruto, t1, "renata"], ...]}` no config, e rode de novo.
- **Plano aberto parado numa pessoa:** `"mesa": {"modo": "fixo", "nome": "joao", "cx": 0.885, "cy": 0.27}` (Márcia:
  o plano aberto só entra quando o João pergunta) ou `{"modo": "voz", "M": {...}, "F": {...}}`.
- **Exportar o MP4** é só pela tela do CapCut (não há linha de comando): precisa do Computer use ligado no app do
  Claude, senão o usuário exporta.
- **Quando quem fala olha para o outro (2026-11-10, Humman 01):** corte seco para a outra pessoa em tela cheia nesse trecho, e
  depois volta para quem fala. É "uma vez ou outra", e NÃO em tela dividida ("pode ser só um corte normal").
  - `capcut/olhar.py W id` mede o giro da cabeça. No Humman o convidado fica à esquerda da câmera dos apresentadores:
    - a Myrian olhando para o João: giro > +0,10;
    - o João olhando para a Myrian: giro < −1,4 (vira de perfil); olhando para o convidado, entre −0,3 e −1.
  - Trechos sustentados por ≥ 1,4 s: `capcut/dividir.py W id "t0-t1:myrian"`.
    - O modo `"t0-t1:joao/myrian"` faz a tela dividida, que só vale se ele pedir.
  - Depois, rode `capcut_podcast.py` de novo e o `emendas.py`.
- **Só legendas num corte que ele já montou (Marcia C01, 2026-11-14):** ele corta, acelera (1.2x) e cola trechos além
  do corte original; não mexa em clipe, velocidade, headline (ele a pôs num clipe composto) nem filtro.
  `capcut/transcrever_timeline.py <pasta> <bruto> W id` transcreve a timeline dele (trechos do bruto em 1x, palavras
  levadas pedaço a pedaço); depois `comparar.py`, `preparar_legenda.py`, `destaques.py` e `capcut_legendas_ig.py`, que
  só troca as trilhas "Legendas IG". Ele pediu mais blocos de destaque: ~13 por minuto (32 em 2:29).
  - O CapCut pode reabrir sozinho segundos depois do primeiro `quit`: confira o `pgrep` de novo antes de gravar.
- **Zoom seco ao longo do corte (JFIT C04 a C10, 2026-11-14):** "adicione cortes para poder dar zoom in e zoom out ao
  longo de todo o video ... Esse vai e volta é bom pra dar dinamicidade".
  - Comando: `capcut_zoom_podcast.py <pasta> <words.json da timeline>`. As palavras saem de `capcut/transcrever_timeline.py`.
  - Divide os takes longos em trechos de ~4,5 s, no começo de uma frase, e alterna normal e zoom de 1,18x. O rosto fica
    no mesmo lugar da tela e não há keyframe.
  - Rode uma vez por projeto: rodar de novo multiplica o zoom.
  - Bruto 1080p já está em escala 3,2: não passe muito de 1,2.
- **Ela esticou o clipe e faltou legenda:** `capcut_legendas_ig.py <pasta> <words do trecho novo> <blocos> --acrescentar`.
  As legendas dela ficam; as novas entram no espaço livre das trilhas "Legendas IG".
- **Dra. Camilee Tostes (2026-11-19):** 10 cortes a 1.1x, cada um da pergunta ao fim da resposta e sem cortes
  internos ("evite muitos cortes de respirações e erros"). Pasta de trabalho durável em
  `Claude Code Skills/trabalho/Camilee`, porque o scratchpad é apagado entre os dias.
  - Plano aberto com `escala_mesa` 3,2: no 5 o rosto pequeno fica borrado.
  - `capcut_zoom_podcast.py` agora divide e dá zoom também nos takes com keyframes de X. O `time_offset` desses keyframes é
    o tempo absoluto do bruto; cada metade fica com os dela mais um keyframe interpolado na emenda.
  - Letra solta em legenda ("vitamina D") precisa estar em PROPRIOS, senão o plano_auto a põe em minúscula.
