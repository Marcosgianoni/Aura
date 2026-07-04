# Business Rules

## Content fidelity
The proposal states only what the orçamento states, plus the fixed brand and template elements (headlines, clauses, CTAs, pillars). Never add commercial terms, contract durations, minimum-term or vigência clauses, guarantees, discounts, or any condition that is not written in the source orçamento. If the source does not mention it, it does not go in the proposal. The only exception is an explicit instruction from the user in the request itself (not inferred from the orçamento). When in doubt, leave it out and flag it after delivery.

## Page-2 headline by sector
Pick the headline that matches the client's sector:
- "quem cuida" for healthcare, clinics, pet care, beauty.
- "quem alimenta" for food, meat and frigorífico, restaurants.
- "quem constrói" for construction and engineering.
- "quem cultiva" for agribusiness and horticulture.
- "quem veste" for textile and confection.
- "quem move o Brasil" as the default (logistics, distribution, services, commerce, industry).

## Payment text
Apply the canonical 30-day NF/boleto text only when the source does not specify a different condition. If the orçamento specifies another payment model, preserve it exactly in substance and do not leave contradictory NF/boleto wording elsewhere in the proposal.

Canonical default, with bold on Nota Fiscal, 30 dias, 7 dias úteis, and 7 dias:

"Após a aprovação do orçamento, a Nota Fiscal será emitida juntamente com o boleto, com vencimento para 30 dias a contar da data de emissão. Realizado o levantamento das informações e/ou a visita técnica (se aplicável), o prazo de entrega dos documentos será de até 7 dias úteis. Mediante o envio dos documentos para validação, será considerado o prazo de até 7 dias para eventuais ajustes, sem cobrança adicional, caso necessário."

Examples of source-specific overrides:
- If the orçamento says "50% de entrada e 50% na conclusão dos serviços", use that as the page-3 payment condition.
- Update page-5 CTA support copy and approval-email body so they do not say "emissão da NF/boleto" or imply 30-day boleto when the source says otherwise.
- Keep the approval flow natural: "após aceite e confirmação da entrada" when the orçamento requires an entrada before activities/agendamentos.

## CTA fidelity
The page-5 CTA support copy is commercial guidance, but it must still follow source fidelity. Do not mention "agendamento da visita" unless the orçamento explicitly requires or implies a technical visit/agendamento. For ordinary document packages with only a delivery timeline, use a neutral CTA such as "Assim que recebermos seu aceite, daremos início à programação técnica e emissão da NF/boleto." For payment with entrada, use "Assim que recebermos seu aceite e a confirmação da entrada, daremos início à programação técnica e aos próximos encaminhamentos." Also update the mailto body to match the same payment/CTA logic.

## Field handling
- Validity equal to the emission date: extend about 7 days and flag.
- Missing A/C contact: use "Administração" as placeholder and flag.
- Contact name inferred from an email prefix: flag for confirmation.
- Truncated client email: reconstruct as .com.br and flag.
- Delivery timeline: 7 business days standard; use 10 days only if the source specifies.
- Cents in values: render as a large integer plus a styled superscript span. When the value is a round integer, show it without decimals (for example R$ 1.750).
- Client legal name: render in CAPS in the cover ficha.
- CNPJ: format as XX.XXX.XXX/XXXX-XX.
- If the source is an individual with CPF instead of CNPJ, use CPF consistently in the cover ficha, approval-email body, and any billing/fiscal wording. Do not render "CNPJ: CPF ..."; label it simply "CPF" and adapt generic terms such as "dados de faturamento" when needed.
- Validity: format as DD/MM/AAAA in the cover corner and the page-5 header.

## Trigger words
- "vai" or "fazer a proposta conforme o modelo": full autonomous execution.
- "deixar cada item especificado": use the detailed itemized layout variant.
- "inclua a informação do contrato mínimo de 12 meses": only then, because the user is explicitly adding it, include this term once (in the payment terms or the technical note). It is never inferred from the orçamento on its own.

## 4.0.0 additions
- Delivery deadlines come only from the orçamento (header field prevails over boilerplate when they conflict). Never import deadlines from any reference document.
- NRs and technical norms appear only when the orçamento cites them. Never add NR-15/NR-16 or any norm by inference.
- Cents are suppressed only when zero, mechanically by sub.py; campos.json carries numbers.
