# Estilo de edição de reels: o padrão deste fork

Guia do estilo de edição montado e aprovado vídeo a vídeo, para reels verticais de um especialista
falando para a câmera (talking head). Ele vai do **bruto da câmera** ao **MP4 4K 30 fps pronto**,
usando o Concat deste fork pela API (porta 7420) e as ferramentas de `tools/`.

> Com o Claude Code aberto nesta pasta, a skill `.claude/skills/edicao-reels` faz todo o
> processo sozinha: "edite o C5430 dos Downloads e salve como 10 - Título".

---

## O resultado, em uma frase
O vídeo começa no apresentador já falando, sem pausas nem tomadas ruins, a 1.10x. Tem legenda
simples curta e blocos de destaque no estilo das referências do Instagram (Poppins branca, seção 2), zoom seco
centralizado por frase e B-rolls de imagem gerados por IA que entram e saem nos cortes com
movimento lento. A exportação é em 4K a 30 fps.

---

## 1. Parte 1: o básico
| Item | Padrão |
|---|---|
| **Tomadas** | Fica sempre a última tomada completa e limpa de cada trecho. Saem bastidor e falas de produção ("ficou ruim", "desculpa", "vamos de novo", "pode soltar"). |
| **Bordas dos trechos** | Começa e termina na 1ª e na última batida de voz acima de -30 dB, com 0,06 s de folga; **o fim vai pelo menos 0,12 s além do fim da última palavra** (fim de frase é falado baixo e era cortado: "peso", "uso", 2026-10-21). O Whisper marca a 1ª palavra até 0,7 s cedo, então não confie nele para a borda. |
| **Pausas** | Corta toda pausa ≥0,2 s, **respirações incluídas**: RMS em janelas de 25 ms, abaixo de -36 dB por ≥0,15 s, deixando 0,05 s de respiro de cada lado. |
| **Ruído de fundo** | `tools/limpar_audio.py <bruto> <projeto>/midia/<nome>_audio_limpo.mov --projeto <projeto>` (DeepFilterNet, teto 24 dB): limpa o chiado sem abafar a voz e troca a mídia dos clipes (vídeo só copiado). **Não use o Noise Reduction do Concat** (afftdn: abafa e deixa metálico). Pedido de 2026-10-21. |
| **Áudio para redes** | Quando pedirem volume "padrão de rede social": áudio já limpo pelo `limpar_audio.py` + efeito `user.voz-redes-sociais` (compressor leve, ganho, limitador; pasta `efeitos/`, o setup instala) com ganho calibrado para ~-14 LUFS e pico ≤ -1 dB, volume do clipe 1,0. No Ozempic (áudio limpo): 14,2 dB → -14,0 LUFS, pico -1,4 dB. |
| **Velocidade** | **1.10x** em todos os clipes (padrão desde 2026-10-21; antes 1.05x), sem folgas, alinhados à grade de quadros (`alinhar_quadros.py`). |
| **Legendas** | Seção 2: Poppins branca, legenda simples de 1 a 4 palavras + blocos dinâmicos, sem animação (`capcut_legendas_ig.py`). |
| **Texto da legenda** | Maiúscula só no início de frase; a pontuação fica. Corrija erros do Whisper e junte palavras partidas ("sente" + "-se"). |
| **Nitidez e cor** | **Não aplicar automaticamente** (pedido de 2026-10-19). Só quando pedirem: camada `concat.adjust` em T3 (nitidez antiga: `sharpen` 20.23). |
| **Retoque de rosto** | **Sempre em vídeo de mulher.** `tools/retoque.py` copia a predefinição do CapCut: remover rugas 13, uniforme 12, linhas do sorriso 93, olheiras 17 e maquiagem "Naturais" 56. Gera uma cópia retocada do bruto e troca a mídia no projeto (`--projeto`). |
| **Cor** | Nenhuma correção, até haver uma LUT definida para o cliente. |

