# Prepara um PC com Windows 10/11 (64 bits) para editar reels com este fork. Passo a passo em
# INSTALAR-WINDOWS.md. Rode no PowerShell, da raiz do repositório:
#   powershell -ExecutionPolicy Bypass -File tools\setup.ps1
# Faz sozinho: Git, Python 3.11, FFmpeg e GitHub CLI (winget); ambiente Python (tools\.venv) com a
# transcrição (faster-whisper, na placa NVIDIA se houver); Coolvetica do site oficial; modelo do Whisper;
# Concat deste fork (instalador da Release do GitHub); API do Concat ligada com o token em .concat-token;
# pastas editados\, exportados\ e o atalho referencias\ ao lado do repositório. Pode rodar de novo à vontade.
param([switch]$SemConcat)
$ErrorActionPreference = "Stop"
$ProgressPreference = "SilentlyContinue"   # o Invoke-WebRequest fica 10x mais rápido sem a barra
$raiz = Split-Path -Parent $PSScriptRoot
Set-Location $raiz

function Tem($cmd) { [bool](Get-Command $cmd -ErrorAction SilentlyContinue) }
function RecarregarPath {
  $env:Path = [Environment]::GetEnvironmentVariable("Path", "Machine") + ";" + [Environment]::GetEnvironmentVariable("Path", "User")
}
function InstalarComWinget($id) {   # (não pode se chamar "Winget": o PowerShell ignora maiúsculas e ela chamaria a si mesma)
  winget install -e --id $id --silent --accept-source-agreements --accept-package-agreements | Out-Null
}

Write-Host "== Programas: Git, Python 3.11, FFmpeg, GitHub CLI (winget)"
if (-not (Tem winget)) { throw "Instale o 'App Installer' (winget) pela Microsoft Store e rode de novo." }
if (-not (Tem git))    { InstalarComWinget Git.Git }
if (-not (Tem py))     { InstalarComWinget Python.Python.3.11 }
if (-not (Tem ffmpeg)) { InstalarComWinget Gyan.FFmpeg }
if (-not (Tem gh))     { InstalarComWinget GitHub.cli }
RecarregarPath   # o winget só põe os programas novos no PATH de janelas novas
foreach ($c in @("git", "py", "ffmpeg", "gh")) {
  if (-not (Tem $c)) { throw "$c foi instalado mas não está no PATH: feche e abra o PowerShell e rode de novo." }
}

Write-Host "== Ambiente Python das ferramentas (tools\.venv)"
$py = Join-Path $raiz "tools\.venv\Scripts\python.exe"
if (-not (Test-Path $py)) { py -3.11 -m venv tools\.venv }
& $py -m pip install -q --upgrade pip
& $py -m pip install -q faster-whisper higgsfield-client python-dotenv pillow fonttools mediapipe "numpy<2.1"
# o mediapipe puxa o opencv 5, que tirou o detector de rosto do zoom: fica o contrib 4.x
# (no PowerShell 5.1, um comando que escreve no erro com "2>" vira exceção: aqui o erro não importa)
$ErrorActionPreference = "Continue"
& $py -m pip uninstall -y -q opencv-python-headless 2>$null | Out-Null
$ErrorActionPreference = "Stop"
& $py -m pip install -q --force-reinstall --no-deps "opencv-contrib-python<5"
if (Tem nvidia-smi) {
  Write-Host "  placa NVIDIA: bibliotecas CUDA para a transcrição"
  & $py -m pip install -q nvidia-cublas-cu12 "nvidia-cudnn-cu12==9.*"
}

Write-Host "== Fontes (fonts\)"
# As livres (Arimo, Archivo, DM Serif Display, Montserrat, Poppins...) já vêm no repositório.
# Coolvetica (Typodermic): grátis, mas sem redistribuir; baixa do site oficial, só os arquivos dela.
$fontes = Join-Path $raiz "fonts"
if (-not (Test-Path (Join-Path $fontes "Coolvetica-Rg.otf"))) {
  $pagina = (Invoke-WebRequest -UseBasicParsing "https://typodermicfonts.com/downloads/").Content
  $zipNome = [regex]::Match($pagina, 'typodermic-free-fonts-[^"/]*\.zip').Value
  if (-not $zipNome) { throw "Não achei o pacote grátis da Typodermic em typodermicfonts.com/downloads" }
  $tmp = Join-Path $env:TEMP "typodermic"
  Remove-Item $tmp -Recurse -Force -ErrorAction SilentlyContinue
  New-Item -ItemType Directory $tmp | Out-Null
  Invoke-WebRequest -UseBasicParsing "https://typodermicfonts.com/assets/downloads/$zipNome" -OutFile "$tmp\t.zip"
  Expand-Archive "$tmp\t.zip" "$tmp\x"
  $todos = Get-ChildItem "$tmp\x" -Recurse -File
  Copy-Item ($todos | Where-Object Name -eq "Coolvetica Rg.otf" | Select-Object -First 1).FullName (Join-Path $fontes "Coolvetica-Rg.otf")
  Copy-Item ($todos | Where-Object Name -eq "Coolvetica Rg It.otf" | Select-Object -First 1).FullName (Join-Path $fontes "Coolvetica-RgIt.otf")
  $eula = $todos | Where-Object Name -like "Typodermic*EULA*.pdf" | Select-Object -First 1
  if ($eula) { Copy-Item $eula.FullName (Join-Path $fontes "Coolvetica-EULA-Typodermic.pdf") }
  Remove-Item $tmp -Recurse -Force
  Write-Host "  Coolvetica baixada da Typodermic"
}

