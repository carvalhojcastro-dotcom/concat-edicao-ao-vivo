# Estilo de edição de reels: o padrão deste fork

Guia do estilo de edição montado e aprovado vídeo a vídeo, para reels verticais de um especialista
falando para a câmera (talking head). Ele vai do **bruto da câmera** ao **MP4 4K 30 fps pronto**,
usando o Concat deste fork pela API (porta 7420) e as ferramentas de `tools/`.

> Com o Claude Code aberto nesta pasta, a skill `.claude/skills/edicao-reels` faz todo o
> processo sozinha: "edite o C5430 dos Downloads e salve como 10 - Título".

---

## O resultado, em uma frase
O vídeo começa no apresentador já falando, sem pausas nem tomadas ruins, a 1.05x. Tem legenda
palavra por palavra, frases de destaque montadas palavra a palavra em fontes mistas, zoom seco
centralizado por frase e B-rolls de imagem gerados por IA que entram e saem nos cortes com
movimento lento. A exportação é em 4K a 30 fps.

---

## 1. Parte 1: o básico
| Item | Padrão |
|---|---|
| **Tomadas** | Fica sempre a última tomada completa e limpa de cada trecho. Saem bastidor e falas de produção ("ficou ruim", "desculpa", "vamos de novo", "pode soltar"). |
| **Bordas dos trechos** | Começa e termina na 1ª e na última batida de voz acima de -30 dB, com 0,06 s de folga. O Whisper marca a 1ª palavra até 0,7 s cedo, então não confie nele para a borda. |
| **Pausas** | Corta toda pausa ≥0,2 s, **respirações incluídas**: RMS em janelas de 25 ms, abaixo de -36 dB por ≥0,15 s, deixando 0,05 s de respiro de cada lado. |
| **Velocidade** | 1.05x em todos os clipes, sem folgas, alinhados à grade de quadros (`alinhar_quadros.py`). |
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
| **serifa** | Helvetica normal, em escadinha | Scholar **reto** e apertado, **branco** |
| **classico** | Helvetica normal (com 2 palavras, vão para as pontas) | Helvetica Neue **Condensed Black** grande |
| **elegante** | Montserrat **Light**, centralizada | Scholar reto enorme, encostado |

- **Regra de fontes:** **Scholar só na palavra de destaque** (a chave). Tudo o mais, pequeno ou
  grande, sai em fonte sóbria, normal e reta (Helvetica ou Montserrat), nunca fina nem cursiva.
- **Pesos iguais aos prints de fonte** (`referencias/Legendas dinamicas`, pedido de 2026-10-20):
  "helvetica" = Helvetica Neue **Condensed Black**; "montserrat" = Montserrat **Light**; "scholar" = Scholar
  **Regular** reto, tracking -0,04; "coolvetica" = Coolvetica Regular. As fontes ficam em `fonts/`
  (o `setup.sh` extrai a Condensed Black do sistema; Montserrat Light e Coolvetica são baixadas).
- **Destaque nem sempre em Scholar**: no serifa e no elegante, `"fonte_chave"` na frase escolhe
  `serifa` (Scholar reto, padrão), `italico`, `bold` (Condensed Black) ou `coolvetica`. **Alterne** ao
  longo do vídeo. Uma fonte mais larga encolhe até a largura do Scholar, então o bloco não muda de forma.
- A Montserrat Light das palavras pequenas do elegante é a exceção à regra "nunca fina": vem do print e
  o contorno + sombra seguram a leitura.
- **Tamanho e posição:** 92% do tamanho, **contorno preto fino + sombra**. O bloco **começa na mesma
  altura da legenda simples** (pedido de 2026-10-21): o topo das letras da 1ª linha fica no topo das
  letras da simples, e o bloco cresce para baixo. A altura é lida das legendas do próprio projeto;
  `--centro=0.67` volta ao bloco centrado.
