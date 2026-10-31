---
name: sfx-motion
description: Sound design (efeitos sonoros) para motion graphics, B-roll animado e elementos que entram na tela em reels, no estilo aprovado pelo usuário - sutil, profissional, sem clichê, um som por elemento, sincronizado ao quadro - e posto no CapCut como clipes editáveis. Use sempre que o pedido envolver "sound effects", "sfx", "efeitos sonoros", "som nos motions", "sons nas animações", "whoosh", "cliques", "obturador", "deixar o motion com som", ou quando você entregar motions/B-roll animado num vídeo, mesmo que ninguém diga "skill" ou "sound design".
---

# Efeitos sonoros para motion graphics

Aprovado no vídeo 24/11 da Sabrina (2026-10-30), depois de duas rodadas. O pedido foi "de uma forma
profissional, sem esses efeitos clichês e bobos ... cada vez que entra uma nova frase nos motions ... variar
... sobrepor ... diminuir o som deles ... sutil, fluido, dinâmico". Sobre o resultado final, a resposta foi
"tirou onda", com o pedido de guardar o aprendizado e **variar os efeitos nos próximos vídeos**.

Tudo aqui é para servir à fala. Quem assiste não deve "ouvir efeitos"; deve sentir que a tela tem peso e
movimento. Se um som chama atenção para si, ele está alto demais ou é caricato.

## O que funciona (e por quê)

- **Um evento por elemento que entra.** Título, cartão, documento, item de lista, pílula, coluna, risco.
  Cada um soa no quadro em que aparece, e não no começo da cena. O ouvido amarra som e imagem quando eles
  coincidem em ~1 quadro. Os tempos saem do script do motion: o `t0` de cada elemento, que já segue a fala.
- **Camadas, não um som só.** Um evento costuma ter:
  - um **transiente**: tique, meio clique ou obturador;
  - um **corpo**: sopro de ar, papel ou inchaço;
  - um **peso**, só em título grande: o grave sentido.

  Sobrepor dá acabamento. Cada camada sozinha é discreta.
- **Espaço.** O pan acompanha a posição na tela (documento à esquerda soa à esquerda). Algo que desliza da
  esquerda para a direita leva o sopro junto. Isso é o que faz soar "fluido".
- **Tamanho vira afinação sutil, não melodia.** Barra mais alta, clique um pouco mais agudo: 0 a 4 semitons
  num som não tonal.
- **Sem notas.** A nota de vidro "parece teclas de piano tocando ... ficou ruim". Nada com altura musical
  definida: nada de plim, pop, boing ou sininho. O que ela pediu e aprovou no lugar: **cliques, obturador de
  câmera**, motor de foco.
- **Clique de mouse só pela metade.** O "Clique do mouse" inteiro nos zooms foi apagado por ela. O
  `clique("aperta"|"solta")`, curto, seco e variado, funcionou.
- **Saída.** Um sopro curto que desce nos últimos 0,3 s da cena acompanha o motion encolhendo de volta para
  a fala.
- **Nível: abaixo do whoosh dela.**
  - Efeitos ~17-20 dB abaixo da voz: picos de -20 a -27 dBFS e -35 a -42 LUFS momentâneo por cena, com a
    voz por volta de -19 LUFS.
  - O whoosh que ela mesma deixou (Simple Whoosh a 45%) é o teto: dá ~-35 LUFS e pico -14 dBFS.
  - Cada clipe vai a 100% no CapCut, com o nível já no arquivo, para ela ajustar um a um.
- **Respeite o que ela já fez no projeto.**
  - Cena que já abre com whoosh dela não ganha entrada nossa; a que não tem ganha `"entrada"`.
  - Não recoloque cliques de zoom nem música que ela tirou.

## A paleta (`tools/sfx_sintese.py`)

| som | o que é | onde usar |
|---|---|---|
| `ar` | sopro de ruído rosa num passa-banda que varre (`f0`→`f1`), com pan que anda | entrada de cartão, item que desliza, troca, saída |
| `tique` | toque digital curto e ressonante | texto que aparece, checkbox, título pequeno |
| `letras` | um tique por letra (via `rolo`) | lettering letra a letra |
| `grave` | impacto grave com queda de afinação, mais sentido que ouvido | título grande, caixa de destaque, cartão que bate |
| `traco` | caneta riscando, da esquerda para a direita | texto riscado, sublinhado |
| `papel` | folha que desliza e assenta | documento, cartão de papel |
| `sobe` | inchaço de filtro que pousa num som (`pouso`) | coluna, barra ou número que cresce |
| `toc` | batida seca e abafada | algo que encaixa ou pousa |
| `obturador` | disparo de câmera (7 golpes do kit, `n` de 0 a 6) | "captura": documento, voto, coluna que chega ao topo, pílula |
| `clique` | meio clique de mouse, `aperta` ou `solta` | número de cartão, item marcado, pílula, barra |
| `foco` | motor de lente focando, sem os bipes | lupa, zoom de detalhe, "olhar de perto" |

