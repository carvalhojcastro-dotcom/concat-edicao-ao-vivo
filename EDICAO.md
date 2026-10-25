# Estilo de edição de reels: o padrão deste fork

Guia do estilo de edição montado e aprovado vídeo a vídeo, para reels verticais de um especialista
falando para a câmera (talking head). Ele vai do **bruto da câmera** ao **MP4 4K 30 fps pronto**,
usando o Concat deste fork pela API (porta 7420) e as ferramentas de `tools/`.

> Com o Claude Code aberto nesta pasta, a skill `.claude/skills/edicao-reels` faz todo o
> processo sozinha: "edite o C5430 dos Downloads e salve como 10 - Título".

---

## O resultado, em uma frase
O vídeo começa no apresentador já falando, sem pausas nem tomadas ruins, a 1.10x. Tem legenda
palavra por palavra, frases de destaque montadas palavra a palavra em fontes mistas, zoom seco
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
| **Legenda simples** | Uma palavra por vez, Helvetica 400 branca, **92% do tamanho base** (0.04302), tracking -0.05 em (o "-0.3" do CapCut), **contorno preto fino + sombra**, offsetY **0.17** (abaixo do rosto). |
| **Texto da legenda** | Sem ponto final; maiúscula só no início de frase; "?" e vírgulas ficam. Corrija erros do Whisper e junte palavras partidas ("sente" + "-se"). |
| **Nitidez e cor** | **Não aplicar automaticamente** (pedido de 2026-10-19). Só quando pedirem: camada `concat.adjust` em T3 (nitidez antiga: `sharpen` 20.23). |
| **Retoque de rosto** | **Sempre em vídeo de mulher.** `tools/retoque.py` copia a predefinição do CapCut: remover rugas 13, uniforme 12, linhas do sorriso 93, olheiras 17 e maquiagem "Naturais" 56. Gera uma cópia retocada do bruto e troca a mídia no projeto (`--projeto`). |
| **Cor** | Nenhuma correção, até haver uma LUT definida para o cliente. |

## 2. Legendas Dinâmicas
Referências do cliente (prints dos estilos e das fontes e o vídeo "Como fazer as legendas"):
`~/Desktop/Concat/referencias/Legendas dinamicas`.

**São as legendas favoritas do usuário**, chamadas por quem pede de "legendas dinâmicas": o valor está na
tipografia mista **somada à animação de entrada** de cada palavra. Sem a animação, não é o estilo.
Do print 1 vale **a disposição das palavras** (escadinha); a fonte serifada vai só em uma ou outra
palavra de destaque, nunca na frase toda. Prints → estilos: 1 = serifa, 2 = classico, 3 = elegante, 5 e 6 = impacto.

Frases importantes viram um bloco tipográfico. Cada palavra é um clipe que **entra quando é dita**
(sobe e aparece em 0,2 s) e **todas saem juntas** quando a frase acaba.

- **Quantidade:** cerca de **18 a 22 frases por minuto**, nas frases importantes. Referência aprovada
  ("bem fluido e prendendo bastante a atenção", 2026-10-21): o projeto `editados/Exemplos - legendas
  dinamicas`, com 11 frases em 36 s (~18/min), **cerca de metade das palavras** em dinâmica e metade em
  legenda simples, frases de 2 a 4 linhas, uma nova a cada 1 a 6 s com legenda simples entre elas, sem
  repetir estilo nem fonte de destaque em frases seguidas. O plano está em `plano_exemplos.json` lá.
- **A proporção é um guia, não uma cota** (2026-10-21): varia conforme o vídeo pede. O que manda é o
  roteiro: a dinâmica vai **sempre nas frases e palavras de maior destaque** (a ideia central, o dado, o
  alerta, o chamado). Nunca use frase de passagem só para chegar ao número; se o trecho não tem frase
  forte, fica em legenda simples.
- **Abertura:** **as primeiras frases do vídeo são sempre dinâmicas**, como gancho.
- **Variedade:** alterne os 4 estilos, nunca o mesmo em duas frases seguidas.
- **Proibido:** o efeito "falha" (palavra piscando).

| Estilo | Palavras pequenas | Palavra-chave (grande) |
|---|---|---|
| **impacto** | Helvetica normal, bloco à esquerda | Helvetica Bold Oblíqua grande |
| **serifa** | Helvetica normal, em escadinha | DM Serif Display **reta**, **branca** |
| **classico** | Helvetica normal (com 2 palavras, vão para as pontas) | Helvetica Neue **Condensed Black** grande (`"fonte_chave": "reta"`: Helvetica **Bold** reta, print "como que / eu faço") |
| **elegante** | Helvetica Neue **Medium** (semibold), centralizada | DM Serif Display enorme, encostada (print "as minhas / legendas") |