- **Entrelinha:** ótica e igual em todas as linhas (pedido de 2026-10-20): o vão vai da base de cima ao
  topo das minúsculas de baixo (0,30 em da letra pequena, `--aperto=`); hastes e perninhas entram nos
  vãos e as linhas só se afastam onde uma letra fosse de fato encostar na outra.
- **Cor do destaque:** **branco** por padrão (pedido de 2026-10-20). O destaque se diferencia pela
  fonte (Scholar Itálico) e pelo tamanho, não pela cor. Amarelo #f4c430 ou a cor do cliente só quando
  pedirem, pelo `"destaque"` do plano. Se usar uma cor escura, rode `contraste_destaques.py`, que troca para branco quando o fundo atrás é escuro.

## 3. Zoom seco (punch-in)
- **Sem animação.** O enquadramento muda no começo das frases: 100%, 118% e **132% nas frases de
  impacto** (como "Salve este vídeo").
- **Um enquadramento fixo por trecho de zoom**, centralizado na posição média do rosto no trecho
  (`centralizar_zoom.py`, OpenCV). Nunca recentralize a cada take.
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
- **Modelos:**
  - `z-image/turbo`: US$ 0,015/imagem, 2K 9:16, o padrão. Ele **lê negação ao contrário**
    ("no doctors" coloca médicos), então descreva só o que deve aparecer.
  - `higgsfield-ai/soul/v2/standard`: US$ 0,0057 em 1080p, o mais barato. Às vezes divide a imagem
    em quadros em cenas de pessoa deitada; resolva com close no rosto.

## 5. Entrega
- Exporte em **4K 2160×3840 a 30 fps** (crie o projeto já em 30 fps).
- Confira quadros do MP4 final: legendas, B-rolls, zoom, início e fim.
- Feche o projeto na API (`project.close` com save), senão ele não abre na janela do Concat.

---

## Ordem dos comandos
```bash
PY=tools/.venv/bin/python          # venv com higgsfield-client, pillow, fonttools, opencv<5
P="$HOME/Desktop/Concat/editados/<nome>"    # pasta do projeto

# 1. criar o projeto 2160x3840 a 30 fps, importar o bruto e pô-lo em T1 (project.create, media.import, addClip)
# 2. transcrever (mlx-whisper large-v3-turbo, tempo por palavra) -> words.json e cortes.json
python3 tools/cortar_ao_vivo.py "$P" cortes.json --pausa 0
#    1.05x + empacotar (setClipSpeed + moveClips), depois:
python3 tools/alinhar_quadros.py "$P"                       # depois: project.save
python3 tools/legendas_simples.py "$P" words.json T4        # 92%, offsetY 0.17, contorno fino
#    (sem nitidez nem cor automáticas; só se pedirem: addLayerClip concat.adjust em T3)
$PY tools/legendas_dinamicas.py "$P" plano_dinamicas.json   # 92%, centro 0.67
python3 tools/zoom_cortes.py "$P" ref_legendas.json plano_zoom.json
$PY tools/centralizar_zoom.py "$P"
$PY tools/broll_higgsfield.py plano_broll.json "$P/broll" <cena-teste>   # depois as outras
python3 tools/broll_imagens.py "$P" plano_broll.json "$P/broll"
python3 tools/broll_animar.py "$P"
python3 tools/exportar.py "$P" "$HOME/Desktop/Concat/exportados/<nome>.mp4"   # 4K, fps do projeto
#    por fim: project.close (save)
```
Os formatos dos planos estão em `tools/planos_exemplo/`.

## Requisitos
- Concat deste fork aberto, com a API ligada (Configurações › API, porta 7420); o token fica em `.concat-token`.
- Chave da API do Higgsfield em `.env.local` (`HF_KEY=id:segredo`), gravada com
  `tools/configurar_chave_higgsfield.sh`. Nunca a cole em chat nem a commite.
- Fontes Scholar (Regular/Italic) e Montserrat Bold em `fonts/`. Não estão no repositório por licença.
