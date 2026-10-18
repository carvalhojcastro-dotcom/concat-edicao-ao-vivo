#!/usr/bin/env bash
# Compila o Concat (janela) para este Mac. Uso: ./build-mac.sh [check]
set -euo pipefail
export PATH="$(brew --prefix rustup)/bin:$HOME/.cargo/bin:$PATH"
export FFMPEG_DIR="$(brew --prefix ffmpeg)"
export LIBCLANG_PATH=/Library/Developer/CommandLineTools/usr/lib
cd "$(dirname "$0")/src"
if [ "${1:-}" = check ]; then
  cargo check -p concat -p concat-api
else
  cargo build --release -p concat
fi
