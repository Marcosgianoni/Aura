---
name: especialista-propostas-super-seg
description: "Specialist build for Super Seg proposals. Invoked only by criador-de-proposta. Reads the Conta Azul orçamento, selects the right layout variant, applies the brand rules, fills the approved five-page A4 template, renders to PDF with overflow compaction, runs QA including a CTA visual check, and returns the output file paths plus data flags."
version: 4.1.3
author: Marcos + Hermes Agent
license: MIT
platforms: [macos, linux, windows]
metadata:
  hermes:
    tags: [proposals, budget, super-seg, handoff, pdf, html]
    related_skills: [proposal-routing-contract, criador-de-proposta]
---

# Especialista Propostas Super Seg

## Trigger
Run this skill only when `criador-de-proposta` invokes it explicitly, for example with `Use o agent especialista-propostas-super-seg`. The broad trigger words ("vai", "fazer a proposta conforme o modelo") are handled at the routing layer, which sends them to `criador-de-proposta`, which then invokes this skill. This is the only entry point.

## Execution model
You execute this workflow in the current agent. You may be a subagent delegated by `criador-de-proposta`, or running standalone. Either way:
- The absolute path of the orçamento is provided in your goal or context. Use it. Do not assume the file is in conversation.
- Do not delegate further. This is a leaf build.
- When delegated, do not message the user. Return the output file paths, a short status, and the data flags to the orchestrator. The orchestrator owns user-facing messaging.
- When standalone, you may emit a single short ack in Portuguese do Brasil and deliver the result yourself.

## Required setup
At the start of execution, export the bundle path and the venv interpreter. This is portable: `$HOME` resolves to the Hermes user's home (on the Aura that is `/home/aura`).
```
export SUPER_SEG_HOME="$HOME/.hermes/skills/software-development/especialista-propostas-super-seg/assets/super-seg"
export PY="$SUPER_SEG_HOME/.venv/bin/python3"
```
The renderer finds the fonts and logo relative to its own location even if `SUPER_SEG_HOME` is unset, but the script invocations below rely on `$SUPER_SEG_HOME` and `$PY`, so always export them first.

Bundle:
- Template and fragments: `assets/super-seg/templates/`
- Scripts: `assets/super-seg/scripts/` (`sub.py`, `render.py`, `qa.py`; all Python, Playwright/Chromium for render)
- Fonts: `assets/super-seg/fonts/` (embedded at render time; never depend on machine fonts or network `@import`)
- Logo: `assets/super-seg/logo_super_seg.png` (white background, embed as base64)
- References: see below.

## The Hermes line: judgment is LLM, mechanics are script
You (the LLM) do what needs judgment. The scripts do what must be deterministic. Do not script the judgment, and do not reason through the mechanics by hand. You never read the scripts (`sub.py`, `render.py`, `qa.py`) into context; you only run them via the commands below. Their internals are not your concern: loading them wastes context and degrades the run.

### LLM steps
1. Read the orçamento at the provided path. If it is a PDF, extract text and page count first. Extract every variable field: proposal number, issue date, validity, client legal name, CNPJ, A/C contact and email, technical-visit address, headcount, scope, inclusion items, total value, service count, payment terms.
2. Select the layout variant from the orçamento itself, not from a guess:
   - `single` (laudo): the orçamento is a single deliverable such as an LTIP/laudo. Uses the single-service block. This is the default.
   - `servicos`: the orçamento has an items table of distinct services (e.g. PPR, Fit Test, Treinamento), each with quantity and value. Page-3 presentation is selected by item count, mechanically enforced by sub.py: 1 to 4 items use the editorial per-item layout (supply the `pagina3_editorial` block); 5 to 7 items REQUIRED for the legacy items-table format, sub.py aborts outside that range (supply the legacy `itens` list with total_int, total_cent, escopo_tag, escopo_titulo, escopo_intro, escopo_descricao, escopo_nota, invest_sublabel; each item has servico, norma, especificacao, qtd, vlr_unit, subtotal as strings). With 8 or more priced items, stop and report instead of generating; never compress or merge items to force a fit. If the orçamento shows a discount line (Total, Descontos, Valor líquido), supply `desconto` as a NUMBER (editorial: inside pagina3_editorial; table: top level); sub.py renders the discount line mechanically and enforces sum minus discount equals total in BOTH formats. Never omit a discount that exists in the orçamento and never invent one.
   - `exames`: the orçamento is an occupational exam battery (Exame / Qtd / Vlr. unit. / Subtotal), in-company. Uses the exam table.
   If the orçamento lists two or more priced line items, it is `servicos` (or `exames` when the items are medical exams), never `single`. See `references/layout-variants.md`.
