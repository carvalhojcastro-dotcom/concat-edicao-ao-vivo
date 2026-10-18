---
name: edicao-reels
description: Edita um vídeo bruto de reels (especialista falando para a câmera) do começo ao fim no Concat deste fork, no estilo de EDICAO.md, e entrega um MP4 4K 30 fps. Use quando o pedido for "edita esse vídeo", "edite o C5430", "faça a edição", "parte 1", "legendas dinâmicas", "coloca b-roll", ou ajustes num reel já editado.
---

# Edição de reels: o processo completo

Você é o editor. O usuário só diz algo como **"edita esse vídeo: <arquivo>"**. Você faz tudo e
entrega o MP4 pronto, **sem pedir confirmação no meio**. As regras de estilo estão em `EDICAO.md`
(leia antes da primeira edição da conversa). Este arquivo diz **como** fazer e **como decidir**.

Variáveis (raiz do repositório = `$R`):
- `PY=$R/tools/.venv/bin/python`
- Projeto: `$HOME/Desktop/Concat/<nome>`
- Trabalho: uma pasta temporária sua
- Saída: `$HOME/Desktop/<nome>.mp4`
- `<nome>` é o que o usuário der; senão, o nome do arquivo sem extensão.

## 0. Pré-checagem (rápida, sem perguntar se estiver tudo ok)
- O venv `tools/.venv` existe? Se não, rode `./tools/setup.sh`.
- O Concat está aberto com a API ligada? Teste `$PY tools/reel.py listar <qualquer projeto>` ou um
  `socket` na porta 7420. Se `.concat-token` não existir, peça ao usuário para ligar a API em
  Configurações > API e salvar o token nesse arquivo.
- `fonts/` tem Scholar-Regular.otf, Scholar-Italic.otf e Montserrat-Bold.otf? Se faltar, rode o setup;
  se ainda faltar, avise e siga (o Concat cai na fonte embutida).
- `.env.local` tem uma linha `HF_KEY=`? Confira só que a linha existe (`grep -c '^HF_KEY=.\+:'`),
  **nunca leia, mostre ou peça a chave no chat**. Se não houver, peça ao usuário para rodar
  `./tools/configurar_chave_higgsfield.sh` ou siga sem B-roll se ele preferir.

## 1. Projeto e transcrição
```bash
$PY tools/reel.py novo "$P" "<video>"
$PY tools/reel.py transcrever "<video>" "$W"      # imprime as frases com tempo
```

## 2. Escolher as tomadas (julgamento)
O bruto tem bastidor e repetições: "vamos lá", "ficou ruim", "desculpa", "volta aí", "foi mal",
"pode soltar", conversa com quem filma.
- Monte o texto final do vídeo e, para cada trecho, use a **última tomada completa e limpa**
  (sem tropeço, sem palavra errada).
- Uma tomada que termina em "…, ficou ruim" é descartada inteira.
- Passe os trechos com os tempos do Whisper: início da 1ª palavra e fim da última.
```bash
$PY tools/reel.py cortes "$W" "38.60-58.80,117.16-158.92,193.40-209.58"
```
- Leia o texto impresso.
- Se o início perdeu uma palavra ou o fim pegou uma palavra de outra tomada, ajuste o tempo do
  trecho e rode de novo.
- Corrija erros de transcrição editando `words.json` (ex.: "chaqueca" → "enxaqueca").

## 3. Parte 1
```bash
$PY tools/reel.py aplicar "$P" "$W"                  # cortes + 1.05x + grade de quadros
python3 tools/legendas_simples.py "$P" "$W/words.json" T4   # 92%, offsetY 0.17, contorno + sombra
$PY tools/reel.py nitidez "$P"
$PY tools/reel.py listar "$P"                        # índices e tempos para os planos
```

## 4. Legendas Dinâmicas (julgamento)
Escreva `$W/dinamicas.json` (formato em `tools/planos_exemplo/dinamicas.json`) e rode
`$PY tools/legendas_dinamicas.py "$P" "$W/dinamicas.json"`.
- **Quantidade:** cerca de 20 a 22 blocos por minuto, nas frases importantes.
- **Abertura:** os blocos cobrem **toda a abertura** (as 3 a 5 primeiras frases).
- **Tamanho dos blocos:** de 1 a 6 palavras, com índices **contíguos**; 2 a 3 linhas.
- **Chave:** a palavra mais forte da frase (o substantivo do assunto, o alerta, o número).
  Nunca um artigo.
- **Estilos:** alterne `impacto`, `serifa`, `classico` e `elegante`, nunca o mesmo em blocos seguidos.
  - `classico` e `elegante` ficam melhor com 1 a 2 palavras na linha de cima e a chave embaixo.
  - `serifa` aceita escadinha de 2 a 4 linhas, com a chave numa linha só.
  - `impacto` aceita linha pequena, chave e linha pequena.
