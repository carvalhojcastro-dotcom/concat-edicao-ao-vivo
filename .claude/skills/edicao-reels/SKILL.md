---
name: edicao-reels
description: Edita um vídeo bruto de reels (especialista falando para a câmera) do começo ao fim no Concat deste fork ou num projeto do CapCut, no estilo de EDICAO.md, com as legendas padrão (estilo das referências do Instagram, Poppins branca, simples + blocos dinâmicos), e deixa o projeto pronto (MP4 4K 30 fps só quando pedirem a exportação). Use quando o pedido for "edita esse vídeo", "edite o C5430", "faça a edição", "parte 1", "legendas", "legendas dinâmicas", "coloca b-roll", "zoom in e zoom out", "no projeto X do CapCut", ou ajustes num reel já editado.
---

# Edição de reels: o processo completo

Você é o editor. O usuário só diz algo como **"edita esse vídeo: <arquivo>"**. Você faz tudo,
**sem pedir confirmação no meio**, e deixa o projeto pronto para ele abrir no Concat. **Exporte o MP4
só quando o pedido incluir exportar** (ou quando ele pedir depois); exemplos e testes ficam só no
projeto. As regras de estilo estão em `EDICAO.md` (leia antes da primeira edição da conversa), e as
regras de trabalho na seção "Como trabalhar" de lá. Este arquivo diz **como** fazer e **como decidir**.
Cortes de podcast/entrevista seguem outro processo: `tools/cortes_podcast/LEIA-ME.md`.
Vídeo que **já vem cortado** pelo usuário (CAP do CapCut): não corte de novo; siga `EDICAO.md` seção 6b
(cortes lidos do draft do CapCut, 1,10x, zoom nos cortes dele, nitidez 20 sem cor, lofi com
`tools/musica_fundo.py`).
Projeto **no CapCut, já cortado** ("só adicione as legendas e b-rolls ... e os zoom in e zoom out grupais"):
EDICAO.md 6f. Remonte o áudio dos cortes e transcreva (tempos da timeline), e então: zoom por frases com
`tools/capcut_caixinha.py` (plano sem "pergunta"; `"x"` no grupo centra quem fala), B-roll do Higgsfield com
`tools/capcut_broll.py` e legendas com `tools/capcut_legendas_ig.py` (passo 4). CapCut fechado para escrever.

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
- `fonts/` tem Poppins-Medium e Poppins-SemiBold (as das legendas padrão; livres, vêm no repositório)? E
  Coolvetica-Rg, HelveticaNeue-Medium e -CondensedBlack (estilos antigos)? Se faltar, rode o setup.
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
$PY tools/reel.py aplicar "$P" "$W"                  # cortes + 1.10x + grade de quadros
$PY tools/limpar_audio.py "<video>" "$P/midia/<nome>_audio_limpo.mov" --projeto "$P"   # ruído de fundo (DeepFilterNet)
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

## 4. Legendas: simples + blocos dinâmicos no estilo IG (padrão, julgamento)
**Padrão desde 2026-10-29** ("assuma esses novos tipos de legendas como os principais"): o estilo das referências do
Instagram que o usuário mandou, medido quadro a quadro (EDICAO.md 6f; vídeos em `referencias/legenda-*-ig*`).
Sempre **branco**, **Poppins Medium/SemiBold** (sem serifa, sem cursiva, sem rosa), sombra preta suave, sem
contorno, **sem animação** (corte seco; no bloco, cada palavra entra quando é dita), centrado, dentro das margens
de 15% a 85%. A ferramenta faz a legenda simples sozinha (1 a 4 palavras emendadas, com a pontuação, some nas
pausas); você escreve só os blocos em `$W/blocos.json`:
```json
{"blocos": [{"linhas": [[0, 1], [2, 3, 4], [5, 6, 7]], "chave": [7]},
            {"linhas": [[204, 205], [206, 207, 208]], "chave": [208], "fecho": true}]}
```
```bash
# Concat (words.json do reel.py cortes, tempos do bruto; o script leva para a timeline):
$PY tools/capcut_legendas_ig.py --concat="$P" "$W/words.json" "$W/blocos.json"
# CapCut (projeto já cortado por lá; CapCut fechado; words.json com os tempos da TIMELINE, do áudio remontado):
$PY tools/capcut_legendas_ig.py "<pasta do projeto no CapCut>" "$W/words_tl.json" "$W/blocos.json"
```
- **Escolha pelo roteiro:** os blocos vão nas frases e palavras de maior destaque (a ideia central, o dado, o
  alerta, o chamado, o item da lista). Nunca em frase de passagem só para cumprir número.
