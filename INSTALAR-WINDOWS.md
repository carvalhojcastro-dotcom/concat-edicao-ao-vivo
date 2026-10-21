# Instalar no Windows

Monta num PC com Windows o mesmo editor do Mac: o Concat deste fork (com edição ao vivo pela API),
as ferramentas, as fontes, as referências e a skill que o Claude Code usa para editar.

**O jeito fácil:** abra o Claude Code (em qualquer pasta), cole o link deste repositório e diga
"instala isso". O Claude segue este arquivo. Você só faz duas coisas que ninguém pode fazer por você:
entrar na sua conta do GitHub e digitar a chave do Higgsfield.

## O que precisa antes
- Windows 10 ou 11, 64 bits; 16 GB de RAM e 30 GB livres (placa NVIDIA deixa a transcrição bem mais rápida).
- Acesso ao repositório privado (o dono convida a sua conta do GitHub como colaboradora).
- Claude Code instalado.
- A chave da API do Higgsfield (para o B-roll), que o dono passa por um canal seguro.

## Passo a passo (o que o Claude faz)
**1. Programas para baixar o repositório**, no PowerShell:
```powershell
winget install -e --id Git.Git --silent --accept-source-agreements --accept-package-agreements
```
```powershell
winget install -e --id GitHub.cli --silent --accept-source-agreements --accept-package-agreements
```
Depois, feche e abra o terminal (ou recarregue o PATH) para o `git` e o `gh` aparecerem.

**2. Entrar no GitHub** (a pessoa faz; no Claude Code, digitando com `!` na frente):
```powershell
gh auth login --web --git-protocol https
```

**3. Clonar na Área de Trabalho, dentro de `Concat\ferramentas`.** A Área de Trabalho pode estar no
OneDrive, então o caminho vem do Windows:
```powershell
$mesa = [Environment]::GetFolderPath("Desktop"); New-Item -ItemType Directory -Force "$mesa\Concat" | Out-Null
```
```powershell
gh repo clone carvalhojcastro-dotcom/concat-edicao-ao-vivo "$mesa\Concat\ferramentas"
```

**4. Rodar o setup**, de dentro de `Concat\ferramentas` (10 a 20 minutos na primeira vez):
```powershell
powershell -ExecutionPolicy Bypass -File tools\setup.ps1
```
Ele instala Python 3.11, FFmpeg e o ambiente das ferramentas; baixa a Coolvetica do site oficial e o
modelo de transcrição; instala o **Concat deste fork** da página Releases (sem pedir administrador);
liga a API do Concat e grava o token; cria `Concat\editados`, `Concat\exportados` e o atalho
`Concat\referencias`; e abre o Concat. Pode rodar de novo à vontade.

**5. Chave do Higgsfield** (a pessoa faz; a chave é digitada sem aparecer e nunca vai para o chat):
```powershell
powershell -ExecutionPolicy Bypass -File tools\configurar_chave_higgsfield.ps1
```

**6. Usar.** Com o Concat aberto, abra o Claude Code na pasta `Concat\ferramentas` e diga:
> edita esse vídeo: C:\Users\voce\Downloads\C5430.MP4 e salve como 13 - Título

As edições aparecem ao vivo no projeto aberto na janela do Concat.

## O que muda em relação ao Mac
O processo e o estilo são os mesmos; `tools/plataforma.py` troca só o que é do Mac:

| | Mac | Windows |
|---|---|---|
| Transcrição | mlx-whisper | faster-whisper, mesmo modelo large-v3-turbo (CUDA na placa NVIDIA) |
| Helvetica das legendas | Helvetica / Helvetica Neue do sistema | **Arimo** (OFL, mesmas medidas) |
| Helvetica Neue Condensed Black | extraída do macOS | **Archivo Condensed Black** (OFL) |
| HEVC / H.264 | VideoToolbox | NVENC, QSV, AMF ou x264/x265 |
| Python das ferramentas | `tools/.venv/bin/python` | `tools/.venv/Scripts/python.exe` |
| Setup | `./tools/setup.sh` | `tools\setup.ps1` |

Os scripts `.sh` de lote dos cortes de podcast (`tools/cortes_podcast/*.sh`) são do Mac (zsh). No
Windows, rode os passos Python deles um a um.

## Se algo não funcionar
- **"O Windows protegeu o computador"** ao abrir o Concat: o instalador não é assinado. Clique em
  **Mais informações › Executar assim mesmo**.
- **A API não responde (porta 7420):** feche o Concat e rode o `setup.ps1` de novo.
- **Nunca use "trocar de versão" nas Configurações do Concat:** isso instala o Concat oficial por cima
  e a edição ao vivo para de funcionar. Versões novas deste fork saem na página Releases.
