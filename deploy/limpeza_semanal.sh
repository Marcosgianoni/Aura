#!/usr/bin/env bash
# Limpeza semanal da VPS Aura: remove artefatos gerados com mais de RETENCAO_DIAS.
# Alvos: pastas de propostas, orcamentos do cache do WhatsApp e residuos de /tmp.
# Agendado via hermes cron (domingo 23:00 UTC, 20:00 Brasilia), modo no-agent.
# Retencao de 7 dias preserva a semana corrente para a regra de reenvio de
# duplicatas (4.1.6) funcionar sem regenerar.
# NOTA: o hermes cron exige o script em ~/.hermes/scripts/ e recusa symlink;
# apos alterar este arquivo e deployar, recopiar:
#   cp ~/Aura/deploy/limpeza_semanal.sh ~/.hermes/scripts/limpeza_semanal.sh
set -euo pipefail

[ "$(whoami)" = "aura" ] || { echo "ABORTADO: rodar como usuario aura (whoami=$(whoami))"; exit 1; }

RETENCAO_DIAS="${RETENCAO_DIAS:-7}"
LOG="$HOME/limpeza_semanal.log"

{
  echo "== limpeza semanal: $(date '+%Y-%m-%d %H:%M:%S') (retencao ${RETENCAO_DIAS}d) =="

  echo "-- propostas antigas em ~/propostas --"
  find "$HOME/propostas" -mindepth 1 -maxdepth 1 -type d -mtime +"$RETENCAO_DIAS" -print -exec rm -rf {} + 2>/dev/null || true

  echo "-- orcamentos antigos no cache do WhatsApp --"
  find "$HOME/.hermes/cache/documents" -maxdepth 1 -type f -mtime +"$RETENCAO_DIAS" -print -delete 2>/dev/null || true

  echo "-- residuos de runs em /tmp --"
  find /tmp -maxdepth 1 -user aura \( -name "aura-smoke" -o -name "hotfix*" -o -name "*.pdf" -o -name "base*.html" -o -name "campos_*.json" \) -mtime +"$RETENCAO_DIAS" -print -exec rm -rf {} + 2>/dev/null || true

  echo "-- espaco em disco --"
  df -h / | tail -1
  echo "== fim =="
  echo
} >> "$LOG" 2>&1

echo "Limpeza semanal Aura concluida ($(date '+%d/%m %H:%M UTC')). Detalhes em ~/limpeza_semanal.log"
