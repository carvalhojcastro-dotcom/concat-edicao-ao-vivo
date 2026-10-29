# CLAUDE.md

Este repositório é um **fork modificado do Concat** (editor de vídeo, Rust/Slint) usado para editar
reels verticais. Veja `FORK.md` (o que mudou no código) e `EDICAO.md` (o estilo de edição).

## Quando pedirem para instalar ("instala isso", "instala esse projeto", o link deste repositório)
Faça a instalação inteira, sem pedir confirmação a cada passo, seguindo **`INSTALAR-WINDOWS.md`** no
Windows ou **`INSTALAR.md`** no Mac (Apple Silicon). Se o repositório ainda não estiver clonado, comece
pelos passos 1 a 3 desses arquivos (o link é privado: precisa do `gh` logado numa conta com acesso).
- Só a pessoa pode: **entrar no GitHub** (`gh auth login`) e **digitar a chave do Higgsfield**
  (`tools/configurar_chave_higgsfield.ps1` no Windows, `.sh` no Mac). Peça para ela rodar esses dois no
  terminal do Claude Code com `!` na frente; nunca peça a chave no chat.
- No fim, confira: o Concat abre, a porta 7420 responde (`tools/ligar_api.py --checar` sai com 0) e
  `tools/.venv` importa `faster_whisper` (Windows) ou `mlx_whisper` (Mac). Diga o que ficou pronto e o
  que falta (em geral, só a chave do Higgsfield).

## Quando o usuário pedir para editar um vídeo
"edita esse vídeo", "edite o C5430 e salve como X", "faça a parte 1", "põe legendas dinâmicas",
"coloca b-roll": **use a skill `edicao-reels`** (`.claude/skills/edicao-reels/SKILL.md`) e faça o
processo completo sem pedir confirmação no meio. Deixe o projeto pronto em `../editados/<nome>` (a pasta
Concat é a mãe deste repositório) e informe o custo do Higgsfield. **Exporte o MP4 (4K 30 fps, em
`../exportados`) só quando pedirem.** Regras de trabalho do usuário: seção 7 de `EDICAO.md`.
**Legendas padrão (desde 2026-10-29):** o estilo das referências do Instagram (`EDICAO.md` 6f, Poppins branca,
simples + blocos dinâmicos, sem animação), no Concat ou no CapCut, com `tools/capcut_legendas_ig.py`. Os estilos
antigos (impacto, serifa, clássico, elegante, prints) só quando o usuário pedir por eles.

## Pastas
`Concat/` = `editados/` (projetos), `exportados/` (MP4), `referencias/` (prints, vídeo-aula, kit;
atalho para `ferramentas/referencias`) e `ferramentas/` (este repositório). A pasta Concat fica na Área
de Trabalho (no Windows, `[Environment]::GetFolderPath("Desktop")`, que pode estar no OneDrive).

## Windows
O mesmo processo roda no Windows (`tools/plataforma.py` troca transcrição, fontes e codificador). No
Windows o Python das ferramentas é `tools/.venv/Scripts/python.exe`: use-o sempre no lugar de `python3`
(que no Windows é um atalho da Microsoft Store) e de `tools/.venv/bin/python`.

## Regras fixas
- O estilo e os padrões numéricos estão em `EDICAO.md`; as ferramentas já os têm como padrão.
- Segredos: `.concat-token` (API do Concat) e `.env.local` (`HF_KEY` do Higgsfield) **nunca** vão para
  o Git nem para o chat. Não leia nem imprima seus valores. A chave é gravada pelo usuário com
  `tools/configurar_chave_higgsfield.sh` (Mac) ou `.ps1` (Windows).
- Não commite `dist/`, `tools/.venv/`, `tools/planos/` (conteúdo de clientes) nem as fontes de licença
  própria (Coolvetica, Helvetica Neue extraída; a Scholar não é mais usada); o `.gitignore` já cuida disso.
- Primeira vez numa máquina: `INSTALAR.md` (Mac) ou `INSTALAR-WINDOWS.md` (Windows); os setups baixam
  o Concat deste fork da Release do GitHub.
- Mudou uma regra de edição: atualize `EDICAO.md`, a skill e as ferramentas, e envie ao GitHub.
- Mudou o código do Concat (`src/`): publique uma Release nova com o `Concat-<versão>-mac-arm64.zip`
  (ver `INSTALAR.md`) **e** o instalador do Windows (`Concat-<versão>-windows-x86_64-setup.exe`, feito
  pelo workflow "Build Windows (fork)" no GitHub Actions).