`obturador`, `clique` e `foco` recortam o kit da usuária (`~/Desktop/Edições/Kit de edição/sfx`, fora do Git).
Todos aceitam `semitons`, `pan` e `db_pico`; os sintetizados aceitam `sem` (semente), que muda o grão.

## Variar nos próximos vídeos

Guarde os princípios acima e mude o "timbre" a cada vídeo, para não virar assinatura repetida:
- **Troque a receita por tipo de elemento.** Exemplos:
  - cartão: `ar`+`clique`+`toc` num vídeo, `papel`+`obturador` no outro;
  - checkbox: `tique`+traço curto de `ar`, ou `clique solta`+`toc`;
  - título: `grave`+`letras`, ou `grave`+`tique`+`ar` curto.
- **Gire o que já é variável:**
  - golpe do obturador (`n`);
  - `semitons` (±2);
  - faixas de `f0`/`f1` do `ar` (mais grave = mais "macio", mais agudo = mais "digital");
  - `sem` de todos os sintetizados.
- **Dentro do vídeo**, dois elementos iguais seguidos (cartão 1, 2, 3) mantêm a receita e variam afinação,
  pan e golpe. Assim soam como família, não como repetição.
- **Combinações novas** valem se seguirem as regras: sem tom musical, curtas, no quadro, abaixo do whoosh.
  Se criar um som novo em `sfx_sintese.py`, olhe o espectrograma antes. Seno cortado sem rampa estala
  (`fecha()` resolve).

## Fluxo

1. **Tempos.** No script do motion (ex.: `tools/planos/sabrina_24_motion.py`), anote o `t0` de cada elemento
   (o `prog(t, t0, ...)` em que ele aparece) e onde ele fica na tela. Pegue início e duração de cada cena do
   plano do B-roll.
2. **Mapa.** Escreva `tools/planos/<cliente>_<video>_sfx.json`. O formato está no topo de
   `tools/sfx_motion.py`; o exemplo completo, em `tools/planos_exemplo/sfx_motion.json`. O mapa aprovado da
   Sabrina é `tools/planos/sabrina_24_sfx.json`: use como referência de densidade e nível, não como cópia.
3. **Gerar.** Os WAV vão para a pasta que o CapCut lê:
   ```bash
   tools/.venv/bin/python tools/sfx_motion.py tools/planos/<mapa>.json "$HOME/Movies/CapCut/User Data/SFX Concat/<video>" /tmp/.../plano_sfx.json
   ```
   O relatório dá pico e volume momentâneo por cena. Se passar do alvo, baixe `"ganho_db"`; se ficar abaixo
   de -45 LUFS, suba. Guarde o plano gerado em `tools/planos/<cliente>_<video>_sfx_plano.json`.
4. **CapCut** (fechado; ela permite fechar e reabrir):
   ```bash
   tools/.venv/bin/python tools/capcut_sfx.py "<pasta do projeto>" <plano_sfx.json>
   ```
   Cada evento vira um clipe nas trilhas "SFX motions (Concat) N", e rodar de novo troca essas trilhas.
   Para **trocar só o som** de clipes já postos, mantendo a posição, o volume e o que ela apagou, gere com
   `--sufixo=v2` (nome novo: o CapCut não relê arquivo de mesmo nome) e rode `capcut_sfx.py ... --trocar`.
5. **Conferir.** Antes de escrever, leia o projeto: ela pode ter mexido (compôs as legendas, apagou música,
   moveu whoosh). Depois, reabra o CapCut. O CapCut encaixa os clipes no quadro, e ±1 quadro é normal.
6. **Relatório curto.** Que som entrou em cada cena, em uma linha por cena; o nível em relação à voz e ao
   whoosh; e o que ficou como ela deixou. Diga que não deu para ouvir dentro do CapCut, se for o caso.

## Armadilhas

- O CapCut precisa estar fechado ao escrever, senão ele regrava o projeto por cima.
- Caminho no plano é o "visto pelo CapCut" (`~/Library/Containers/com.lemon.lvoverseas/Data/Movies/...`).
  O arquivo de verdade fica em `~/Movies/CapCut/User Data/SFX Concat/`.
- Não rode `capcut_legendas_ig.py` num projeto em que ela transformou as legendas em clipe composto.
- Só foi testado no CapCut. No Concat ainda não há ferramenta para pôr os eventos.