## 2. Legendas: simples + blocos dinâmicos (estilo das referências do Instagram)
Pedido: "a partir de agora" a legenda simples é a do 1º vídeo de referência e as dinâmicas as dos outros dois, "sempre
bold ou semi-bold, sem serifa, sempre em branco" (nada de cursiva, serifada ou rosa). Medido quadro a quadro (fonte por
sobreposição contra 220 candidatas; tamanho, espaçamento e linha de base por ajuste nos quadros):
| | simples | bloco dinâmico |
|---|---|---|
| fonte | Poppins Medium | Poppins SemiBold (pequenas e chave) |
| em (altura do quadro) | 2,71% | pequenas 4,4%, chave 7,6%, fecho 9,7% |
| espaço entre letras | -0,065 em | -0,07 / -0,06 em |
| entrelinha | — | topo das minúsculas de baixo 0,2 em (da linha de cima) abaixo da base de cima |
| posição | centrada, base a 63,9% | centrado, a linha da chave na base da simples |
| animação | nenhuma (corte seco, emendada) | nenhuma; palavra por palavra quando é dita |
Sombra preta suave, sem contorno. Simples de 1 a 4 palavras (até ~40% da largura), mantém a pontuação, some nas pausas.
Blocos: ~13 por minuto, frase inteira de 2 a 8 palavras em 2 ou 3 linhas; descendente de cima (g, ç) empurra a linha
de baixo. Ferramenta: `tools/capcut_legendas_ig.py <pasta CapCut> <words.json> <plano.json>` (direto no CapCut, palavras
com tempos da timeline) ou `tools/capcut_legendas_ig.py --concat=<projeto> <words.json> <plano.json>` (no Concat, com o
words.json do `reel.py cortes`, tempos do bruto). As duas saídas foram conferidas contra a mesma prévia: caixas
iguais a 1-2 px. `--base=` sobe ou desce a linha das legendas (padrão 0,639). Os estilos antigos (Helvetica com
contorno, impacto/serifa/clássico/elegante, os prints) foram apagados em 2026-10-29 ("para não ter erro").
- **Poppins no Concat:** o Concat junta as Poppins pela família interna ("Poppins") e escolhe pelo peso (SemiBold
  pedida a 500 saía Medium; a 600, negrito sintético 8% mais largo). A ferramenta registra cópias renomeadas
  (`dist/fontes_concat/*-IG.ttf`, família própria de uma face só, peso 400): aí o Concat desenha o arquivo certo
  no tamanho certo.
- **Tamanho no CapCut** (medido no export do "11 - Caixinha"): o CapCut faz a altura typo da fonte (OS/2 ascendente -
  descendente) = tamanho x 0,0032 da altura do quadro e centra essa caixa na posição (erro medido ~2%).
- **Projeto já cortado** ("só adicione as legendas e b-rolls ... e os zoom in e zoom out grupais"): zoom por frases com
  `capcut_caixinha.py` (sem "pergunta" no plano; `"x"` no grupo centra quem fala), B-roll do Higgsfield com
  `capcut_broll.py` (fotos com as entradas nativas que ela escolheu no "13 - Bioestimulador": "Diminuir zoom" e
  "Slide lateral", e o avanço lento 100% -> 108%), legendas com `capcut_legendas_ig.py`.


## 3. Zoom seco (punch-in)
- **A pessoa sempre centralizada e com margem no topo** (pedido de 2026-10-21): enquadre cada take,
  inclusive os abertos (por isso o aberto é 108%, não 100%: sobra imagem para centralizar). O centro é a
  média de rosto e peito; a cabeça fica a ~13% do topo em todos os takes, para a margem não pular.
  Quem decide é o enquadramento, não um "enquadramento fixo por trecho".
- **Conjuntos que seguem as frases:** cada conjunto de zoom é uma frase curta ou duas, ou uma ideia (1,5 a 4 s,
  variando com a frase), ~12 a 16 trocas por minuto; troca só em corte que já existe, e take de fala contínua
  com mais de 4 s é dividido num começo de frase. `tools/zoom_por_frases.py` monta os conjuntos pelas
  legendas (`--min=1.5 --ideia=2.5` deu o ritmo do Ozempic) e `tools/centralizar_zoom.py` faz o
  enquadramento take a take (`--estampa` com estampa no peito).
- **Centralizar:** pessoa a mais de 3% do centro faz o conjunto ganhar o zoom que dá folga (até 130%),
  **mas a estampa vence**: a legenda nunca fica em cima dela (pedido de 2026-10-23); para isso a cabeça
  pode subir até 6% do topo.
