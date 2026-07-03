#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
render.py (bundle) :: gera render.html offline a partir do base.html, mede
overflow por pagina, aplica compactacao escopada por id e renderiza o PDF A4.

Caminhos por ambiente, nada hardcoded:
  SUPER_SEG_HOME  -> raiz do bundle (fontes em $SUPER_SEG_HOME/fonts, logo em
                     $SUPER_SEG_HOME/logo_super_seg.png)
  CHROMIUM_PATH   -> opcional; se ausente, usa o Chromium do proprio Playwright

Uso:
  python3 render.py <base.html> <saida.pdf> [render.html]

Fontes embutidas (mantem o mesmo padrao do Project): Lora apelidada de
'Fraunces', Poppins apelidada de 'Manrope'. Os .ttf viajam no bundle, em
$SUPER_SEG_HOME/fonts, para a saida ser identica em qualquer maquina.

Historico 4.1.4:
  - A CAPA entrou na medicao de encaixe. Antes ficava fora por decisao de
    projeto ("bloco de datas senta perto da borda por design"), premissa que
    quebrou na proposta GD 36148: nome de cliente em 3 linhas + lead de 4
    linhas empurraram o bloco de datas e o selo para fora da pagina (o
    overflow:hidden da .page clipa em silencio). O template agora ancora o
    .capa-bottom na base (absoluto) e o render mede o miolo da capa contra o
    topo desse bloco, com levers proprios (titulo, subtitulo, slogan, ficha).
  - O bloco .pagamento-edit ganhou levers. Era o unico bloco da pagina 3 sem
    nenhum lever: quando o proprio pagamento era o invasor (texto de 4 linhas
    na GD 36148), a compactacao apertava todo o resto menos o culpado.