- **Regra de fontes:** **a serifada (DM Serif Display) só na palavra de destaque** (a chave). Tudo o mais, pequeno ou
  grande, sai em fonte sóbria, normal e reta (Helvetica ou Montserrat), nunca fina nem cursiva.
- **Pesos iguais aos prints de fonte** (`referencias/Legendas dinamicas`, pedido de 2026-10-20):
  "helvetica" = Helvetica Neue **Condensed Black**; "montserrat" = Montserrat **Light**; "scholar" = **DM Serif Display**
  reta, tracking -0,02 (no lugar da Scholar, que só tinha licença no CapCut; 2026-10-21); "coolvetica" = Coolvetica Regular. As fontes ficam em `fonts/`
  (o `setup.sh` extrai a Condensed Black do sistema; Montserrat Light e Coolvetica são baixadas).
- **Destaque nem sempre serifado**: no serifa e no elegante, `"fonte_chave"` na frase escolhe
  `serifa` (DM Serif Display reta, padrão), `italico`, `bold` (Condensed Black) ou `coolvetica`. **Alterne** ao
  longo do vídeo. Uma fonte mais larga encolhe até a largura da serifada, então o bloco não muda de forma.
- **Pesos semibold ou bold** (pedido de 2026-10-23: "priorize usar fontes mais semibold ou bold, evitando
  pesos mais finos"): as palavras pequenas de todos os estilos saem em Helvetica Neue Medium; a
  Montserrat Light do elegante saiu.
- **Tamanho e posição:** 92% do tamanho, **contorno preto fino + sombra**. O bloco **começa na mesma
  altura da legenda simples** (pedido de 2026-10-21): o topo das letras da 1ª linha fica no topo das
  letras da simples, e o bloco cresce para baixo. A altura é lida das legendas do próprio projeto;
  `--centro=0.67` volta ao bloco centrado.
- **Entrelinha:** ótica e igual em todas as linhas (pedido de 2026-10-20): o vão vai da base de cima ao
  topo das minúsculas de baixo (0,30 em da letra pequena, `--aperto=`); hastes e perninhas entram nos
  vãos e as linhas só se afastam onde uma letra fosse de fato encostar na outra.
- **Cor do destaque:** **branco** por padrão (pedido de 2026-10-20). O destaque se diferencia pela
  fonte (serifada) e pelo tamanho, não pela cor. Amarelo #f4c430 ou a cor do cliente só quando
  pedirem, pelo `"destaque"` do plano. Se usar uma cor escura, rode `contraste_destaques.py`, que troca para branco quando o fundo atrás é escuro.

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

## 6. Legenda sobre roupa com estampa
Na camiseta com estampa clara no peito (ex.: "SIMPLES MEDICINA" do Dr. Leonardo), a legenda branca
some. Antes de legendar, olhe a roupa; se houver estampa clara:
- zoom normal (enquadrado com `--estampa`, ver abaixo) e legenda **abaixo da estampa**, na parte escura (faixa do fim da
  estampa + 0,025 até 0,86 da altura; largura até 0,56; linhas acima de 20 caracteres em duas,
  preset `linha2`);
- sobre B-roll claro, **nada de contorno grosso** ("não use traços tão fortes"): use `sombra_suave`;
- confira todas as frases numa folha de quadros antes de entregar.
- **Roupa clara** (camiseta branca/creme, Dr. Leonardo vídeos 5 a 8): a legenda branca some no tecido.
  `tools/sombra_legenda.py <projeto>` põe uma sombra em degradê (PNG transparente numa trilha entre o vídeo
  e as legendas, escurecendo ~70% de 0,70 até 0,80 da altura e até a base), sem mudar o estilo das
  legendas. Placa atrás da palavra (`legendas_simples.py --fundo=#000000a6`) existe, mas não serve aos
  blocos dinâmicos. A estampa escura em roupa clara também é achada pelo `--estampa`.
- **Com zoom** (Ozempic, 2026-10-21): `centralizar_zoom.py <projeto> --estampa` (cabeça ≥ 10% do topo, estampa
  ≤ 0,745); legenda simples com o topo das letras em 0,769 (`--altura=` calculada) e dinâmicas com
  `--escala=0.85`, blocos de 2 linhas.

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
  a cabeça fica a 24%). Legendas do meio para baixo: `legendas_simples.py --altura=0.15`.

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
$PY tools/legendas_simples.py "$P" words.json T4        # 92%, offsetY 0.17, contorno fino
#    (sem nitidez nem cor automáticas; só se pedirem: addLayerClip concat.adjust em T3)
$PY tools/legendas_dinamicas.py "$P" plano_dinamicas.json   # 92%, começa na altura da legenda simples
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
