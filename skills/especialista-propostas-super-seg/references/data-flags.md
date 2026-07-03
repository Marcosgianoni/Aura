# Data Flags

These flags are surfaced after delivery, never before. They never block the proposal from being produced and sent. Deliver first, then report.

## Always flag
- Truncated or mismatched client emails.
- Placeholder contacts (for example A/C "Administração" used because no contact was provided).
- Expired or too-short validity windows (validity equal to or near the emission date).
- Third-party or off-site execution locations that differ from the registered address.
- Stale pricing.
- Ambiguous payment periodicities.
- Installment math inconsistencies.

## Never write into the proposal copy
Flags above are reported to the user AFTER delivery; they are never inserted into the proposal itself. In particular, the client's address must never appear in the proposal prose, including the lead/apresentação, the escopo description, the technical note (observação técnica), or any other field. This holds even when the orçamento carries an off-site or operational execution address that differs from the registered address: that case is flagged to the user after delivery (see "off-site execution locations" above), not written into the document. The proposal copy refers to the client by name only. Inserting the address bloats the layout and can push content off the page (for example clipping the emission/validity dates on page 1).

## Resubmission
When the user resends an orçamento with the same trigger phrase, diff it against the prior version to identify what changed. The user does not explain the changes verbally; detect them.

## Duplicate detection
If a resubmitted orçamento is identical to a prior one, confirm with the user before regenerating, rather than producing a duplicate silently.