Write-Host "== Modelo do Whisper (baixa ~1,6 GB na primeira vez)"
& $py -c "import sys; sys.path.insert(0, 'tools'); import plataforma; from faster_whisper import WhisperModel; WhisperModel(plataforma.MODELO_CT2, device='cpu', compute_type='int8'); print('  ok')"

Write-Host "== Pastas de trabalho, ao lado do repositório"
$mae = Split-Path -Parent $raiz   # a pasta Concat: editados\, exportados\, referencias\ e este repositório
foreach ($d in @("editados", "exportados")) { New-Item -ItemType Directory -Force (Join-Path $mae $d) | Out-Null }
$ref = Join-Path $mae "referencias"
if (-not (Test-Path $ref)) { New-Item -ItemType Junction -Path $ref -Target (Join-Path $raiz "referencias") | Out-Null }
Write-Host "  $mae\{editados, exportados, referencias}"

function AcharConcat {
  foreach ($p in @("$env:LOCALAPPDATA\Programs\Concat\concat.exe", "$env:ProgramFiles\Concat\concat.exe")) {
    if (Test-Path $p) { return $p }
  }
  return $null
}

Write-Host "== Concat deste fork"
$exe = AcharConcat
if ($SemConcat) {
  Write-Host "  pulado (-SemConcat)"
} elseif ($exe) {
  Write-Host "  já instalado: $exe"
} else {
  $ErrorActionPreference = "Continue"
  gh auth status 2>$null | Out-Null
  $logado = ($LASTEXITCODE -eq 0)
  $ErrorActionPreference = "Stop"
  if (-not $logado) {
    throw "O GitHub CLI não está logado. Rode 'gh auth login' (no Claude Code: '! gh auth login'), entre com a conta que tem acesso ao repositório e rode o setup de novo."
  }
  $repo = (git remote get-url origin) -replace '\.git$', '' -replace '.*github\.com[:/]', ''
  $tmp = Join-Path $env:TEMP "concat-release"
  Remove-Item $tmp -Recurse -Force -ErrorAction SilentlyContinue
  gh release download --repo $repo --pattern "Concat-*-windows-x86_64-setup.exe" --dir $tmp
  if ($LASTEXITCODE -ne 0) { throw "Não consegui baixar o instalador do Concat da Release de $repo" }
  $instalador = Get-ChildItem $tmp -Filter "*.exe" | Select-Object -First 1
  # Inno Setup, só para esta conta (sem administrador), sem janelas
  Start-Process -Wait -FilePath $instalador.FullName -ArgumentList "/VERYSILENT", "/SUPPRESSMSGBOXES", "/NORESTART", "/CURRENTUSER"
  Remove-Item $tmp -Recurse -Force
  $exe = AcharConcat
  if (-not $exe) { throw "O instalador do Concat rodou, mas não achei o concat.exe" }
  Write-Host "  instalado: $exe"
}

Write-Host "== API do Concat (porta 7420) e .concat-token"
# Liga o servidor nas preferências do Concat e grava o mesmo token em .concat-token. Com o Concat
# aberto ele regravaria as preferências ao sair: só fecha o Concat se ainda precisar ligar.
& $py tools\ligar_api.py --checar
if ($LASTEXITCODE -eq 0) {
  Write-Host "  já ligada"
} else {
  Get-Process concat -ErrorAction SilentlyContinue | Stop-Process -Force
  Start-Sleep -Seconds 1
  & $py tools\ligar_api.py
}
if ($exe -and -not (Get-Process concat -ErrorAction SilentlyContinue)) { Start-Process -FilePath $exe; Write-Host "  Concat aberto" }

@"

== Pronto. Falta só (uma vez) a chave da API do Higgsfield, para o B-roll:
   powershell -ExecutionPolicy Bypass -File tools\configurar_chave_higgsfield.ps1
   (a chave é digitada sem aparecer e fica em .env.local, fora do Git; nunca a cole no chat)
Depois: com o Concat aberto, abra o Claude Code nesta pasta e diga "edita esse vídeo: <arquivo>".
"@ | Write-Host
