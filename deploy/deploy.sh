#!/usr/bin/env bash
# Deploy da skill Super Seg a partir do repositorio Aura.
# Rodar NA VPS, como aura: bash ~/Aura/deploy/deploy.sh
# Portoes: git ff-only (historico integro), VERSION impresso, smoke obrigatorio.
set -euo pipefail

SKILL="especialista-propostas-super-seg"
REPO_DIR="${REPO_DIR:-$HOME/Aura}"
DEST="$HOME/.hermes/skills/software-development/$SKILL"

cd "$REPO_DIR"
git pull --ff-only origin main
COMMIT="$(git rev-parse --short=12 HEAD)"
echo "== Aura deploy: commit $COMMIT =="
head -2 "skills/$SKILL/VERSION"

# rsync com --delete remove arquivos que sairam do bundle (fim dos residuos
# do unzip -o); .venv e preservada pelo exclude.
rsync -a --delete --exclude='.venv/' "skills/$SKILL/" "$DEST/"
echo "== sync ok -> $DEST =="

bash "$REPO_DIR/deploy/smoke.sh"
echo "== DEPLOY OK: commit $COMMIT =="