"""

import base64
import os
import re
import sys
from pathlib import Path

from playwright.sync_api import sync_playwright

HOME = Path(os.environ.get("SUPER_SEG_HOME") or Path(__file__).resolve().parents[1]).resolve()
FONT_DIR = HOME / "fonts"
LOGO_SRC = HOME / "logo_super_seg.png"
CHROMIUM_PATH = os.environ.get("CHROMIUM_PATH")  # opcional

# Arquitetura D1: moldura fixa, miolo elastico. O header e o primeiro elemento da
# pagina (posicao constante) e o rodape e ABSOLUTO a 12mm da borda em todas as
# paginas internas; nenhum dos dois se move com o conteudo. O que varia e o miolo.
# A medicao de overflow, portanto, nao olha mais onde o rodape parou (ele nao anda):
# ela mede onde o CONTEUDO termina e exige uma folga minima ate o topo do rodape.
# Se o conteudo invadir a faixa, a compactacao aperta o miolo daquela pagina.
# Na capa (4.1.4) a mesma logica vale contra o .capa-bottom, tambem ancorado.
GAP_MIN_PX = 8  # folga minima (px ~2mm) entre o fim do conteudo e o topo do rodape
RESIDUO_TOL_PX = 16  # excesso residual de caixa tolerado apos compactacao maxima
MAX_ITER = 8

# IMPORTANTE: usar sempre .ttf ESTATICOS aqui. Fonte variavel (tabela fvar) faz o
# Chromium rasterizar a serifada para Type 3 no print-to-PDF, o que quebra o
# espacamento do texto (ex.: "Program a de Gerenciam ento"). As Lora abaixo sao
# instancias estaticas (wght=400) geradas das variaveis originais.
FONT_FACES = [
    ("Fraunces", 400, False, "Lora-Regular.ttf"),
    ("Fraunces", 400, True,  "Lora-Italic.ttf"),
    ("Manrope",  300, False, "Poppins-Light.ttf"),
    ("Manrope",  400, False, "Poppins-Regular.ttf"),
    ("Manrope",  500, False, "Poppins-Medium.ttf"),
    ("Manrope",  700, False, "Poppins-Bold.ttf"),
]


def b64(path: Path) -> str:
    return base64.b64encode(path.read_bytes()).decode("ascii")


def logo_data_uri(path: Path) -> str:
    raw = path.read_bytes()
    if raw[:8].startswith(b"\x89PNG"):
        mime = "image/png"
    elif raw[:3] == b"\xff\xd8\xff":
        mime = "image/jpeg"
    else:
        mime = "image/png"
    return f"data:{mime};base64," + base64.b64encode(raw).decode("ascii")


def build_font_face_css() -> str:
    blocks = []
    for fam, weight, italic, fname in FONT_FACES:
        path = FONT_DIR / fname
        if not path.exists():
            sys.exit(f"Fonte ausente no bundle: {path}")
        style = "italic" if italic else "normal"
        blocks.append(
            f"@font-face{{font-family:'{fam}';font-style:{style};"
            f"font-weight:{weight};font-display:swap;"
            f"src:url(data:font/ttf;base64,{b64(path)}) format('truetype');}}"
        )
    return "\n".join(blocks)


def make_render_html(base_html: Path, render_html: Path) -> None:
    html = base_html.read_text(encoding="utf-8")

    html, n = re.subn(r"@import url\([^)]*\);", "", html, count=1)
    assert n == 1, f"esperava 1 @import, removi {n}"

    face_css = build_font_face_css()
    html, n = re.subn(r"(<style>)", r"\1\n" + face_css + "\n", html, count=1)
    assert n == 1, "nao achei <style> para injetar @font-face"

    if not LOGO_SRC.exists():
        sys.exit(f"Logo ausente no bundle: {LOGO_SRC}")
    html = html.replace("logo_super_seg.png", logo_data_uri(LOGO_SRC))

    idx = {"i": 0}
    def add_id(m):
        idx["i"] += 1
        return f'{m.group(0)} id="pg{idx["i"]}"'
    html = re.sub(r'<div class="page[^"]*"', add_id, html)
    assert idx["i"] == 5, f"esperava 5 paginas, marquei {idx['i']}"

    render_html.write_text(html, encoding="utf-8")


def _ramp(start: float, floor: float, per: float, level: int) -> float:
    # encolhe 'start' em 'per' por nivel, com piso em 'floor'.
    v = start - per * level
    return round(floor if v < floor else v, 3)


def compaction_css(pg_id: str, level: int) -> str:
    # Levers escopados por id. Os valores de partida sao os reais do template;
    # os pisos sao folgas seguras (proximas do padrao que o Project entrega).
    # Capa (1): titulo, subtitulo, slogan e ficha do cliente (4.1.4).
    # Paginas internas (2 a 4): texto, pilares, termos, itens de escopo.
    # Pagina de CTA (5): caixas dos botoes, titulo, contato e principios, que
    # eram justamente o que nao encolhia antes.
    # NOTA: col-espec e escopo-servicos-nota tem font-size FIXO em 8pt (fora da
    # rampa). Abaixo de 8pt o Poppins quebra o espacamento no PDF do Chromium
    # (ex.: "Program a de Gerenciam ento"). A compactacao da pagina 3 e absorvida
    # por espacamento (paddings/line-height) e pelos tamanhos do cabecalho do escopo.
    # Pisos aprofundados na 3.3.0: com o rodape fixo, o miolo util encolheu ~13mm
    # e a pagina 2 (a mais cheia) precisa de mais curso de compactacao para caber.
    # 4.1.4: levers novos da capa (escopados pelas classes capa-*, so existem na
    # pg1) e do pagamento-edit (font com piso 8pt pelo limite do Poppins).
    L = level
    return f"""
    #{pg_id} .secao-cabecalho {{ margin-top:{_ramp(10,2.5,1.4,L)}mm; margin-bottom:{_ramp(7,2,0.9,L)}mm; }}
    #{pg_id} .cab-escopo {{ margin-top:{_ramp(7,2.5,0.9,L)}mm; margin-bottom:{_ramp(5,2,0.6,L)}mm; }}
    #{pg_id} .lead-pequeno {{ line-height:{_ramp(1.55,1.28,0.05,L)}; }}
    #{pg_id} .escopo-incluso-edit li {{ padding-top:{_ramp(4,2,0.6,L)}pt; padding-bottom:{_ramp(4,2,0.6,L)}pt; }}
    #{pg_id} .escopo-servicos {{ padding-top:{_ramp(4,1.5,0.6,L)}mm; }}
    #{pg_id} .escopo-servicos-header {{ padding-bottom:{_ramp(3,1,0.5,L)}mm; }}
    #{pg_id} .escopo-servicos-header .escopo-edit-numero {{ font-size:{_ramp(30,20,2.5,L)}pt; }}
    #{pg_id} .escopo-servicos-header .escopo-edit-titulo {{ font-size:{_ramp(18,14,1,L)}pt; }}
    #{pg_id} .escopo-servicos-header .escopo-edit-qtd .qtd-num {{ font-size:{_ramp(22,16,1.5,L)}pt; }}
    #{pg_id} .escopo-servicos-intro {{ margin-bottom:{_ramp(3,1,0.5,L)}mm; padding-top:{_ramp(2.5,1,0.4,L)}mm; line-height:{_ramp(1.45,1.25,0.05,L)}; }}
    #{pg_id} .tabela-servicos tbody td {{ padding-top:{_ramp(4,1.5,0.6,L)}pt; padding-bottom:{_ramp(4,1.5,0.6,L)}pt; }}
    #{pg_id} .tabela-servicos .col-espec {{ font-size:8pt; line-height:{_ramp(1.32,1.18,0.04,L)}; }}
    #{pg_id} .tabela-servicos .col-servico .serv-nome {{ font-size:{_ramp(9.5,8.5,0.25,L)}pt; }}
    #{pg_id} .escopo-servicos-nota {{ padding-top:{_ramp(3,1,0.5,L)}mm; padding-bottom:{_ramp(3,1,0.5,L)}mm; line-height:{_ramp(1.5,1.28,0.05,L)}; font-size:8pt; }}
    #{pg_id} .ed-item {{ padding-top:{_ramp(3.5,1.2,0.5,L)}mm; padding-bottom:{_ramp(3.5,1.2,0.5,L)}mm; }}
    #{pg_id} .ed-num {{ font-size:{_ramp(24,17,1.5,L)}pt; }}
    #{pg_id} .ed-titulo {{ font-size:{_ramp(13,10.5,0.5,L)}pt; margin-bottom:{_ramp(1.6,0.8,0.2,L)}mm; }}
    #{pg_id} .ed-preco {{ font-size:{_ramp(16,12,0.8,L)}pt; }}
    #{pg_id} .ed-desc {{ font-size:{_ramp(8.5,8,0.15,L)}pt; line-height:{_ramp(1.45,1.25,0.05,L)}; margin-bottom:{_ramp(1.8,0.8,0.25,L)}mm; }}
    #{pg_id} .ed-check li {{ font-size:8pt; line-height:{_ramp(1.3,1.15,0.04,L)}; padding-top:{_ramp(0.5,0.1,0.1,L)}mm; padding-bottom:{_ramp(0.5,0.1,0.1,L)}mm; }}
    #{pg_id} .ed-header-escopo {{ padding-bottom:{_ramp(2.5,1,0.4,L)}mm; }}
    #{pg_id} .ed-nota {{ padding-top:{_ramp(2.5,1,0.4,L)}mm; padding-bottom:{_ramp(2.5,1,0.4,L)}mm; margin-top:{_ramp(2.5,1,0.4,L)}mm; line-height:{_ramp(1.45,1.25,0.05,L)}; font-size:8pt; }}
    #{pg_id} .termo-edit {{ padding-top:{_ramp(3.5,1.4,0.5,L)}mm; padding-bottom:{_ramp(3.5,1.4,0.5,L)}mm; }}
    #{pg_id} .pilar {{ padding-top:{_ramp(3.5,1.2,0.5,L)}mm; padding-bottom:{_ramp(3.5,1.2,0.5,L)}mm; }}
    #{pg_id} .stats-editorial, #{pg_id} .midia-editorial {{ margin-top:{_ramp(5,1,0.8,L)}mm; }}
    #{pg_id} .btn-edit {{ padding-top:{_ramp(6,3,0.8,L)}mm; padding-bottom:{_ramp(6,3,0.8,L)}mm; }}
    #{pg_id} .cta-titulo-bloco {{ margin-bottom:{_ramp(12,6,1.6,L)}mm; }}
    #{pg_id} .cta-titulo-edit {{ margin-bottom:{_ramp(6,3,0.8,L)}mm; }}
    #{pg_id} .cta-sub-edit {{ line-height:{_ramp(1.5,1.32,0.05,L)}; }}
    #{pg_id} .contato-edit {{ margin-top:{_ramp(10,5,1.3,L)}mm; padding-top:{_ramp(6,3,0.8,L)}mm; }}
    #{pg_id} .slogan-manifesto {{ margin-top:{_ramp(10,4,1.5,L)}mm; padding-top:{_ramp(6,3,0.8,L)}mm; }}
    #{pg_id} .capa-titulo {{ font-size:{_ramp(62,50,1.8,L)}pt; margin-bottom:{_ramp(10,4,0.9,L)}mm; }}
    #{pg_id} .capa-conteudo {{ padding-top:{_ramp(6,1,0.7,L)}mm; padding-bottom:{_ramp(6,1,0.7,L)}mm; }}
    #{pg_id} .capa-subtitulo {{ font-size:{_ramp(11.5,9.5,0.3,L)}pt; line-height:{_ramp(1.55,1.3,0.04,L)}; }}
    #{pg_id} .capa-slogan {{ margin-top:{_ramp(8,3,0.7,L)}mm; padding-top:{_ramp(6,2.5,0.5,L)}mm; }}
    #{pg_id} .ficha-cliente {{ padding-top:{_ramp(8,3.5,0.6,L)}mm; padding-bottom:{_ramp(8,3.5,0.6,L)}mm; }}
    #{pg_id} .pagamento-edit {{ margin-top:{_ramp(4,1.5,0.4,L)}mm; padding-top:{_ramp(3,1,0.3,L)}mm; }}
    #{pg_id} .pagamento-edit p {{ font-size:{_ramp(9,8,0.15,L)}pt; line-height:{_ramp(1.55,1.3,0.04,L)}; }}
    """


def measure_overflow(page):
    # Modelo D1: o rodape e fixo (absoluto, 12mm da borda) e nao anda. Medimos onde
    # o CONTEUDO de cada pagina termina (maior bottom entre os filhos da pagina,
    # exceto o proprio elemento-limite) e comparamos com o topo do limite. Se o
    # conteudo chegar a menos de GAP_MIN_PX do limite, esta invadindo a faixa e a
    # pagina precisa de compactacao. Retorna (pagina, px de invasao alem da folga).
    # 4.1.4: a capa (pg1) ENTROU na medicao. O limite dela e o .capa-bottom
    # (bloco de datas + selo), agora ancorado na base pelo template. A decisao
    # antiga de deixar a capa fora quebrou na GD 36148 (selo clipado para fora
    # da pagina). Paginas 2 a 5 seguem medindo contra o .footer-edit.
    invasoes = page.evaluate(f"""() => {{
        const out = [];
        const GAP = {GAP_MIN_PX};
        const medir = (pg, nome, seletorLimite) => {{
            const top = pg.getBoundingClientRect().top;
            const limite = pg.querySelector(seletorLimite);
            if (!limite) return;
            const limiteTop = limite.getBoundingClientRect().top - top;
            let contentBottom = 0;
            for (const el of pg.children) {{
                if (el === limite) continue;
                const b = el.getBoundingClientRect().bottom - top;
                if (b > contentBottom) contentBottom = b;
            }}
            const excesso = Math.round(contentBottom - (limiteTop - GAP));
            if (excesso > 0) out.push([nome, excesso]);
        }};
        const capa = document.getElementById('pg1');
        if (capa) medir(capa, 'pg1', '.capa-bottom');
        for (let i = 2; i <= 5; i++) {{
            const pg = document.getElementById('pg' + i);
            if (pg) medir(pg, 'pg' + i, '.footer-edit');
        }}
        return out;
    }}""")
    return [(pg, e) for pg, e in invasoes]


def render(base_html: Path, out_pdf: Path, render_html: Path) -> None:
    make_render_html(base_html, render_html)
    levels: dict[str, int] = {}  # nivel por pagina, so aumenta (evita oscilacao)

    launch_kwargs = {"args": ["--no-sandbox", "--disable-dev-shm-usage"]}
    if CHROMIUM_PATH:
        launch_kwargs["executable_path"] = CHROMIUM_PATH

    base = render_html.read_text(encoding="utf-8")

    with sync_playwright() as p:
        browser = p.chromium.launch(**launch_kwargs)
        page = browser.new_page()

        for it in range(MAX_ITER + 1):
            extra_css = "".join(
                compaction_css(pg, lv) for pg, lv in sorted(levels.items()) if lv > 0
            )
            html = base.replace("</style>", extra_css + "\n</style>", 1) if extra_css else base
            page.set_content(html, wait_until="networkidle")
            page.evaluate("document.fonts.ready")
            page.wait_for_timeout(1800)

            cortando = measure_overflow(page)
            if not cortando:
                print(f"[iter {it}] todas as paginas cabem (conteudo fora da faixa do rodape).")
                break
            print(f"[iter {it}] conteudo invadindo a faixa do rodape (px de excesso): {cortando}")
            for pg, _ in cortando:
                levels[pg] = min(levels.get(pg, 0) + 1, MAX_ITER)
        else:
            # A medicao usa bounding box (inclui padding e borda alem do texto),
            # entao um excesso residual pequeno apos compactacao maxima costuma
            # ser caixa, nao tinta visivel. Quem da o veredito de sobreposicao
            # real e o qa.py (guarda de encaixe por charbox, medido pelo fundo
            # do caractere desde a 4.1.4).
            residuo = max((e for _, e in cortando), default=0)
            if residuo <= RESIDUO_TOL_PX:
                print(f"obs: paginas no limite apos compactacao maxima (excesso de caixa <= {RESIDUO_TOL_PX}px): {cortando}; o QA decide.")
            else:
                print(f"AVISO: atingiu MAX_ITER com conteudo ainda invadindo o rodape: {cortando}; revisar manualmente.")

        out_pdf.parent.mkdir(parents=True, exist_ok=True)
        page.pdf(
            path=str(out_pdf),
            format="A4",
            margin={"top": "0", "right": "0", "bottom": "0", "left": "0"},
            print_background=True,
            prefer_css_page_size=True,
        )
        browser.close()
    print(f"PDF -> {out_pdf}")


def main() -> None:
    if len(sys.argv) < 3:
        sys.exit("uso: python3 render.py <base.html> <saida.pdf> [render.html]")
    base_html = Path(sys.argv[1])
    out_pdf = Path(sys.argv[2])
    render_html = Path(sys.argv[3]) if len(sys.argv) > 3 else base_html.with_name("render.html")
    if not base_html.exists():
        sys.exit(f"base.html nao encontrado: {base_html} (rode sub.py antes)")
    render(base_html, out_pdf, render_html)


if __name__ == "__main__":
    main()
