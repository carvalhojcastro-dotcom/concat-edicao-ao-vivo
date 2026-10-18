# Estilo de edição de reels: o padrão deste fork

Guia do estilo de edição montado e aprovado vídeo a vídeo, para reels verticais de um especialista
falando para a câmera (talking head). Ele vai do **bruto da câmera** ao **MP4 4K 30 fps pronto**,
usando o Concat deste fork pela API (porta 7420) e as ferramentas de `tools/`.

> Com o Claude Code aberto nesta pasta, a skill `.claude/skills/edicao-reels` faz todo o
> processo sozinha: "edite o C5430 dos Downloads e salve na Mesa como 10 - Título".

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
| **Nitidez** | Camada `concat.adjust` com `sharpen` 20.23 em T3, entre o vídeo e as legendas. |
| **Cor** | Nenhuma correção, até haver uma LUT definida para o cliente. |

## 2. Legendas Dinâmicas
Frases importantes viram um bloco tipográfico. Cada palavra é um clipe que **entra quando é dita**
(sobe e aparece em 0,2 s) e **todas saem juntas** quando a frase acaba.

- **Quantidade:** cerca de **20 a 22 frases por minuto**, nas frases importantes.
- **Abertura:** **as primeiras frases do vídeo são sempre dinâmicas**, como gancho.
- **Variedade:** alterne os 4 estilos, nunca o mesmo em duas frases seguidas.
- **Proibido:** o efeito "falha" (palavra piscando).

| Estilo | Palavras pequenas | Palavra-chave (grande) |
|---|---|---|
| **impacto** | Helvetica normal, bloco à esquerda | Helvetica Bold Oblíqua grande |
| **serifa** | Helvetica normal, em escadinha | Scholar Itálico **amarelo** |
| **classico** | Helvetica normal (com 2 palavras, vão para as pontas) | Helvetica Bold grande |
| **elegante** | Montserrat Bold, centralizada | Scholar Itálico enorme, encostado |

- **Regra de leitura:** palavras pequenas sempre em **letra normal e reta**; fonte fina e cursiva
  **só nas palavras grandes**.
- **Tamanho e posição:** 92% do tamanho, centro do bloco a **67% da altura** (abaixo do rosto),
  **contorno preto fino + sombra**.
- **Cor do destaque:** **amarelo #f4c430**. Com o contorno, lê bem em fundo claro e escuro. Se usar
  uma cor escura, rode `contraste_destaques.py`, que troca para branco quando o fundo atrás é escuro.

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
P="$HOME/Desktop/Concat/<nome>"    # pasta do projeto

# 1. criar o projeto 2160x3840 a 30 fps, importar o bruto e pô-lo em T1 (project.create, media.import, addClip)
# 2. transcrever (mlx-whisper large-v3-turbo, tempo por palavra) -> words.json e cortes.json
python3 tools/cortar_ao_vivo.py "$P" cortes.json --pausa 0
#    1.05x + empacotar (setClipSpeed + moveClips), depois:
python3 tools/alinhar_quadros.py "$P"                       # depois: project.save
python3 tools/legendas_simples.py "$P" words.json T4        # 92%, offsetY 0.17, contorno fino
#    camada de nitidez: addLayerClip concat.adjust em T3 + sharpen 20.23
$PY tools/legendas_dinamicas.py "$P" plano_dinamicas.json   # 92%, centro 0.67
python3 tools/zoom_cortes.py "$P" ref_legendas.json plano_zoom.json
$PY tools/centralizar_zoom.py "$P"
$PY tools/broll_higgsfield.py plano_broll.json "$P/broll" <cena-teste>   # depois as outras
python3 tools/broll_imagens.py "$P" plano_broll.json "$P/broll"
python3 tools/broll_animar.py "$P"
python3 tools/exportar.py "$P" "$HOME/Desktop/<nome>.mp4"   # 4K, fps do projeto
#    por fim: project.close (save)
```
Os formatos dos planos estão em `tools/planos_exemplo/`.

## Requisitos
- Concat deste fork aberto, com a API ligada (Configurações › API, porta 7420); o token fica em `.concat-token`.
- Chave da API do Higgsfield em `.env.local` (`HF_KEY=id:segredo`), gravada com
  `tools/configurar_chave_higgsfield.sh`. Nunca a cole em chat nem a commite.
- Fontes Scholar (Regular/Italic) e Montserrat Bold em `fonts/`. Não estão no repositório por licença.
