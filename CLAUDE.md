# CLAUDE.md

Este repositório é um **fork modificado do Concat** (editor de vídeo, Rust/Slint) usado para editar
reels verticais. Veja `FORK.md` (o que mudou no código) e `EDICAO.md` (o estilo de edição).

## Quando o usuário pedir para editar um vídeo
"edita esse vídeo", "edite o C5430 e salve como X", "faça a parte 1", "põe legendas dinâmicas",
"coloca b-roll": **use a skill `edicao-reels`** (`.claude/skills/edicao-reels/SKILL.md`) e faça o
processo completo sem pedir confirmação no meio. Entregue o MP4 4K 30 fps na Mesa e informe o custo do
Higgsfield.

## Regras fixas
- O estilo e os padrões numéricos estão em `EDICAO.md`; as ferramentas já os têm como padrão.
- Segredos: `.concat-token` (API do Concat) e `.env.local` (`HF_KEY` do Higgsfield) **nunca** vão para
  o Git nem para o chat. Não leia nem imprima seus valores. A chave é gravada pelo usuário com
  `tools/configurar_chave_higgsfield.sh`.
- Não commite `dist/`, `fonts/`, `tools/.venv/` nem `tools/planos/` (conteúdo de clientes).
- Primeira vez numa máquina: `./tools/setup.sh` (e `--app` para compilar o Concat deste fork).
