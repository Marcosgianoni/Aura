# Deploy da Aura (skills)

Fonte canonica: este repositorio. A VPS e deploy-only, nunca editada.

## Fluxo de trabalho
1. No Mac: atualizar `skills/<skill>/` no clone local (arquivos vindos do chat).
2. `git diff` para revisar, depois commit e push na main.
3. Na VPS, como aura: `bash ~/Aura/deploy/deploy.sh`

O deploy.sh faz pull ff-only, imprime o VERSION, sincroniza com rsync
(--delete remove residuos, .venv preservada) e roda o smoke. Deploy so
esta pronto com "SMOKE OK". Rollback: `git checkout <commit>` no clone da
VPS e rodar o deploy.sh de novo.

## Smoke
`deploy/smoke.sh`: monta os 5 goldens e renderiza+valida o CBC no QA.
`SMOKE_FAST=1 bash deploy/smoke.sh` pula o render (so montagem).
