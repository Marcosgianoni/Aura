#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
qa.py (bundle) :: QA do PDF gerado.

Estrutural (pypdf):
  - exatamente 5 paginas
  - cada pagina A4 retrato (595 x 842 pt, tolerancia +-2pt)
  - 6 anotacoes de link (3 institucionais na pag. 2 + 3 botoes na pag. 5)
  - paginacao "0X / 05" presente no texto das paginas 2 a 5 (rodape nao clipado)

Encaixe (pypdfium2, charboxes):
  - paginas 2 a 5: o FUNDO do caractere minusculo mais baixo do miolo precisa
    ficar acima do topo do rodape com folga minima (LIMITE_MIOLO_PT).
    Historico: a versao anterior media pelo TOPO do caractere contra uma faixa
    fixa de 50pt; hastes descendentes (p, j, g, y) desciam ate ~44pt colidindo
    com o rodape (topo ~48pt) sem disparar o guarda. Furo provado no golden da
    GD 36148 (pagamento de 4 linhas na pg3). Medir pelo fundo fecha o furo.
  - pagina 1 (capa): presenca dos blocos EMITIDA EM / VALIDA ATE e do selo
    institucional DESDE 2013 (se o conteudo empurrar o bloco de datas, o selo
    sai da pagina e some do texto extraivel), e nenhum caractere com fundo
    abaixo de CAPA_PISO_PT (conteudo encostando na borda inferior).
    Historico: a capa ficava fora de todos os guardas; quebra real chegou ao
    cliente na proposta GD 36148 (nome de 3 linhas + lead de 4 linhas).

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

# Geometria medida no PDF real (charboxes pypdfium2):
# o texto do rodape das paginas internas ocupa a faixa vertical de ~36.5pt
# (fundo) a ~48.0pt (topo). O miolo precisa terminar acima do topo do rodape
# com folga; medimos pelo FUNDO do caractere para pegar hastes descendentes.
RODAPE_TOPO_PT = 48.0
FOLGA_MIOLO_PT = 6.0
LIMITE_MIOLO_PT = RODAPE_TOPO_PT + FOLGA_MIOLO_PT  # 54.0

# Capa: nenhum caractere pode ter o fundo abaixo deste piso (texto encostando
# ou clipando na borda inferior). Calibracao medida em capas saudaveis:
# o bloco inferior (datas + selo DESDE 2013) fica a ~7.9pt (GD, nome de 3
# linhas) e ~10.1pt (CBC) da borda. O bloco esta no fluxo e desce conforme o
# conteudo cresce; o modo de falha principal (selo empurrado para fora da
# pagina) e pego pelas checagens de PRESENCA em qa_capa. O piso e um guarda
# complementar contra texto parcialmente clipado na borda.
CAPA_PISO_PT = 4.0


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


def qa_encaixe_miolo(pdf: Path) -> bool:
    # Paginas 2 a 5: procura o caractere MINUSCULO com o fundo mais baixo.
    # Minusculas pertencem ao miolo (o rodape e todo caixa alta, digitos e
    # pontuacao). Se o fundo dele estiver abaixo de LIMITE_MIOLO_PT, o miolo
    # invadiu ou encostou no rodape: REPROVADO.
    # Usa pypdfium2 (charboxes em pontos reais do PDF); o visitor do pypdf nao
    # devolve coordenadas confiaveis nos PDFs do Chromium (transformacao no cm).
    doc = pdfium.PdfDocument(str(pdf))
    ok = True
    for i in range(2, ESPERA_PAGINAS + 1):
        tp = doc[i - 1].get_textpage()
        pior_fundo = None
        vizinhanca = []
        for j in range(tp.count_chars()):
            _l, fundo, _r, _t = tp.get_charbox(j)
            c = tp.get_text_range(j, 1)
            if c.islower():
                if pior_fundo is None or fundo < pior_fundo:
                    pior_fundo = fundo
                if fundo < LIMITE_MIOLO_PT:
                    vizinhanca.append(c)
        if pior_fundo is None:
            # pagina sem nenhuma minuscula seria anomala por si so
            print(f"  encaixe pg{i}: FALHA (nenhum texto minusculo encontrado)")
            ok = False
            continue
        limpo = pior_fundo >= LIMITE_MIOLO_PT
        if limpo:
            print(f"  encaixe pg{i} (fundo do miolo {pior_fundo:.1f}pt >= {LIMITE_MIOLO_PT:.0f}pt): OK")
        else:
            trecho = "".join(vizinhanca)[:60]
            print(f"  encaixe pg{i} (fundo do miolo {pior_fundo:.1f}pt < {LIMITE_MIOLO_PT:.0f}pt): FALHA (miolo sobre o rodape: '{trecho}')")
        ok &= limpo
    doc.close()
    return ok


def qa_capa(pdf: Path) -> bool:
    # Capa (pagina 1): tres guardas.
    # 1) "EMITIDA EM" presente no texto extraivel
    # 2) "VALIDA ATE" presente no texto extraivel
    # 3) selo institucional "DESDE 2013" presente (se o bloco de datas for
    #    empurrado para baixo, o selo sai da pagina e some da extracao)
    # 4) nenhum caractere com fundo abaixo de CAPA_PISO_PT
    # Regexes tolerantes a espacamento de letras (letter-spacing vira espacos
    # na extracao) e a possiveis variacoes do acento na extracao.
    doc = pdfium.PdfDocument(str(pdf))
    tp = doc[0].get_textpage()
    n = tp.count_chars()
    txt = tp.get_text_range(0, n) if n else ""

    checks = [
        ("capa 'EMITIDA EM'", r"E\s*M\s*I\s*T\s*I\s*D\s*A\s*E\s*M"),
        ("capa 'VALIDA ATE'", r"V\s*[ÁA]\s*L\s*I\s*D\s*A\s*A\s*T\s*[ÉE]"),
        ("capa selo 'DESDE 2013'", r"D\s*E\s*S\s*D\s*E\s*2\s*0\s*1\s*3"),
    ]
    ok = True
    for nome, padrao in checks:
        achou = re.search(padrao, txt, re.IGNORECASE) is not None
        print(f"  {nome}: {'OK' if achou else 'FALHA (bloco ausente ou empurrado para fora da pagina)'}")
        ok &= achou

    pior_fundo = None
    for j in range(n):
        _l, fundo, _r, _t = tp.get_charbox(j)
        c = tp.get_text_range(j, 1)
        if c.strip():
            if pior_fundo is None or fundo < pior_fundo:
                pior_fundo = fundo
    if pior_fundo is None:
        print("  capa piso: FALHA (capa sem texto extraivel)")
        ok = False
    else:
        piso_ok = pior_fundo >= CAPA_PISO_PT
        print(f"  capa piso (fundo mais baixo {pior_fundo:.1f}pt >= {CAPA_PISO_PT:.0f}pt): {'OK' if piso_ok else 'FALHA (conteudo encostando na borda inferior)'}")
        ok &= piso_ok

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
    ok &= qa_encaixe_miolo(pdf)
    ok &= qa_capa(pdf)

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
