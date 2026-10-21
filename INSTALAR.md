# Instalar em outro Mac

Para montar num Mac novo (Apple Silicon) o mesmo editor com o mesmo jeito de editar: o Concat
deste fork, as ferramentas, as fontes, as referências e a skill que o Claude Code usa.

## O que você precisa antes
- Mac com chip Apple (M1 ou mais novo).
- [Homebrew](https://brew.sh) instalado.
- Acesso ao repositório privado no GitHub (`carvalhojcastro-dotcom/concat-edicao-ao-vivo`).
- [Claude Code](https://claude.com/claude-code) instalado.

## Passo a passo

**1. Clonar dentro de uma pasta `Concat`.** O repositório vira a subpasta `ferramentas`; o setup
cria `editados/`, `exportados/` e `referencias/` ao lado dele.
```bash
mkdir -p ~/Desktop/Concat
```
```bash
gh repo clone carvalhojcastro-dotcom/concat-edicao-ao-vivo ~/Desktop/Concat/ferramentas
```
(Sem o `gh`: `git clone https://github.com/carvalhojcastro-dotcom/concat-edicao-ao-vivo.git ~/Desktop/Concat/ferramentas`.)

**2. Rodar o setup**, com o Concat fechado:
```bash
cd ~/Desktop/Concat/ferramentas && ./tools/setup.sh
```
Ele faz sozinho:
- instala ffmpeg, gh e o ambiente Python (transcrição, rosto, Higgsfield);
- baixa o **Concat deste fork** da Release do GitHub para `/Applications` (ou compila do código com
  `./tools/setup.sh --compilar`, ~10 min);
- **liga a API do Concat** (porta 7420) e grava o token em `.concat-token`;
- prepara as fontes: as livres já vêm no repositório, a Coolvetica é baixada do site oficial e as
  faces da Helvetica Neue são extraídas do macOS;
- cria `~/Desktop/Concat/editados`, `exportados` e o atalho `referencias`.

**3. Ligar o Higgsfield** (B-roll). A chave é digitada sem aparecer e fica em `.env.local`, fora do Git:
```bash
./tools/configurar_chave_higgsfield.sh
```

**4. Fonte Scholar.** É a única com licença própria que não dá para baixar automaticamente. Se o
setup avisou `FALTA fonts/Scholar-...`, copie `Scholar-Regular.otf` e `Scholar-Italic.otf` do Mac
antigo (`~/Desktop/Concat/ferramentas/fonts/`) para a mesma pasta no novo. Se o CapCut estiver
instalado e a Scholar já tiver sido usada nele, o setup a encontra sozinho.

**5. Usar.** Abra o Concat, abra o Claude Code na pasta `~/Desktop/Concat/ferramentas` e diga:
> edita esse vídeo: ~/Downloads/C5430.MP4 e salve como 13 - Título

## O que fica onde
| Onde | O quê |
|---|---|
| GitHub (este repositório) | código do Concat modificado (`src/`), ferramentas (`tools/`), estilo (`EDICAO.md`), skill (`.claude/skills/edicao-reels`), referências (`referencias/`), fontes livres, modelo de rosto |
| GitHub, aba Releases | o `Concat.app` já compilado (`Concat-<versão>-mac-arm64.zip`) |
| Só em cada Mac | `.env.local` (chave do Higgsfield), `.concat-token`, Scholar, Coolvetica, Helvetica Neue extraída, `tools/.venv`, projetos e vídeos |

## Publicar uma versão nova do Concat
Depois de mudar o código em `src/`:
```bash
./build-mac.sh && ./bundle-mac.sh && rm -rf /Applications/Concat.app && cp -R dist/Concat.app /Applications/
```
```bash
ditto -c -k --keepParent dist/Concat.app dist/Concat-0.2.7-fork.N-mac-arm64.zip
```
```bash
gh release create v0.2.7-fork.N dist/Concat-0.2.7-fork.N-mac-arm64.zip --repo carvalhojcastro-dotcom/concat-edicao-ao-vivo --title "Concat 0.2.7 fork N" --notes "O que mudou"
```
(troque `N` pelo próximo número).

## Se algo não abrir
- **"Concat está danificado" / não abre:** o app não é assinado pela Apple. Rode
  `xattr -dr com.apple.quarantine /Applications/Concat.app` (o setup já faz isso).
- **A API não responde:** feche o Concat, rode `./tools/setup.sh` de novo e abra o Concat.
