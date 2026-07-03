# Render and QA

The render and QA are deterministic scripts. The agent calls them; it does not reason through them.

## Substitution (`scripts/sub.py`)
Fills the scalar fields and rebuilds the CTA hrefs.
- Input: the master template, a `campos.json` with the proposal data, and the output path.
- `python3 sub.py <template.html> <campos.json> <base.html>`.
- It uses `rep()` with exact occurrence asserts: if the template diverges, it aborts loudly instead of producing a wrong proposal.
- It rebuilds the mailto and WhatsApp hrefs from `campos.json`, so the client name, CNPJ, and value inside the approval buttons are always correct. The Google Calendar href is never touched.
- `campos.json` fields: numero, cliente, cliente_caps, cliente_display, cnpj, ac_contato, ac_email, data_emissao, validade, validade_barra, valor_grande, valor_moeda, service_summary, service_summary_wa.
- The scope region (service tag, description, inclusion list, observation) is layout-specific and is filled by the agent before substitution, per `layout-variants.md`. `sub.py` owns the scalars and the hrefs, not the scope.

## Render with compaction (`scripts/render.py`)
Builds the offline render HTML and renders the A4 PDF.
- `python3 render.py <base.html> <saida.pdf>`. Requires `SUPER_SEG_HOME` set to the bundle root.
- It removes the Google Fonts `@import` and injects `@font-face` with the bundle fonts embedded as base64. Never depend on machine fonts or on network at render time.
- Fonts: to keep the same output as today, the bundle ships Lora aliased as Fraunces and Poppins aliased as Manrope, in `$SUPER_SEG_HOME/fonts`. Required files: Lora-Variable.ttf, Lora-Italic-Variable.ttf, Poppins-Light.ttf, Poppins-Regular.ttf, Poppins-Medium.ttf, Poppins-Bold.ttf.
- Logo: embedded as base64 with the MIME detected from the file bytes (the current `logo_super_seg.png` is a real PNG, so it embeds as image/png).
- It injects ids `pg1`..`pg5` on the five pages. Layout model (D1): header and footer are a FIXED frame (the footer is absolutely positioned 12mm from the bottom on every internal page); only the content between them is elastic. The script measures where each internal page's CONTENT ends (capa excluded) and requires a minimum gap to the footer top; if content invades the footer band, it applies scoped compaction CSS per page id, iteratively, until all pages fit.
- Render call: Chromium, `goto`/`set_content` with `wait_until="networkidle"`, then `document.fonts.ready`, then a 1800ms wait, then `page.pdf` with A4, zero margins, `print_background`, `prefer_css_page_size`.
- The compaction ramps are intentionally conservative. Calibrate them per layout against the real overflow of each variant.
- Chromium path: Playwright's own browser by default; set `CHROMIUM_PATH` to override.

## QA (`scripts/qa.py`)
Validates the PDF and rasterizes pages for inspection.
- `python3 qa.py <saida.pdf>`.
- Structural (pypdf): exactly five pages; each A4 portrait at 595x842pt with a 2pt tolerance; six link annotations (three institutional on page 2 plus three buttons on page 5).
- Structural guards (pypdf/pypdfium2): pagination "0X / 05" must be extractable from pages 2 to 5 (a clipped footer fails), and the bottom 50pt band of pages 2 to 5 must contain no lowercase text (content overlapping the fixed footer fails). Both are hard failures (exit 1).
- Visual (pypdfium2): rasterizes all five pages and footer crops at scale 2.0. Page 2 (media buttons) and page 5 (CTAs) are rasterized so the agent can check for a gray block behind any button. A gray offset block means the render did not embed fonts or a CSS shadow leaked.

## Known gotchas
- Offline fonts (Lora, Poppins) render measurably taller than the Google Fonts CDN versions, so expect overflow and rely on the compaction pass.
- A CSS comment containing the literal string `</style>` will prematurely close the style block and silently drop all later rules. Never put `</style>` inside a comment.
- The template ships with the button shadows set to none, which removes the gray-block class of problem at the source regardless of the render engine.
