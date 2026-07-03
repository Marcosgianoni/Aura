#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
qa.py (bundle) — QA do PDF gerado.

Estrutural (pypdf):
  - exatamente 5 paginas
  - cada pagina A4 retrato (595 x 842 pt, tolerancia +-2pt)
  - 6 anotacoes de link (3 institucionais na pag. 2 + 3 botoes na pag. 5)
  - paginacao "0X / 05" presente no texto das paginas 2 a 5 (rodape nao clipado)
  - faixa do rodape (ultimos 50pt) sem texto minusculo nas paginas 2 a 5
    (conteudo sobrepondo o rodape fixo = reprovado)

Visual (pypdfium2):
  - rasteriza as 5 paginas inteiras e os crops de rodape
  - importante: a pag. 2 (botoes de midia) e a pag. 5 (CTAs) sao rasterizadas
    para a inspecao do bloco cinza atras dos botoes
  - salva PNGs no diretorio de QA para inspecao

Uso:
  python3 qa.py <caminho_do_pdf> [dir_qa]
"""

import re
import sys
from pathlib import Path

from pypdf import PdfReader
import pypdfium2 as pdfium

A4_W, A4_H = 595, 842
DIM_TOL = 2
ESPERA_PAGINAS = 5
ESPERA_LINKS = 6
SCALE = 2.0
FOOTER_FRAC = 0.12

PAGINAS = {0: "capa", 1: "pg2", 2: "pg3", 3: "pg4", 4: "pg5"}


def qa_rodapes(reader: PdfReader) -> bool:
    # O rodape das paginas internas (2 a 5) contem a paginacao "0X / 05".
    # Se o conteudo empurrar o rodape para fora da pagina (overflow clipado),
    # esse texto some do PDF e a checagem reprova. E o guarda-costas
    # deterministico contra rodape clipado, que a inspecao visual nao pega
    # (um rodape ausente nao parece "cortado", so nao esta la).
    ok = True
    for i in range(2, ESPERA_PAGINAS + 1):
        txt = reader.pages[i - 1].extract_text() or ""
        achou = re.search(rf"{i:02d}\s*/\s*0\s*{ESPERA_PAGINAS}", txt) is not None
        print(f"  rodape pg{i} ('{i:02d} / 05'): {'OK' if achou else 'FALHA (rodape ausente ou clipado)'}")
        ok &= achou
    return ok


BANDA_RODAPE_PT = 50  # faixa inferior da pagina (pt, de baixo para cima) reservada ao rodape


def qa_faixa_rodape(pdf: Path) -> bool:
    # Com o rodape FIXO (absoluto), o modo de falha possivel e o conteudo
    # escorregar por baixo dele (sobreposicao). O rodape e todo caixa alta,
    # digitos e pontuacao; o conteudo tem minusculas. Entao: na faixa dos
    # ultimos BANDA_RODAPE_PT da pagina, texto com letra minuscula = conteudo
    # invadindo a faixa do rodape = REPROVADO.
    # Usa pypdfium2 (charboxes em pontos reais do PDF); o visitor do pypdf nao
    # devolve coordenadas confiaveis nos PDFs do Chromium (transformacao no cm).
    doc = pdfium.PdfDocument(str(pdf))
    ok = True
    for i in range(2, ESPERA_PAGINAS + 1):
        tp = doc[i - 1].get_textpage()
        pedacos = []
        for j in range(tp.count_chars()):
            _l, _b, _r, topo = tp.get_charbox(j)
            if topo < BANDA_RODAPE_PT:
                pedacos.append(tp.get_text_range(j, 1))
        banda = "".join(pedacos)
        limpo = not any(c.islower() for c in banda)
        detalhe = "OK" if limpo else f"FALHA (conteudo sob o rodape: '{banda.strip()[:60]}')"
        print(f"  faixa rodape pg{i} (so caixa alta abaixo de {BANDA_RODAPE_PT}pt): {detalhe}")
        ok &= limpo
    doc.close()
    return ok


def qa_estrutural(pdf: Path) -> bool:
    reader = PdfReader(str(pdf))
    ok = True

    n = len(reader.pages)
    print(f"paginas: {n} ({'OK' if n == ESPERA_PAGINAS else 'FALHA'})")
    ok &= n == ESPERA_PAGINAS

    for i, pg in enumerate(reader.pages, 1):
        box = pg.mediabox
        w, h = float(box.width), float(box.height)
        dim_ok = abs(w - A4_W) <= DIM_TOL and abs(h - A4_H) <= DIM_TOL
        print(f"  pg{i}: {w:.0f}x{h:.0f}pt ({'OK' if dim_ok else 'FALHA'})")
        ok &= dim_ok

    links = 0
    for pg in reader.pages:
        for a in pg.get("/Annots", []) or []:
            obj = a.get_object()
            if obj.get("/Subtype") == "/Link":
                links += 1
    print(f"links: {links} ({'OK' if links == ESPERA_LINKS else 'FALHA'})")
    ok &= links == ESPERA_LINKS

    ok &= qa_rodapes(reader)
    ok &= qa_faixa_rodape(pdf)

    return ok


def qa_visual(pdf: Path, qa_dir: Path) -> None:
    doc = pdfium.PdfDocument(str(pdf))
    for idx, nome in PAGINAS.items():
        if idx >= len(doc):
            continue
        img = doc[idx].render(scale=SCALE).to_pil()
        out = qa_dir / f"{nome}.png"
        img.save(out)
        print(f"  visual: {out}")
        w, h = img.size
        footer = img.crop((0, int(h * (1 - FOOTER_FRAC)), w, h))
        fout = qa_dir / f"{nome}_footer.png"
        footer.save(fout)
        print(f"  rodape: {fout}")
    doc.close()


def main() -> None:
    if len(sys.argv) < 2:
        sys.exit("uso: python3 qa.py <caminho_do_pdf> [dir_qa]")
    pdf = Path(sys.argv[1])
    qa_dir = Path(sys.argv[2]) if len(sys.argv) > 2 else pdf.parent / "qa"
    qa_dir.mkdir(parents=True, exist_ok=True)
    if not pdf.exists():
        sys.exit(f"PDF nao encontrado: {pdf}")

    print(f"== QA: {pdf.name} ==")
    ok = qa_estrutural(pdf)
    print("-- visual (inspecionar pg2 e pg5 para bloco cinza nos botoes) --")
    qa_visual(pdf, qa_dir)
    print("== RESULTADO:", "APROVADO" if ok else "REPROVADO", "==")
    sys.exit(0 if ok else 1)


if __name__ == "__main__":
    main()