- **Sem animação.** O enquadramento muda no começo das frases: aberto (108% depois de centralizar), 118%
  e **132% nas frases de impacto** (como "Salve este vídeo").
- Se o rosto ficar fora do centro por falta de folga, suba a escala do trecho (ex.: 145%).

## 4. B-roll de imagem (Higgsfield)
- **Tempo:**
  - **O vídeo sempre começa com o apresentador falando.** O 1º B-roll é o gancho visual: entra
    **depois de 2 a 3 s de fala ou na passagem da 1ª para a 2ª frase**.
  - Toda imagem **entra no início de um corte e sai no fim de um corte**, nunca no meio de um take.
  - Toda imagem tem **movimento lento** (aproxima, afasta ou desliza), alternado entre elas.
- **Quantidade:** de 5 a 7 por vídeo de ~1 min. Gere **1 de teste**, confira e só depois o resto.
- **Conteúdo:**
  - **Nunca mostrar médico, enfermeiro ou profissional de saúde**, porque o especialista é quem fala.
  - **Nunca ter nada escrito:** letras, números, rótulos, telas, laudos.
  - **Pessoas brasileiras**, em cenário brasileiro.
  - **Nem outros profissionais da área de quem fala** (médico para médico, contador ou consultor
    para contabilidade).
  - **Cena de objeto:** escreva "nobody around" no prompt, senão o modelo põe gente.
- **Conta:** a API do Higgsfield com saldo pré-pago (a assinatura não compensa). Sem variações:
  de 5 a 7 imagens por vídeo de ~1 min.
- **Modelos:**
  - `z-image/turbo`: US$ 0,015/imagem, 2K 9:16, o padrão. Ele **lê negação ao contrário**
    ("no doctors" coloca médicos), então descreva só o que deve aparecer.
  - `higgsfield-ai/soul/v2/standard`: US$ 0,0057 em 1080p, o mais barato. Às vezes divide a imagem
    em quadros em cenas de pessoa deitada; resolva com close no rosto.

## 5. Entrega
- O projeto fica pronto em `editados/<nome>`. **Exporte só quando pedirem** (o usuário prefere ver no
  Concat e muitas vezes exporta ele mesmo).
- Exportação: **4K 2160×3840 a 30 fps, SDR** (Dr. Leonardo: **2K 1440×2560**, `exportar_seguro.py <P> <mp4> 1440 2560`) (`hdr=False`; vídeo de iPhone é HLG e em HDR legenda e
  B-roll ficavam cinza). Crie o projeto já em 30 fps.
