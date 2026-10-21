# Guarda a chave da API do Higgsfield em <repositório>\.env.local (HF_KEY=id:segredo).
# A chave é digitada sem aparecer na tela e nunca é mostrada; o arquivo é ignorado pelo Git.
$ErrorActionPreference = "Stop"
$envFile = Join-Path (Split-Path -Parent $PSScriptRoot) ".env.local"
$seguro = Read-Host "Cole a chave da API do Higgsfield (formato id:segredo) e tecle Enter" -AsSecureString
$chave = [Runtime.InteropServices.Marshal]::PtrToStringAuto([Runtime.InteropServices.Marshal]::SecureStringToBSTR($seguro))
if ($chave -notmatch ":") { throw "Formato inválido: precisa ser id:segredo." }
$linhas = @()
if (Test-Path $envFile) { $linhas = Get-Content $envFile | Where-Object { $_ -notmatch '^HF_KEY=' } }
$linhas += "HF_KEY=$chave"
# UTF-8 sem BOM (o Set-Content do PowerShell 5 põe BOM e a 1ª linha deixa de ser lida)
[IO.File]::WriteAllLines($envFile, [string[]]$linhas, (New-Object Text.UTF8Encoding($false)))
# só a conta do Windows que rodou o script lê o arquivo
icacls $envFile /inheritance:r /grant:r "$($env:USERNAME):(R,W)" | Out-Null
Write-Host "Chave salva em $envFile."
