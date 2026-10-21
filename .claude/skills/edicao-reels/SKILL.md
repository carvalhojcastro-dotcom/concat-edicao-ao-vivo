---
name: edicao-reels
description: Edita um vídeo bruto de reels (especialista falando para a câmera) do começo ao fim no Concat deste fork, no estilo de EDICAO.md, e deixa o projeto pronto no Concat (MP4 4K 30 fps quando pedirem a exportação). Use quando o pedido for "edita esse vídeo", "edite o C5430", "faça a edição", "parte 1", "legendas dinâmicas", "coloca b-roll", ou ajustes num reel já editado.
---

# Edição de reels: o processo completo

Você é o editor. O usuário só diz algo como **"edita esse vídeo: <arquivo>"**. Você faz tudo,
**sem pedir confirmação no meio**, e deixa o projeto pronto para ele abrir no Concat. **Exporte o MP4
só quando o pedido incluir exportar** (ou quando ele pedir depois); exemplos e testes ficam só no
projeto. As regras de estilo estão em `EDICAO.md` (leia antes da primeira edição da conversa), e as
regras de trabalho na seção "Como trabalhar" de lá. Este arquivo diz **como** fazer e **como decidir**.
Cortes de podcast/entrevista seguem outro processo: `tools/cortes_podcast/LEIA-ME.md`.

Variáveis (raiz do repositório = `$R`):
- `PY=$R/tools/.venv/bin/python` (Mac) ou `PY=$R/tools/.venv/Scripts/python.exe` (Windows). Use `$PY` em
  todos os comandos; no Windows o `python3` é um atalho da Microsoft Store. O Claude Code no Windows roda
  os comandos no Git Bash, então a sintaxe abaixo é a mesma; `tools/plataforma.py` cuida das diferenças
  (transcrição, fontes Arimo/Archivo, codificador). Ver `INSTALAR-WINDOWS.md`.
- Pasta Concat = a pasta-mãe do repositório (`$(dirname $R)`, em geral `~/Desktop/Concat`)
- Projeto: `<pasta Concat>/editados/<nome>`
- Trabalho: uma pasta temporária sua
- Saída (quando exportar): `<pasta Concat>/exportados/<nome>.mp4`
- `<nome>` é o que o usuário der; senão, o nome do arquivo sem extensão.

## 0. Pré-checagem (rápida, sem perguntar se estiver tudo ok)
- O venv `tools/.venv` existe? Se não, rode `./tools/setup.sh`.
- O Concat está aberto com a API ligada? Teste um `socket` na porta 7420. Se `.concat-token` não
  existir, rode `./tools/setup.sh` com o Concat fechado (ele liga a API e grava o token).
- `fonts/` tem Coolvetica-Rg, HelveticaNeue-Medium e -CondensedBlack? Se faltar, rode o setup (a DM
  Serif Display e as outras livres já vêm no repositório).
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
- **Nomes próprios:** nome de pasta ou arquivo não é fonte de grafia. Na dúvida, transcreva de novo
  com outro modelo (medium × large-v3-turbo), ouça as divergências e, se ainda houver dúvida,
  **pergunte ao usuário antes de queimar a legenda** (já saiu "Sibert" no lugar de "Siebert").

## 3. Parte 1
Sem nitidez, cor ou LUT automáticas (pedido de 2026-10-19): só aplique se o usuário pedir.
```bash
$PY tools/reel.py aplicar "$P" "$W"                  # cortes + 1.05x + grade de quadros
$PY tools/legendas_simples.py "$P" "$W/words.json" T4   # 92%, offsetY 0.17, contorno + sombra
$PY tools/reel.py listar "$P"                        # índices e tempos para os planos
```

### Retoque de rosto (sempre em vídeo de mulher)
Se quem fala é mulher, retoque o rosto. Os padrões vêm da predefinição do CapCut do usuário. A
ferramenta processa o bruto em 4K (leva alguns minutos, então rode em segundo plano) e troca a mídia
dos clipes sem mexer em cortes, legendas e zoom:
```bash
$PY tools/retoque.py "<video>" "$W/ret" --quadros "20 45"      # antes/depois em JPG: confira
$PY tools/retoque.py "<video>" "$P/midia/<nome>_retoque.mov" --projeto "$P"
```
Em homem, não aplique sem pedido.

## 4. Legendas Dinâmicas (julgamento)
Escreva `$W/dinamicas.json` (formato em `tools/planos_exemplo/dinamicas.json`) e rode
`$PY tools/legendas_dinamicas.py "$P" "$W/dinamicas.json"`.
- **Escolha pelo roteiro:** os blocos vão **sempre nas frases e palavras de maior destaque** (a ideia
  central, o dado, o alerta, o chamado). Nunca em frase de passagem só para cumprir número.
- **Quantidade (guia, não cota):** cerca de 18 a 22 blocos por minuto, perto de metade das palavras;
  referência aprovada em `editados/Exemplos - legendas dinamicas` (`plano_exemplos.json`).
- **Abertura:** os blocos cobrem **toda a abertura** (as 3 a 5 primeiras frases).
- **Tamanho dos blocos:** de 1 a 6 palavras, com índices **contíguos**; 2 a 3 linhas.
- **Chave:** a palavra mais forte da frase (o substantivo do assunto, o alerta, o número).
  Nunca um artigo.
