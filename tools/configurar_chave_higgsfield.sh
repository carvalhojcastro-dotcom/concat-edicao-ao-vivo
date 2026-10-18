#!/usr/bin/env bash
# Guarda a chave da API do Higgsfield em ~/Developer/Concat/.env.local (HF_KEY=id:segredo).
# A chave é digitada sem aparecer na tela e nunca é mostrada; o arquivo é ignorado pelo Git.
set -euo pipefail
env_file="$(cd "$(dirname "$0")/.." && pwd)/.env.local"
printf 'Cole a chave da API do Higgsfield (formato id:segredo) e tecle Enter: '
IFS= read -rs chave; echo
case "$chave" in *:*) ;; *) echo "Formato inválido: precisa ser id:segredo." >&2; exit 1 ;; esac
umask 077
tmp="$(mktemp)"
[ -f "$env_file" ] && grep -v '^HF_KEY=' "$env_file" > "$tmp" || true
printf 'HF_KEY=%s\n' "$chave" >> "$tmp"
mv "$tmp" "$env_file"; chmod 600 "$env_file"
echo "Chave salva em $env_file."
