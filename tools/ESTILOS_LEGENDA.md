# Estilos de legenda (pacote de 2026-10-19)

Reproduz no Concat três referências que o usuário mandou:

| Referência | O que virou |
|---|---|
| Reel DeaL7FgRV4C (e DdsIOERNQNo): frases montadas palavra por palavra, em degraus | presets de composição `linha`, `grande`, `escada`, `sanduiche`, `numero`, `dupla`, `quatro`, `chave` em **Plus Jakarta Sans** |
| Vitrine Vimeo 1189819698: 24 animações em Poppins Black | 24 animações de entrada (lista abaixo) |
| Imagens "MODELOS PRONTOS", "PADRÃO com DINAMISMO", "CHAMATIVOS com ESTILO", "elegantes que IMPRESSIONAM" | modelos `modelo:modelos`, `modelo:padrao`, `modelo:chamativos`, `modelo:elegantes` |

**Regra do usuário:** a cursiva fina rosa do reel **não** entra. O destaque usa **Scholar Itálico branco** por padrão (pedido de 2026-10-20); amarelo (#f4c430) só se pedirem.

## Arquivos

- `estilos_legenda.py`: a biblioteca (fontes, medidas, composições, animações, PNG e vídeo com alfa).
- `legendas_estilos.py`: aplica um plano num projeto, sincronizado com as palavras do Whisper.
- `catalogo_estilos.py`: monta o projeto **Desktop/Concat/editados/Catálogo de legendas**, com todos os estilos em sequência:
  - reel: 0–22 s;
  - modelos: 22–35 s;
  - vitrine: 35–95 s.
- `folha_animacao.py`: folha de conferência com quadros de cada animação em vários instantes.
- Fontes em `../fonts`:
  - Poppins (Medium até Black, com itálicos);
  - Plus Jakarta Sans (Medium até ExtraBold);
  - Playfair Display (Bold, Black, SemiBold Italic, ExtraBold Italic).

  Todas são OFL e as licenças estão na pasta.

## Uso num projeto

```bash
tools/.venv/bin/python tools/legendas_estilos.py "<projeto>" words.json plano.json [--seco]
```

`words.json` vem do Whisper, já corrigido, em tempos da timeline. `plano.json`:

```json
{"destaque": "#ffffff", "frases": [
  {"preset": "escada",    "linhas": ["A regra da", "ovelha", "negra{#22305e}"], "de": 12, "anim": "pop"},
  {"preset": "numero",    "linhas": ["até", "*60%*", "que os seus mais^m", "competidores"], "de": 20},
  {"preset": "modelo:padrao", "linhas": [["Quebre", "o"], ["PADRÃO"], ["com", "DINAMISMO"]], "de": 30, "anim": "blurup"},
  {"preset": "grande", "familia": "pop", "linhas": ["gratidão"], "de": 37, "anim": "ouro"}
]}
```

**Campos de cada frase:**
- `de`: índice da 1ª palavra falada. Cada palavra das linhas entra no tempo da palavra falada correspondente, então o número de palavras precisa bater. `--seco` mostra o texto falado ao lado para conferir.
- Sem `de`, use `inicio` (em segundos) e as palavras entram a cada 0,3 s.
- `familia: "pop"`: troca a Plus Jakarta pela Poppins, para frases no estilo da vitrine.
- `centro: [x, y]`: posição do bloco em frações do quadro. O padrão é 0,5 × 0,6, abaixo do rosto.

**Marcação no texto:**
- `*palavra*`: destaque em Scholar Itálico grande, sobreposto.
- `palavra{#hex}`: cor própria. Palavras escuras ganham um halo claro sozinhas.
- `palavra^g`: tamanho próprio dentro da linha (`p`, `m`, `g`, `gg`).

**Tamanhos** (fração da altura): `p` 0,030 · `m` 0,042 · `g` 0,062 · `gg` 0,080 · script 0,115.

## Animações (`anim`)

**Reel:**
- `pop`: a palavra aparece em cerca de 3 quadros, com um leve zoom. É o padrão das composições do reel.

**Vitrine:**

| Nome | Efeito |
|---|---|
| `abaixo` / `acima` | desce ou sobe até o lugar |
| `direita` / `esquerda` | desliza com leve blur |
| `blur` | sai do desfoque para o nítido |
| `blurup` | desfoque + sobe |
| `zoomout` | o bloco encolhe até o tamanho final |
| `slide` | entra da esquerda com rastro (motion blur); usar em itálico |
| `palavra` | uma palavra por vez |
| `fadein` | letra a letra |
| `surgir` | letras sobem desfocadas |
| `reveal` | letras sobem uma a uma |
| `girando` | letras giram e se ajeitam |
| `flicker` | pisca |
| `flicking` | contorno vazado e letras acendendo em ordem aleatória |
| `maquina` | digitação |
| `riscado` | digita e risca em vermelho |
| `destacado` | placa azul atrás |
| `sublinhado` | linha amarela que se desenha |
| `moderno` | letras pulando com relevo cinza |
| `cinematic` | letras espaçadas e desfocadas se juntam em cerca de 2,6 s |
| `corte` | a palavra é fatiada e as metades param tortas (PNG) |
| `ouro` / `prata` | metal com clarão e reflexo (vídeo ProRes 4444 com alfa + PNG) |
| `brilho` | roxo com halo e reflexo passando |

## Como é feito (limites do Concat 0.2.7, testados)

- **Texto nativo editável sempre que dá.** Fica em PNG ou vídeo com alfa só o que o Concat não desenha:
  - degradê;
  - dourado e prata;
  - faixa de luz dentro das letras;
  - palavra fatiada;
  - retângulos (placa, sublinhado, risco).
- **Keyframe** existe em `offsetX`, `offsetY`, `scale`, `rotation` e `opacity`, e nos parâmetros dos efeitos (`setEffectKey`). Assim o blur (`concat.gaussian-blur` radius) e o rastro (`concat.motion-blur` length) são animados de verdade.
- **Escala e rotação** giram em volta da própria palavra. Vêm de `setClipTransform`, não de `updateClip`.
- **Coisas que não funcionam em títulos:** `crop` e `stretchX/Y`. Por isso retângulos e metades de palavra viram PNG.
- **Glow:** o efeito `concat.glow` é fraco sobre texto. O halo é uma cópia da palavra com Gaussian Blur por baixo.
- **Imagem ou vídeo** entra encaixado no quadro a escala 1. A escala certa é calculada pelo tamanho do PNG.
- **Keys em offset:** a base fica 0 e as keys são absolutas, porque o 0.2.7 soma a base com as keys nos títulos.
- **Trabalho gerado:** os PNG e MOV ficam em `<projeto>/estilos/`.