- **Quantidade:** ~13 blocos por minuto (quem fala rápido pede blocos longos: "estão aparecendo e sumindo muito
  rápido ... não consigo nem ler"). A abertura (gancho) vira bloco.
- **Cada bloco é uma frase inteira** de 2 a 8 palavras, em 2 ou 3 linhas, com índices **contíguos**, terminando
  numa pausa (o bloco completo fica na tela até a próxima palavra).
- **Chave:** a palavra (ou as palavras) mais forte, nunca um artigo; pode dividir a linha com palavras pequenas
  (`[[126], [127, 128, 129]]` com `"chave": [127, 129]` → "o / **suco** de **caixinha**"). `"fecho": true` na frase de
  fecho (chave maior). Vírgula do fim da chave sai sozinha.
- **Linhas:** 1 a 3 palavras curtas cada; o script centra, encolhe o bloco que passaria da margem e desce a linha
  de baixo se uma descendente de cima (g, ç, p) encostar.
- **Roupa ou fundo muito claro:** a sombra suave segura a leitura; se não segurar, `$PY tools/sombra_legenda.py "$P"`
  (degradê escuro atrás das legendas). Roupa com estampa no peito: veja EDICAO.md.
- **Este é o único estilo de legenda.** Os antigos (Helvetica com contorno, impacto/serifa/clássico/elegante, os
  prints "como que / eu faço", entrada "Mini zoom") foram apagados em 2026-10-29 a pedido ("para não ter erro").
- **Estampa no peito:** `--base=<fração>` desce a linha das legendas para baixo da estampa (EDICAO.md seção 6).

## 5. Zoom seco (julgamento)
Só zoom seco. **Não ponha zoom animado (keyframes) nos takes**: foram desfeitos ("não gostei, não faça mais",
2026-10-30). Take que já vier com zoom animado: pergunte antes de manter.

Padrão: `$PY tools/zoom_por_frases.py "$P" --min=1.5 --ideia=2.5` monta os conjuntos pelas legendas
(troca em começo de frase, ou de ideia depois de 2,5 s; divide take contínuo com mais de 4 s num começo
de frase). Para escolher à mão, escreva `$W/zoom.json` (formato em `tools/planos_exemplo/zoom.json`):
trechos `[índice da palavra que começa a frase, escala]`. O zoom só troca num corte que já existe (o
`zoom_cortes.py` dá a escala de cada take pelo trecho onde ele começa); nunca corte uma fala contínua só
para trocar o zoom.
- **Conjuntos que seguem as frases:** cada conjunto é uma frase curta ou duas, ou uma ideia (pergunta,
  dado, exemplo, conclusão), em geral 2 a 4 s; o tamanho varia com a frase, para fazer sentido. Cerca de
  12 a 16 trocas por minuto, sem exagero.
- Alterne aberto (`1.0` no plano) e zoom in (`1.18`); `1.32` só numa frase de impacto ("Salve este vídeo").
- Depois, o `centralizar_zoom.py` enquadra **cada take**: pessoa centralizada, cabeça a ~13% do topo
  (nunca menos de 10%), abertos a 108% (sobra imagem para centralizar). Com estampa no peito,
  `--estampa` impede que ela desça sobre a legenda (limitando o zoom quando precisa); centralizar vem
  antes: pessoa de lado faz o conjunto subir o zoom (até 130%).
```bash
cp "$P/concat.json" "$W/ref.json"
$PY tools/zoom_cortes.py "$P" "$W/ref.json" "$W/zoom.json"
$PY tools/centralizar_zoom.py "$P"            # ou --estampa
```
Ele avisa os takes em que a pessoa ficou de lado por falta de folga; confira esses nos quadros.

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
- **B-roll em motion graphics** (Sabrina e quem pedir motion): sem legenda por cima, conteúdo centrado a ~80%
  (`EDICAO.md` 6e), e **efeitos sonoros em cada elemento que entra**: siga a skill `sfx-motion`.

## 7. Revisão e entrega
- **Quadros de revisão:** `$PY tools/quadros.py "$P" <saida.jpg> "<tempos>"` (usa
  `render_projeto.py`, que renderiza sem deixar cópia de projeto nem card repetido nos recentes do
  Concat). Use o fim de cada bloco dinâmico e o meio de cada B-roll e de cada zoom. **Não crie cópias
  de projeto** para revisar, testar cor ou exportar.
- **Antes de entregar o MP4:** `$PY tools/conferir_video.py "$P" <mp4>` (palavra faltando, sobrando ou
  cortada perto de corte); ouça cada ponto e corrija.
- **Olhe as imagens. Confira:**
  - legenda abaixo do rosto, legível e dentro das margens (15% a 85%);
  - bloco com a chave grande, linhas centradas e juntas, sem palavra encostando;
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
- Legendas: mude `$W/blocos.json` (ou use `--base=`) e rode de novo o `capcut_legendas_ig.py` (no Concat com
  `--concat=`, troca as legendas e deixa a headline; no CapCut, troca as trilhas "Legendas IG").

## Armadilhas conhecidas
- O Concat não lê `.ttc`: as faces da Helvetica Neue (Medium, Condensed Black) são extraídas para
  `fonts/` pelo setup e registradas com nome próprio; a Helvetica comum vai como "Helvetica".
- OpenCV precisa ser < 5 (o 5 tirou o detector de rosto).
- `alinhar_quadros.py` não salva sozinho; o `reel.py aplicar` já salva.
- Chave do Higgsfield: nunca no chat, nunca em commit; só via `configurar_chave_higgsfield.sh`.