- **Estilos:** alterne `impacto`, `serifa`, `classico` e `elegante`, nunca o mesmo em blocos seguidos.
  - `classico` e `elegante` ficam melhor com 1 a 2 palavras na linha de cima e a chave embaixo.
  - `serifa` aceita escadinha de 2 a 4 linhas, com a chave numa linha só.
  - `impacto` aceita linha pequena, chave e linha pequena.
- Remova vírgulas do fim só nas palavras-chave (o script já tira as dos blocos).
- A serifada (DM Serif Display) só aparece na palavra-chave; o resto do bloco o script põe em Helvetica/Montserrat.
- **Fonte da chave** (`"fonte_chave"` na frase, serifa e elegante): `serifa` (DM Serif Display reta, padrão),
  `italico`, `bold` (Condensed Black) ou `coolvetica`. Alterne ao longo do vídeo, sem repetir em
  blocos seguidos.
- **Roupa com estampa clara no peito** (ex.: camiseta com logo): legenda branca some em cima dela.
  Zoom em 100% e legenda abaixo da estampa; sobre B-roll claro use `sombra_suave`, nunca contorno
  grosso. Detalhes em `EDICAO.md`.

## 5. Zoom seco (julgamento)
Escreva `$W/zoom.json` (formato em `tools/planos_exemplo/zoom.json`): trechos `[índice da palavra
que começa a frase, escala]`.
- Comece em 1.0 e alterne 1.0 e 1.18; use **1.32 nas frases de impacto** ("Salve este vídeo",
  "Atenção", a conclusão).
- Use de 15 a 18 trocas por minuto.
```bash
cp "$P/concat.json" "$W/ref.json"
$PY tools/zoom_cortes.py "$P" "$W/ref.json" "$W/zoom.json"
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
- **Nem profissionais da área de quem fala** (médico para médico, contador ou consultor para
  contabilidade). Em cena de objeto, escreva "nobody around", senão o modelo põe gente.
```bash
$PY tools/broll_higgsfield.py "$W/broll.json" "$P/broll" <cena1>     # 1 de teste
```
- **Olhe a imagem antes de gerar o resto.** Se tiver médico, texto, pessoa não brasileira ou
  quadros divididos, mova para `$P/broll/descartadas/`, reescreva o prompt e gere de novo.
- Depois gere as outras e:
```bash
$PY tools/broll_imagens.py "$P" "$W/broll.json" "$P/broll"
$PY tools/broll_animar.py "$P"
```

## 7. Revisão e entrega
- **Quadros de revisão:** `$PY tools/quadros.py "$P" <saida.jpg> "<tempos>"` (usa
  `render_projeto.py`, que renderiza sem deixar cópia de projeto nem card repetido nos recentes do
  Concat). Use o fim de cada bloco dinâmico e o meio de cada B-roll e de cada zoom. **Não crie cópias
  de projeto** para revisar, testar cor ou exportar.
- **Olhe as imagens. Confira:**
  - legenda abaixo do rosto e legível;
  - palavras pequenas retas e chave grande;
  - B-roll certo;
  - zoom com o rosto no centro;
  - o vídeo começa no apresentador.
- **Feche na API** (`$PY tools/reel.py fechar "$P"`), senão o projeto não abre na janela do Concat.
- **Exportar só se pedirem:**
```bash
$PY tools/exportar.py "$P" "<pasta Concat>/exportados/<nome>.mp4"   # 4K, fps do projeto, SDR
```
  Com o projeto aberto na janela, use `tools/exportar_seguro.py` (mesmos argumentos).
  **Confira o MP4:** `ffprobe` (2160x3840, 30 fps, bt709, com áudio) e 3 ou 4 quadros dele.

## 8. Relatório ao usuário (curto)
- O que entrou: tomadas escolhidas, número de cortes, blocos dinâmicos, zooms e B-rolls.
- O texto completo das legendas e o que foi conferido (nomes próprios).
- Onde está o projeto (e o MP4, se exportou).
- **Custo do Higgsfield:** imagens geradas × preço (z-image US$ 0,015, Soul 2 US$ 0,0057),
  em dólar e em reais.
- O tempo que levou.
- Algo a conferir, se houver.

## Pedidos de ajuste depois da entrega
Edite o projeto (ele fica salvo), reexporte com o mesmo nome se já havia MP4, e feche na API.
- **Mexa só no vídeo que o usuário apontou**; não refaça os outros por iniciativa própria.
- Os tempos que ele passa são `mm:ss:quadros`.
- Se o projeto estiver **aberto na janela do Concat**, as edições pela API aparecem ao vivo, mas a
  exportação direta é recusada: use `tools/exportar_seguro.py`.
- Ao trocar uma imagem com o projeto aberto na janela, o `addClip` pode "imantar" o clipe para
  outro ponto: confira e corrija com `moveClips`.
- Legendas: para mudar tamanho ou posição, apague todos os clipes de texto e refaça (simples e depois
  dinâmicas) com `--escala=`/`--altura=`/`--centro=`.

## Armadilhas conhecidas
- O Concat não lê `.ttc`: as faces da Helvetica Neue (Medium, Condensed Black) são extraídas para
  `fonts/` pelo setup e registradas com nome próprio; a Helvetica comum vai como "Helvetica".
- OpenCV precisa ser < 5 (o 5 tirou o detector de rosto).
- `alinhar_quadros.py` não salva sozinho; o `reel.py aplicar` já salva.
- Chave do Higgsfield: nunca no chat, nunca em commit; só via `configurar_chave_higgsfield.sh`.
