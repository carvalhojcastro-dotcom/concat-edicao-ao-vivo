# CLAUDE.md

Este repositório é um **fork modificado do Concat** (editor de vídeo, Rust/Slint) usado para editar
reels verticais. Veja `FORK.md` (o que mudou no código) e `EDICAO.md` (o estilo de edição).

## Quando o usuário pedir para editar um vídeo
"edita esse vídeo", "edite o C5430 e salve como X", "faça a parte 1", "põe legendas dinâmicas",
"coloca b-roll": **use a skill `edicao-reels`** (`.claude/skills/edicao-reels/SKILL.md`) e faça o
processo completo sem pedir confirmação no meio. Deixe o projeto pronto em `../editados/<nome>` (a pasta
Concat é a mãe deste repositório) e informe o custo do Higgsfield. **Exporte o MP4 (4K 30 fps, em
`../exportados`) só quando pedirem.** Regras de trabalho do usuário: seção 7 de `EDICAO.md`.

## Pastas
`Concat/` = `editados/` (projetos), `exportados/` (MP4), `referencias/` (prints, vídeo-aula, kit;
atalho para `ferramentas/referencias`) e `ferramentas/` (este repositório). Num Mac novo: `INSTALAR.md`.

## Regras fixas
- O estilo e os padrões numéricos estão em `EDICAO.md`; as ferramentas já os têm como padrão.
- Segredos: `.concat-token` (API do Concat) e `.env.local` (`HF_KEY` do Higgsfield) **nunca** vão para
  o Git nem para o chat. Não leia nem imprima seus valores. A chave é gravada pelo usuário com
  `tools/configurar_chave_higgsfield.sh`.
- Não commite `dist/`, `tools/.venv/`, `tools/planos/` (conteúdo de clientes) nem as fontes de licença
  própria (Coolvetica, Helvetica Neue extraída; a Scholar não é mais usada); o `.gitignore` já cuida disso.
- Primeira vez numa máquina: `INSTALAR.md` (`./tools/setup.sh` baixa o Concat da Release do GitHub;
  `--compilar` compila do código).
- Mudou uma regra de edição: atualize `EDICAO.md`, a skill e as ferramentas, e envie ao GitHub.
- Mudou o código do Concat (`src/`): compile, instale e publique uma Release nova com o
  `Concat-<versão>-mac-arm64.zip` (ver `INSTALAR.md`).
