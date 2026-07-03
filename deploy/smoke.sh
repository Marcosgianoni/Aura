#!/usr/bin/env bash
# Smoke da skill Super Seg: monta os 5 goldens e renderiza+valida CBC e GD.
# Deploy so esta pronto quando isto passa. SMOKE_FAST=1 pula render/QA.
# 4.1.4: o golden da GD entrou no render+QA. Ele reproduz os dois defeitos do
# hotfix (capa longa que clipava o selo e pagamento de 4 linhas invadindo o
# rodape da pg3); validar so o CBC deixava essa classe de defeito passar.
# O grep do veredito virou exato: "APROVADO" solto tambem casa com REPROVADO.
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

for par in "campos_cbc_editorial:cbc" "campos_gd_tabela:gd"; do
  g="${par%%:*}"; n="${par##*:}"
  echo "== smoke: render + QA do golden $n =="
  "$PY" "$SS/scripts/render.py" "$OUT/$g.html" "$OUT/$n.pdf"
  "$PY" "$SS/scripts/qa.py" "$OUT/$n.pdf" "$OUT/${n}_qa" | tee "$OUT/qa_$n.log"
  grep -q "== RESULTADO: APROVADO ==" "$OUT/qa_$n.log"
done
echo "== SMOKE OK =="
