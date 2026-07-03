#!/usr/bin/env bash
# Smoke da skill Super Seg: monta os 5 goldens e renderiza+valida o CBC.
# Deploy so esta pronto quando isto passa. SMOKE_FAST=1 pula render/QA.
set -euo pipefail

SKILL="especialista-propostas-super-seg"
SS="$HOME/.hermes/skills/software-development/$SKILL/assets/super-seg"
PY="$SS/.venv/bin/python3"; [ -x "$PY" ] || PY=python3
OUT=/tmp/aura-smoke; mkdir -p "$OUT"

echo "== smoke: montagem dos 5 goldens =="
for g in campos_exemplo campos_cbc_editorial campos_rogg_editorial \
         campos_gd_tabela campos_teste_editorial_4itens; do
  "$PY" "$SS/scripts/sub.py" \
    "$SS/templates/template_proposta_super_seg.html" \
    "$SS/examples/$g.json" "$OUT/$g.html"
done

if [ "${SMOKE_FAST:-0}" = "1" ]; then
  echo "== SMOKE OK (FAST: render/QA pulados) =="; exit 0
fi

echo "== smoke: render + QA do golden CBC =="
"$PY" "$SS/scripts/render.py" "$OUT/campos_cbc_editorial.html" "$OUT/cbc.pdf"
"$PY" "$SS/scripts/qa.py" "$OUT/cbc.pdf" "$OUT/cbc_qa" | tee "$OUT/qa.log"
grep -q "APROVADO" "$OUT/qa.log"
echo "== SMOKE OK =="