3. Apply the brand and business rules: page-2 sector headline, payment text from the orçamento when it differs from the canonical 30-day NF/boleto wording, validity and contact handling, cents formatting. See `references/business-rules.md`.
4. Do not build the page-3 HTML by hand and do not hand-edit the template. You supply structured data only; `sub.py` renders the page-3 escopo (single block or items table) and injects it. Preserve every fixed element exactly as the template has it: the page-1 headline "Sua empresa super segura, do laudo à entrega", the structure, typography, colors, slogan, social proof, pillars, the six page-4 clauses, the three page-5 CTA buttons, and the institutional links. Use the exact source values; never invent, round, or reword the client name, CNPJ, numbers, or totals. This extends to commercial terms: never add a contract duration, minimum-term or vigência clause, guarantee, discount, or any condition that is not written in the orçamento. If the source does not state it, it does not appear in the proposal. If the orçamento explicitly specifies a non-canonical payment condition (for example 50% entrada / 50% conclusão), preserve that condition in the page-3 payment block and update any page-5 CTA support copy or approval email wording that would otherwise contradict it. See `references/business-rules.md` (Content fidelity).
5. Write `campos.json`. Scalars for every variant: numero, cliente, cliente_caps, cliente_display, cnpj, ac_contato, ac_email, data_emissao, validade, validade_barra, valor_grande and valor_moeda (write them, but sub.py DERIVES both from the total and overwrites whatever you write, applying the cents rule), service_summary, service_summary_wa. Optional copy: lead_apresentacao (page-1 lead) and setor_verbo (page-2 "quem ___ o Brasil": move/alimenta/constrói/cultiva/cuida/veste). For `variante: "servicos"` also include escopo_intro and the `pagina3_editorial` block: `itens` (max 3; each with categoria, titulo, titulo_italico as an exact substring of titulo, qtd as a number, preco as a number carrying the item SUBTOTAL, optional preco_unitario when the orçamento prices per unit, descricao with selective `**bold**` marks, checklist with up to 4 short faithful entries), plus total (number), observacao_tecnica, investimento.subtitulo_itens, and forma_pagamento (origem "canonico", or "orcamento" with texto when the orçamento condition differs). All money fields are NUMBERS, never preformatted strings; `sub.py` owns all formatting and suppresses cents only when they are zero. `sub.py` builds the blocks, numbering, headers, quantity labels, and hrefs; do not hand-edit any of it. setor_verbo must be the verb only (e.g. "move"), never containing "Brasil": the template already closes the headline with "o Brasil." and sub.py aborts otherwise. The Google Calendar URL is never modified. Critically: numero is the proposal number exactly as printed (e.g. "35954"); never append the date, an index, or anything else to it. See `references/brand-constants.json` and `examples/campos_cbc_editorial.json` (editorial golden; `examples/campos_rogg_editorial.json` (3-item editorial) and `examples/campos_gd_tabela.json` (5-item legacy table with desconto) are the reference examples).

### Script steps
6. Substitute scalars and rebuild CTA hrefs: `"$PY" "$SUPER_SEG_HOME/scripts/sub.py" <template.html> campos.json base.html`. It is assert-guarded; if the template diverges it aborts instead of producing a wrong proposal. This replaces the old build_proposal.py, which is retired.
7. Render with compaction: `"$PY" "$SUPER_SEG_HOME/scripts/render.py" base.html SAIDA.pdf` (with `SUPER_SEG_HOME` set). It builds the offline render HTML with the bundle fonts and logo embedded as base64, injects page ids `pg1`..`pg5`, measures per-page overflow, applies scoped compaction CSS until all five pages fit, then renders the A4 PDF. It replaces render_proposal.mjs, which is retired. Fitting is render.py's job, not yours: write `campos.json` once from the source and render once. If the PDF still overflows after render.py's compaction, report it as a fit problem; never hand-trim the copy in `campos.json` and re-render in a loop. See `references/render-and-qa.md`.
8. Validate: `"$PY" "$SUPER_SEG_HOME/scripts/qa.py" SAIDA.pdf` (pypdf structural: five pages, A4 595x842pt, six link annotations; pypdfium2 rasterizes all five pages and footer crops for inspection).