- Remova vírgulas do fim só nas palavras-chave (o script já tira as dos blocos).

## 5. Zoom seco (julgamento)
Escreva `$W/zoom.json` (formato em `tools/planos_exemplo/zoom.json`): trechos `[índice da palavra
que começa a frase, escala]`.
- Comece em 1.0 e alterne 1.0 e 1.18; use **1.32 nas frases de impacto** ("Salve este vídeo",
  "Atenção", a conclusão).
- Use de 15 a 18 trocas por minuto.
```bash
cp "$P/concat.json" "$W/ref.json"
python3 tools/zoom_cortes.py "$P" "$W/ref.json" "$W/zoom.json"
$PY tools/centralizar_zoom.py "$P"
```
Se algum trecho sair "limitado pela folga", suba a escala dele (ex.: 1.45) com `setClipTransform`
e rode `centralizar_zoom.py` de novo.

## 6. B-roll (julgamento + custo)
Escreva `$W/broll.json` (formato em `tools/planos_exemplo/broll.json`).
- **Quantidade e escolha:** de 5 a 7 cenas por minuto, em falas concretas que viram imagem (um
  sintoma, um hábito, um órgão, uma situação do dia a dia).
- **1ª cena:** depois de 2 a 3 s de fala ou na passagem da 1ª para a 2ª frase. **Nunca em 0 s.**
- **Tempo de cada cena:** `inicio`/`fim` = tempo da 1ª e da última palavra (saem de `listar`).
  O `broll_animar.py` encaixa nos cortes.
- **Prompts** em inglês, só descrição positiva (o z-image lê negação ao contrário). Sempre:
  pessoas **brasileiras** em cenário brasileiro, roupa do dia a dia; **sem médico ou profissional de
  saúde**; **nada escrito** (nem embalagem com rótulo, tela, laudo, monitor com número).
  Órgãos em 3D funcionam bem.
```bash
$PY tools/broll_higgsfield.py "$W/broll.json" "$P/broll" <cena1>     # 1 de teste
```
- **Olhe a imagem antes de gerar o resto.** Se tiver médico, texto, pessoa não brasileira ou
  quadros divididos, mova para `$P/broll/descartadas/`, reescreva o prompt e gere de novo.
- Depois gere as outras e:
```bash
python3 tools/broll_imagens.py "$P" "$W/broll.json" "$P/broll"
python3 tools/broll_animar.py "$P"
```

## 7. Revisão e entrega
- **Quadros de revisão:** copie `concat.json` para `dist/verificacao/<x>/` e rode
  `python3 tools/quadros.py <copia> <saida.jpg> "<tempos>"`. Use o fim de cada bloco dinâmico e o
  meio de cada B-roll e de cada zoom.
- **Olhe as imagens. Confira:**
  - legenda abaixo do rosto e legível;
  - palavras pequenas retas e chave grande;
  - B-roll certo;
  - zoom com o rosto no centro;
  - o vídeo começa no apresentador.
```bash
python3 tools/exportar.py "$P" "$HOME/Desktop/<nome>.mp4"       # 4K, fps do projeto (30)
$PY tools/reel.py fechar "$P"
```
- **Confira o MP4:** `ffprobe` (2160x3840, 30 fps, com áudio) e 3 ou 4 quadros extraídos dele.

## 8. Relatório ao usuário (curto)
- O que entrou: tomadas escolhidas, número de cortes, blocos dinâmicos, zooms e B-rolls.
- Onde está o arquivo.
- **Custo do Higgsfield:** imagens geradas × preço (z-image US$ 0,015, Soul 2 US$ 0,0057),
  em dólar e em reais.
- O tempo que levou.
- Algo a conferir, se houver.

## Pedidos de ajuste depois da entrega
Edite o projeto (ele fica salvo), reexporte com o mesmo nome e feche na API.
- Se o projeto estiver **aberto na janela do Concat**, as edições pela API aparecem ao vivo, mas a
  exportação é recusada: exporte de uma cópia do `concat.json` em `dist/verificacao/`.
- Ao trocar uma imagem com o projeto aberto na janela, o `addClip` pode "imantar" o clipe para
  outro ponto: confira e corrija com `moveClips`.
- Legendas: para mudar tamanho ou posição, apague todos os clipes de texto e refaça (simples e depois
  dinâmicas) com `--escala=`/`--altura=`/`--centro=`.

## Armadilhas conhecidas
- Use "Helvetica" como família ("Helvetica Neue" o Concat não acha).
- OpenCV precisa ser < 5 (o 5 tirou o detector de rosto).
- `alinhar_quadros.py` não salva sozinho; o `reel.py aplicar` já salva.
- Chave do Higgsfield: nunca no chat, nunca em commit; só via `configurar_chave_higgsfield.sh`.
