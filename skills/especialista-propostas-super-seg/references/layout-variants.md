# Layout Variants

Select the variant by service count and type. The base template ships the single-service variant; the others are scope-block fragments that replace the `.escopo-edit` region.

## Single service
Expanded scope block: large numeral, two-column inclusion list, observation note. This is the base template as shipped. Use for one service line (the common case).

## Multiple services (2 or more)
CSS grid table `.escopo-resumo` with columns: number, Serviço/Norma, Especificação, Qtd., Valor. For a small count, an itemized card grid is also acceptable. Number the services sequentially (01, 02, 03 ...). The trigger "deixar cada item especificado" forces this detailed and itemized layout even when it could fit a simpler one.

## Training proposals (NRs)
Training grid table with columns: number, Treinamento, NR, Modalidade/Data, Turma/Carga, Valor. Tag example: "NR-35 · Trabalho em Altura". Inclusion list mentions carga horária, certificado, instrutor habilitado.

## Exam batteries
Four-column table: Exame, Qtd., Vlr. unit., Subtotal, with a total row. Adapt Termo III (the exams clause) to the "exames inclusos" wording for these proposals.

## Recurring or monthly services
Show "Regime/Mensal" in the Qtd block. Display the monthly value as R$ N/mês with the annual total in the sublabel. Highlight the 12-month minimum contract in at least three to five locations across the document.

## Service-type tags and inclusion hints
- LTIP (Insalubridade e Periculosidade): tag "LTIP · NR-15 e NR-16"; inclusion: visita técnica, análise por número de colaboradores, ICP-Brasil; observation: análises quantitativas cobradas à parte.
- PCMSO: tag "PCMSO · NR-7"; inclusion: programa anual, ASOs, periódicos, demissionais.
- PGR/PPRA: tag "PGR · NR-1 e NR-9" (PGR replaced PPRA in 2022); inclusion: inventário de riscos, plano de ação, monitoramento.
- Training: tag per NR; inclusion: carga horária, certificado, instrutor habilitado.
- Other portfolio items follow the same editorial pattern: a normative tag, a short scope paragraph, an inclusion list, an optional technical note.

## Portfolio context
Super Seg covers compliance document packages (PGR/NR-01, PCMSO/NR-07, LTCAT, LTIP/NR-15/16, AET/NR-17), eSocial SST events (S-2210/2220/2230/2240), psychosocial risk programs, NR technical inspections (NR-13, NR-12), occupational training (NR-05/10/11/12/13/17/18/23/33/35), occupational exam batteries, and on-site technical monitoring.

## 4.0.0 editorial (servicos)
Page 3 of the `servicos` variant is the editorial per-item layout: section header `ESCOPO CONTRATADO · N ITENS` left and `TOTAL R$ ...` right, then one block per item (big green number, category eyebrow, serif title with a blue italic term, description with selective bolds, two-column checklist with green markers, and the item subtotal on the right under a `QTD. NN` label), followed by the technical note, the investment block, and the payment block. Driven entirely by `pagina3_editorial` in campos.json; fragment `templates/pg3_servicos_editorial.html`. Selection by item count (4.1.1): 1-4 items editorial, 5-7 items legacy table, 8+ report and stop. All bounds are hard asserts in sub.py (the table refuses 1-4, closing the route the agent took on Jose Norberto 36127). Discounts from the orçamento are first-class: `desconto` number field, rendered as a summary line, arithmetic-guarded in both formats (lesson from GD 36148). The old items table remains only as an internal fallback for legacy campos without the editorial block (collision fix: unit/sub columns widened to 21/23mm).