### LLM close
9. Inspect the rendered page images. Beyond layout and overflow, check the page-2 media buttons and the page-5 CTAs specifically: every button and pill must show its brand color with no gray block behind or beside it. A gray offset block means the render did not embed fonts or a CSS shadow leaked; fail and report. Do not deliver.
10. Deliver, in one of two modes.
    Delegated (another agent requested the proposal): return the absolute paths of the HTML, PDF, and page-images directory, plus a short status and the data flags. Do not call send_message.
    Standalone (a person requested it via a chat platform such as WhatsApp): deliver by calling the send_message tool exactly once. The message argument has exactly two lines:
      Proposta <numero> pronta: <cliente_display>, <valor_moeda>.
      MEDIA:<absolute path to the PDF>
    The MEDIA tag only works inside the send_message tool call. Writing MEDIA: or bare file paths in your conversational reply sends raw text to the user, never an attachment. Attach only the PDF; the HTML stays on disk and is offered only if the user asks for it. No summary bullets, no file listings, no recommendations in the delivery message. If there are data flags (for example the orçamento validity date already expired at generation time), send them as one short sentence in a second message after the delivery. The caption value follows the cents rule (suppress ",00", keep real cents).

## Output contract
Always produce both files, named `Proposta_Super_Seg_[Cliente]_[Numero].html` and `Proposta_Super_Seg_[Cliente]_[Numero].pdf`. The PDF is the deliverable the seller sends; the HTML is the editable source with clickable buttons. Never deliver only one.

## Hard requirements
- Exactly five A4 pages.
- Use the approved template and the chosen variant only. Preserve the brand identity and the protected Google Calendar URL.
- Embed fonts and the logo at render time. Never rely on network `@import` or machine-installed fonts.
- Render only with `scripts/render.py` (Playwright/Chromium, fonts and logo embedded). Run QA before any delivery, including the CTA visual check.

## Prohibited fallbacks
Do not: summarize the orçamento instead of building the proposal; create DOCX, use ReportLab, or generate a Letter-size PDF; create a generic layout; create temporary render scripts or use any render path other than `scripts/render.py`; start Codex, run `codex exec`, hand the task to an external Codex/OpenAI agent, or modify `~/.codex` while processing a proposal. If a required asset or script is missing, stop and report an objective configuration error.

Never improvise around a missing variant. Specifically: do not rewrite the canonical headlines, the CTA labels, the pillar text, the clause text, or any other fixed copy; do not change the design, the colors, the fonts, or the button styling; do not hand-write or hand-edit the page-3 HTML or build the items table yourself in the HTML; do not concatenate or transform field values (the proposal number, dates, and totals are copied verbatim from the orçamento). If the orçamento is multi-item, use `variante: "servicos"` and put the items in `campos.json`; let `sub.py` render the table. If a variant truly does not exist for the orçamento at hand, stop and report it rather than reformatting or redesigning the proposal.

## Money in user-facing messages
In every message you write to the user (WhatsApp delivery, status, flags), format money with the same rule as the proposal: cents only when they are not zero. Write "Valor total: R$ 1.430", never "R$ 1.430,00". The authoritative formatted value is in campos.json as valor_moeda after sub.py runs.

## Data flags
Always surface after delivery, never block it. See `references/data-flags.md`.

## Revision and resubmission
When the user resends an orçamento with the same trigger, diff against the prior version to find what changed; the user does not explain changes verbally. If the resubmission is identical to a prior one, confirm before regenerating. The latest explicit human instruction is sovereign.