- **Confira o MP4 antes de entregar** (pedido de 2026-10-21: "sempre confira ... para garantir que não fez
  cortes errados"): `tools/conferir_video.py <P> <mp4>` transcreve o MP4, compara com as legendas e aponta
  palavra faltando, sobrando ou pouco clara perto de corte. Ouça cada ponto e corrija antes de entregar.
- Confira quadros do MP4 final: legendas, B-rolls, zoom, início e fim.
- Feche o projeto na API (`project.close` com save), senão ele não abre na janela do Concat.

## 6. Legenda sobre roupa com estampa ou clara
Na camiseta com estampa clara no peito (ex.: "SIMPLES MEDICINA" do Dr. Leonardo), a legenda branca some. Antes
de legendar, olhe a roupa:
- **Estampa no peito:** `centralizar_zoom.py <projeto> --estampa` (cabeça ≥ 10% do topo, estampa ≤ 0,745) e a
  legenda abaixo da estampa, na parte escura, com `capcut_legendas_ig.py ... --base=<fração>` (a linha das
  legendas; padrão 0,639). Confira todas as frases numa folha de quadros antes de entregar.
- **Roupa clara** (camiseta branca/creme): a sombra suave das legendas costuma segurar; se não segurar,
  `tools/sombra_legenda.py <projeto>` põe um degradê escuro (PNG numa trilha entre o vídeo e as legendas,
  ~70% de 0,70 até 0,80 da altura e até a base), sem mudar o estilo. Nada de contorno grosso ("não use traços
  tão fortes").

## 6b. Vídeo que já vem cortado (CAP do CapCut)
O usuário às vezes manda os cortes prontos ("CAP ...", exportados do CapCut) e pede o resto (2026-10-23):
- **Não corte de novo.** O CAP entra inteiro a 1,10x e é dividido nos cortes dele, para o zoom trocar
  exatamente ali. Os cortes vêm do projeto do CapCut (`~/Movies/CapCut/User Data/Projects/
  com.lveditor.draft/<nome>/draft_info.json`, início de cada segmento da trilha de vídeo; um draft pode
  ter dado dois CAPs). Sem o draft: `tools/achar_cortes.py <cap> --bruto=<original>` (acha pelo áudio).
- **Sem cor nem exposição:** o CAP já sai do CapCut em SDR; só **nitidez 20** (`concat.adjust`
  sharpen 20,23 em cada take).
- Áudio limpo (`limpar_audio.py`) + `user.voz-redes-sociais` calibrado, legendas simples e dinâmicas,
  sombra em roupa clara, zoom com `zoom_por_frases.py --corte=2.5 --cortes=<cortes do usuário>` (troca em
  qualquer corte dele depois de 2,5 s; ~14 trocas por minuto) e `centralizar_zoom.py --estampa`.
- **Lofi baixinho:** `tools/musica_fundo.py <P> <musica>` (17 dB abaixo da voz, fades de 1,7/2,4 s), **uma
  música diferente em cada vídeo** (pedido de 2026-10-23). As do CapCut do usuário ficam com nome em
  `Edições/Kit de edição/musica/CapCut/` (ele escolheu usá-las; a licença delas é a do CapCut); a
  "Chillhop Jazz Coffee Shop" (Pixabay) é livre para redes.
- **Zoom in em close** (pedido de 2026-10-23: "dar mais zoom nos zoom ins"): `centralizar_zoom.py
  --estampa --fechado` leva o conjunto de zoom in a até 170%, com a estampa inteira abaixo das legendas;
  se nem assim couber, o zoom in fica no limite da estampa.
- **Versão com headline** (V2): `tools/headline.py <P> "linha 1|linha 2"`: caixa branca, letra preta
  (Helvetica Bold, tamanho 0,038), no peito, um pouco abaixo do meio (`--altura=0.02`, entre o queixo e a estampa), **só na abertura** (até o fim do 1º conjunto aberto, 2 a 5 s, para
  não cobrir o rosto no close), entrando de baixo para cima. O hook é a pergunta ou promessa do vídeo, em
  2 linhas curtas ("Parou o Ozempic, / engorda de novo?").
- Entrega do Dr. Leonardo: 2K em `Edições/Dr Leonardo/Editados Prontos/`.

## 6c. Cortes de palestra (câmera de mão, plano aberto)
Pedido de 2026-10-25 (Dr. Leonardo, "Cortes palestra"):
- **Legenda do SRT do usuário** (palavra por palavra, do CapCut, já revisado): o texto é o do SRT; o Whisper
  só confere. Ordene por tempo, tire entrada repetida (frase inteira que repete palavras já marcadas) e
  aspas. **Não acrescente palavra**; só troque a que os dois modelos ouvem diferente ("se ele for" → "se eu for").
- CAP exportado **com legenda queimada**: refaça o corte a partir do bruto pelos trechos do draft do CapCut
  (`cortar_ao_vivo.py` com o que fica fora deles). O bruto do iPhone é HLG: `concat.exposure -1,55` iguala ao CAP.
- **Zoom grande e sempre centralizado:** `zoom_por_frases.py --zoom=1.6` e `centralizar_zoom.py --corpo
  --seguir --topo=0.24 --topo-min=0.22`. `--corpo` acha a pessoa pela silhueta (o rosto pequeno some no
  plano aberto); `--seguir` põe keyframes no offsetX para acompanhar a câmera que anda dentro do take.
- **Headline acima da cabeça** (fundo branco, letra preta, tamanho 0,030, o vídeo todo; o usuário pediu "um pouco menor e um pouco mais pra baixo" sem tapar a cabeça):
  `headline.py <P> "l1|l2" --altura=-0.1825 --tamanho=0.030 --fim=<duração>` (caixa entre 9% e 18% da altura;
  a cabeça fica a 24%). Legendas um pouco mais baixas: `capcut_legendas_ig.py ... --base=0.66`.

## 6d. Legendas dentro de um projeto do CapCut
Pedido de 2026-10-26 ("faça dentro do CapCut ... deixe tudo editável"): o projeto fica no CapCut e as legendas
entram nele como textos normais, no estilo da seção 2.
1. Ache o projeto pelo nome em `com.lveditor.draft/root_meta_info.json` (a pasta pode ter outro nome; o nome pode
   vir com acento decomposto, compare normalizado).
2. Remonte o áudio da trilha principal pelos segmentos do `draft_info.json` (fonte, velocidade) e transcreva com
   dois modelos: os tempos já são os da timeline.
3. Escreva os blocos (seção 2) e, com o CapCut **fechado**, rode `tools/capcut_legendas_ig.py <pasta do projeto>
   <words.json> <blocos.json>`: backup em `~/Desktop/Concat/backup-capcut/`, fontes copiadas para
   `~/Movies/CapCut/User Data/Fontes Concat/` (a única pasta fora do sistema que o CapCut da App Store lê), textos
   em trilhas "Legendas IG". Rodar de novo troca as legendas. Prévia de como o CapCut desenha: `desenhar()` do
   mesmo script.
4. Reabra o CapCut e confira o nome do projeto na lista: na primeira abertura depois da escrita ele pode voltar
   ao nome da pasta ("60 - Cirurgia 25.02.26" virou "1028 (1)", 2026-10-28). Se voltar, feche o CapCut e grave o
   nome em `draft_name` no `draft_meta_info.json` da pasta e no `root_meta_info.json`; aí ele fica. Nome com mais
   de 50 caracteres o CapCut corta (volta ao da pasta): é limite dele, não insista.
- **Margens** (linhas-guia do usuário, 2026-10-29): tudo entre 15% e 85% da largura (o script encolhe o bloco que
  passaria).
- **Caixinha de perguntas + zoom por frases** (série "Caixinha de perguntas" do Dr. Rafael, 2026-10-29):
  `tools/capcut_caixinha.py <pasta no CapCut> <plano.json>` põe a figurinha de pergunta do Instagram (foto dele, a
  pergunta que ele lê no começo) acima da cabeça o vídeo todo e troca o zoom por grupos de cortes que começam e
  terminam com uma frase (in 1,4 / out = o enquadramento dela, alternando). O X acompanha a escala (o centro que
  ela escolheu fica no centro); no zoom in o Y desce para a cabeça não encostar na caixinha. Nada de corte novo.

## 6e. Editar do zero no CapCut, no jeito da usuária
Pedido de 2026-10-27 ("aprenda com a edição do primeiro e replique no segundo ... me entregue pronto e
editável no CapCut"). Medido no projeto que ela editou ("5 - Braços definidos"):
- **Cortes:** 0,04 s de ar antes da voz e 0,06 s depois; pausas tiradas (o `reel.py cortes` dá isso; tire
  0,025 s do começo de cada pedaço). Fala a **1,1x**, voz a 155%, redução de ruído 85% e retoque de rosto.
- **Zoom** muda com a ideia: abertos 100-110%, zoom in 130-150% com o rosto a ~30% da altura, centrado.
- **Sem zoom animado (keyframes) nos takes:** os zooms com a curva "Desaceleração na saída" foram todos desfeitos
  ("desfaça isso por favor, não gostei, não faça mais", 2026-10-30). Só zoom seco por conjuntos. Se um take já
  vier com zoom animado, não presuma que é dela: pergunte antes de manter.
- **Música** lofi a 0,19 com fade de 0,8 s / 3 s; **efeitos** dos Favoritos dela (Clique do mouse, Simple
  Whoosh a 48%, Autofoco Sony) na entrada e na troca de B-roll.
- **B-roll:** fotos realistas na trilha de cima, com o Fade-in dela e avanço lento de zoom (100→108%).
- **Confira a fala cortada** (`conferir_video.py` no áudio remontado): a transcrição longa esconde começos
  falsos ("Ele estimula o próprio..." → "vamos lá" → a tomada boa).
Ferramenta: `tools/capcut_montar.py <projeto novo> <projeto modelo> <plano.json>` (pedaços, zoom, música,
efeitos, B-roll) e depois `capcut_legendas_ig.py`. Fotos e fontes em `~/Movies/CapCut/User Data/` (sandbox).
- **Bruto direto para projetos no CapCut** ("abra cada um desses vídeos em um projeto no CapCut, faça os cortes,
  acelere em 1.05x e adicione as novas legendas", 2026-10-29): `reel.py transcrever` + `reel.py cortes` (tomadas),
  `capcut_novo.py` (modelo da mesma cliente e do mesmo cenário) e `capcut_montar.py` só com `pedacos`,
  `"velocidade"` e `"volume"` (ganho para ~-14 LUFS; pedaço com `"volume"` próprio, ex.: pergunta de quem filma 7 dB
  mais alta), depois `capcut_legendas_ig.py`. Confira a fala cortada transcrevendo o corte de novo.
- **Escala uniforme no JSON do CapCut:** `uniform_scale.value` é a proporção x/y que a trava mantém (1,0 em todos os
  clipes feitos por ela), não o zoom; o zoom fica só em `clip.scale`. Com o zoom ali, a imagem aparecia certa, mas
  ao mudar o tamanho no CapCut ficava achatada (y = x / value; "a imagem fica achatada. isso é errado", 2026-10-30).
- **Sem projeto no CapCut** ("abra no CapCut", 2026-10-28): `tools/capcut_novo.py <projeto modelo> "<nome>" <bruto>`
  põe o bruto na pasta do CapCut por link físico (caminho escrito por nós fora dela vira "arquivo não
  acessível" no sandbox) e clona um projeto da mesma cliente (fica o que vale para o vídeo todo: ajustes de cor, LUT, sombra atrás das
  legendas; sai o conteúdo) e registra na lista do CapCut. Sabrina: modelo "19 - O ente atrasou o repasse"
  (1,02x, retoque, zoom 1,1/1,3/1,5). Pedaços com zoom por frase e rosto centrado: `tools/capcut_pedacos.py`;
  folha de revisão sem abrir o CapCut (zoom, motions e legendas): `tools/capcut_previa.py`. A pasta do vídeo em
  Edições › Sabrina Reinbold leva o **nome da pasta do Drive** do card (ex.: "3 - Por que um RPPS pode ter…", 2026-10-31).
  No 24/11 ela tirou a música e os cliques de zoom e pôs o whoosh do modelo (45%) na entrada de cada motion;
  o 01/12 saiu assim: sem música, sem clique, whoosh na entrada dos motions (`"efeitos"` no início de cada B-roll).
  Se ela pedir música, a Lofi vai a 0,16 (`"musica": {"volume": 0.157}`; no 13 ela baixou de 0,39 para isso).
- **B-roll em motion graphics** (Sabrina, 2026-10-28: "animações motions sobre o que ela está falando ... paleta
  de cores verde ... lettering moderno e com dinamismo"): cenas em tela cheia, fundo verde-escuro, menta e lima,
  Poppins Black + Plus Jakarta. No plano, `"tipo": "video"` no B-roll. **Sem legenda enquanto o motion está na
  tela** e o conteúdo **centrado no quadro, a ~80%** do tamanho do primeiro (pedido de 2026-10-30: "retirar as
  legendas nos momentos em que o motion aparece ... puxar o motion mais para baixo, e diminuir ... centralizar
  todos os elementos"): `tools/planos/sabrina_24_motion.py` mede a caixa da cena e a põe no centro; nas legendas,
  `"sem_legenda": [[ini, fim], ...]` (as janelas do B-roll) no plano do `capcut_legendas_ig.py`.
- **Efeitos sonoros nos motions** (2026-10-30: "profissional, sem esses efeitos clichês ... cada vez que entra uma
  nova frase nos motions ... variar ... sobrepor ... sutil, fluido"): um evento por elemento que entra, no quadro
  em que ele aparece, feito em `tools/sfx_sintese.py` (sopro de ar, tique digital, grave sentido, traço de caneta,
  papel, inchaço, batida seca, e obturador / meio clique / motor de foco recortados do kit dela; camadas
  sobrepostas). **Sem notas** (a nota de vidro "parece teclas de piano tocando ... ficou ruim", 2026-10-30): no
  lugar dela, clique ou obturador. Posto no CapCut com
  `tools/capcut_sfx.py` (um clipe por evento, trilhas "SFX motions (Concat)"). Nível: ~17-20 dB abaixo da voz
  (-35 a -40 LUFS momentâneo, picos -20 a -27 dBFS), no máximo o do whoosh dela a 45%. Nada de clique de mouse,
  "pop" ou "boing". Processo, paleta e como variar a cada vídeo: skill `sfx-motion`
  (`.claude/skills/sfx-motion/SKILL.md`); mapa de eventos em JSON para `tools/sfx_motion.py`.

## 7. Como trabalhar (regras do usuário)
- **Escopo:** mexa só no vídeo que ele apontou; não refaça os outros por iniciativa própria.
- **Tempos** que ele passa vêm em `mm:ss:quadros`.
- **Nomes próprios:** pasta ou arquivo não é fonte de grafia. Segunda transcrição com outro modelo
  nas dúvidas e, se persistir, pergunte antes de queimar a legenda. No fim, liste o texto das legendas.
- **Exemplos e testes** vão no projeto do Concat para ele ver na janela; nada de MP4 sem pedido.
- **Sem cópias de projeto** para revisar, testar ou exportar: todo projeto aberto pela API entra nos
  recentes do Concat e vira card repetido. Quadros com `tools/quadros.py`/`render_projeto.py`;
  exportação com o projeto na janela via `tools/exportar_seguro.py`.
- **Mudou uma regra de edição?** Atualize este arquivo, a skill e as ferramentas, e envie ao GitHub.
- **Cortes de podcast/entrevista:** processo próprio em `tools/cortes_podcast/LEIA-ME.md`.
- **Kit de edição** (SFX, transição, música do padrão vindo do CapCut): valores em
  `referencias/kit-de-edicao/` (os arquivos de áudio e LUT ficam fora do Git, por licença).

---

## Ordem dos comandos
```bash
PY=tools/.venv/bin/python          # venv com higgsfield-client, pillow, fonttools, opencv<5
P="$(dirname "$PWD")/editados/<nome>"    # pasta do projeto (pasta Concat = mãe do repositório)

# 1. criar o projeto 2160x3840 a 30 fps, importar o bruto e pô-lo em T1 (project.create, media.import, addClip)
# 2. transcrever (mlx-whisper large-v3-turbo, tempo por palavra) -> words.json e cortes.json
$PY tools/cortar_ao_vivo.py "$P" cortes.json --pausa 0
#    1.10x + empacotar (setClipSpeed + moveClips), depois:
$PY tools/alinhar_quadros.py "$P"                       # depois: project.save
#    (sem nitidez nem cor automáticas; só se pedirem: addLayerClip concat.adjust em T3)
$PY tools/capcut_legendas_ig.py --concat="$P" words.json blocos.json   # legendas: simples + blocos (seção 2)
$PY tools/zoom_cortes.py "$P" ref_legendas.json plano_zoom.json
$PY tools/centralizar_zoom.py "$P"          # take a take; --estampa se houver estampa no peito
$PY tools/broll_higgsfield.py plano_broll.json "$P/broll" <cena-teste>   # depois as outras
$PY tools/broll_imagens.py "$P" plano_broll.json "$P/broll"
$PY tools/broll_animar.py "$P"
$PY tools/exportar.py "$P" "$(dirname "$PWD")/exportados/<nome>.mp4"   # só se pedirem; 4K, SDR
#    por fim: project.close (save)
```
Os formatos dos planos estão em `tools/planos_exemplo/`.

## Windows
O processo e o estilo são os mesmos; `tools/plataforma.py` troca só o que é do Mac (transcrição em
faster-whisper, Arimo no lugar da Helvetica, Archivo Condensed Black no lugar da Helvetica Neue
Condensed Black, codificador da placa). Python: `tools/.venv/Scripts/python.exe`. Instalação e tabela
completa em `INSTALAR-WINDOWS.md`.

## Requisitos
Instalação num Mac novo: `INSTALAR.md` (o `tools/setup.sh` faz quase tudo).
- Concat deste fork aberto, com a API ligada (porta 7420); o setup liga e grava o token em `.concat-token`.
- Chave da API do Higgsfield em `.env.local` (`HF_KEY=id:segredo`), gravada com
  `tools/configurar_chave_higgsfield.sh`. Nunca a cole em chat nem a commite.
- Fontes: as livres (Montserrat, Poppins, Plus Jakarta, Playfair) vêm no repositório; Coolvetica e as
  faces da Helvetica Neue o setup obtém.
