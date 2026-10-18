# concat-edicao-ao-vivo

Fork **modificado** do [Concat](https://github.com/jub0t/Concat) (versão 0.2.7), um editor de
vídeo open source em Rust/Slint. O código continua sob a licença **AGPL-3.0-or-later**
(veja `LICENSE` e `LICENSE-EXCEPTIONS.md`). "Concat" e o logo são marcas do autor original
(veja `TRADEMARK.md`). Este fork não é um build oficial e, se for distribuído a terceiros,
deve usar outro nome e outro ícone.

## Editar um vídeo: "edita esse vídeo"
1. Uma vez por máquina: `./tools/setup.sh --app`, instale `dist/Concat.app` em /Applications, ligue a
   API em Configurações > API e salve o token em `.concat-token`. Para B-roll, rode
   `./tools/configurar_chave_higgsfield.sh`.
2. Abra o **Claude Code** nesta pasta e diga: **"edita esse vídeo: ~/Downloads/C5430.MP4 e salva como
   Meu Título"**. A skill `.claude/skills/edicao-reels` faz o processo inteiro e entrega o MP4 4K 30 fps
   na Mesa.

O estilo de edição (regras e números) está em **[EDICAO.md](EDICAO.md)**.

## O que muda em relação ao original

### 1. API JSON-RPC que edita ao vivo o projeto aberto na janela
- `concat-api`: `Api::share_window`, `WindowLink` e `for_window`. Pedidos para o projeto que
  está aberto na janela (abrir, ler, editar, desfazer, salvar, importar mídia) vão para a
  própria janela, em vez de serem recusados, e as edições aparecem na tela na hora.
- `concat/src/studio.rs`: `Studio::api_request` e `api_apply`, que aplicam as edições pelo
  mesmo caminho de um clique (histórico, autosave, monitor e mix).
- `concat/src/panes/settings.rs`: `window_link()` espera até 120 s pela janela, num laço de
  `recv_timeout` curto. Se a API for parada no laço de eventos, o pedido é solto em até
  0,1 s, sem travar. Num timeout, a mensagem avisa que a edição pode ter sido aplicada e
  pede para conferir com `project.get`.

### 2. Títulos com sombra cerca de 8× mais rápidos
- `concat-text`: o desfoque da sombra é feito só na região das palavras, e não no quadro
  inteiro; a composição também. O resultado é idêntico pixel a pixel, e há um teste novo
  para isso. Um lote de 129 legendas em 4K caiu de 25 s para 5 s.

### 3. Layout da janela para vídeo vertical
- `concat/src/dock.rs`, `lib.rs` e `prefs.rs`: o monitor fica numa coluna inteira à
  direita, e o arranjo dos painéis é lembrado entre uma abertura e outra.

### 4. Ferramentas de edição de reels (`tools/`, Python)
Scripts que falam com a API (porta 7420; o token fica em `.concat-token`, fora do Git):

| Script | O que faz |
|---|---|
| `cortar_ao_vivo.py` | corta trechos (segundos da mídia) com ripple |
| `alinhar_quadros.py` | alinha clipes à grade de quadros (evita quadro preto) |
| `legendas_simples.py` | legenda palavra por palavra a partir do Whisper |
| `legendas_dinamicas.py` | frases em destaque palavra a palavra, 4 estilos, fontes mistas |
| `zoom_cortes.py` / `centralizar_zoom.py` | zoom seco por frase, centralizado no rosto (OpenCV) |
| `broll_higgsfield.py` | gera B-roll de imagem pela API do Higgsfield (chave em `.env.local`) |
| `broll_imagens.py` / `broll_animar.py` | posiciona B-roll nos cortes e anima |
| `contraste_destaques.py` | escolhe a cor do destaque pelo brilho do fundo |
| `exportar.py` | exporta pela API (padrão 4K) |
| `quadros.py` | renderiza quadros para conferência |
| `reel.py` | etapas mecânicas: novo projeto, transcrição, cortes/tomadas, 1.05x, nitidez, listar, fechar |
| `setup.sh` | instala dependências, venv, fontes e (com `--app`) compila o Concat |

As ferramentas usam um venv próprio (`tools/.venv`) com `higgsfield-client`, `python-dotenv`,
`pillow`, `fonttools` e `opencv-python-headless<5`. As fontes Scholar e Montserrat **não**
estão no repositório: coloque os arquivos em `fonts/`.

## Compilar (macOS)
```bash
./build-mac.sh      # cargo build --release -p concat (Homebrew: rustup, ffmpeg)
./bundle-mac.sh     # monta dist/Concat.app com o FFmpeg embutido e assinatura ad-hoc
```
