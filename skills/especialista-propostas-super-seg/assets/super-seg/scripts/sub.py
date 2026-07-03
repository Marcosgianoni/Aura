#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""sub.py (bundle) — preenche o template da proposta Super Seg.

Variante 'single' (laudo, padrao) faz so substituicao escalar, como antes.
Variante 'servicos' monta a tabela multi-item da pagina 3 a partir de
campos['itens'] e troca o bloco de escopo inteiro. A capa (lead) e o verbo
setorial da pagina 2 sao trocados quando os campos opcionais existem.

Uso: python3 sub.py <template.html> <campos.json> <saida_base.html>
"""
import json, re, sys
from pathlib import Path
from urllib.parse import quote

SCRIPT_DIR = Path(__file__).resolve().parent
TPL_DIR = SCRIPT_DIR.parent / "templates"

LEAD_LTIP = ("Laudo Técnico de Insalubridade e Periculosidade (LTIP) elaborado por "
             "especialistas, em conformidade integral com as NRs 15 e 16 — protegendo "
             "sua operação contra multas, autuações e passivos trabalhistas.")


def fmt_moeda(v):
    """Formata pt-BR com prefixo R$. Centavos suprimidos SOMENTE quando zero.
    Entrada e numerica (int/float); strings pre-formatadas sao erro de contrato."""
    assert isinstance(v, (int, float)) and not isinstance(v, bool), \
        f"[fmt] valor deve ser numerico, veio {type(v).__name__}: {v!r}"
    cents = round(v * 100)
    inteiro, cent = divmod(cents, 100)
    int_str = f"{inteiro:,}".replace(",", ".")
    return f"R$ {int_str}" if cent == 0 else f"R$ {int_str},{cent:02d}"


def fmt_partes(v):
    """Parte inteira e centavos separados (para spans estilizados).
    Retorna (int_str, cent_str); cent_str vazia quando centavos sao zero."""
    cents = round(v * 100)
    inteiro, cent = divmod(cents, 100)
    int_str = f"{inteiro:,}".replace(",", ".")
    return int_str, ("" if cent == 0 else f"{cent:02d}")


def validate_editorial(E):
    """Validacoes duras do bloco pagina3_editorial (4.0.0). Falha = aborta."""
    itens = E["itens"]
    assert 1 <= len(itens) <= 4, \
        f"[editorial] {len(itens)} itens: o layout editorial suporta ate 4; use o formato legado de tabela (5 a 7 itens) ou reporte."
    for i, it in enumerate(itens, 1):
        ti = it.get("titulo_italico", "")
        assert not ti or ti in it["titulo"], \
            f"[editorial] item {i}: titulo_italico {ti!r} nao e substring do titulo."
        assert len(it.get("checklist", [])) <= 4, \
            f"[editorial] item {i}: checklist com mais de 4 entradas (layout e 2x2)."
        if "preco_unitario" in it:
            assert round(it["preco_unitario"] * it["qtd"], 2) == round(it["preco"], 2), \
                f"[editorial] item {i}: preco_unitario x qtd != preco ({it['preco_unitario']} x {it['qtd']} != {it['preco']})."
    soma = round(sum(it["preco"] for it in itens), 2)
    desconto = round(float(E.get("desconto", 0)), 2)
    assert desconto >= 0, "[editorial] desconto negativo nao existe no orcamento."
    assert abs(soma - desconto - E["total"]) < 0.01, \
        f"[editorial] soma dos itens ({soma}) menos desconto ({desconto}) diverge do total ({E['total']}): fidelidade aritmetica ao orcamento."
    fp = E.get("forma_pagamento", {})
    if fp.get("origem") == "orcamento":
        assert fp.get("texto"), "[editorial] forma_pagamento.origem=orcamento exige o campo texto."


def rep(html, old, new, n=1):
    c = html.count(old)
    assert c > 0, f"[rep] nao encontrado: {old!r}"
    if n != -1:
        assert c == n, f"[rep] esperava {n} de {old!r}, achei {c}. Template divergente, abortando."
    return html.replace(old, new)


def rebuild_href(html, pattern, new_href, label):
    new, k = re.subn(pattern, lambda m: f'href="{new_href}"', html, count=1)
    assert k == 1, f"[href] esperava 1 {label}, troquei {k}"
    return new


PAGAMENTO_CANONICO = (
    "Após a aprovação do orçamento, a <strong>Nota Fiscal</strong> será emitida "
    "juntamente com o boleto, com vencimento para <strong>30 dias</strong> a contar "
    "da data de emissão. Realizado o levantamento das informações e/ou a visita "
    "técnica (se aplicável), o prazo de entrega dos documentos será de até "
    "<strong>7 dias úteis</strong>. Mediante o envio dos documentos para validação, "
    "será considerado o prazo de até <strong>7 dias</strong> para eventuais ajustes, "
    "sem cobrança adicional, caso necessário.")


def parse_moeda(txt):
    """Converte string pt-BR ('1.120,00') em float. Para a guarda da tabela legada."""
    t = txt.strip().replace("R$", "").strip().replace(".", "").replace(",", ".")
    return float(t)


def md_bold(s):
    """Converte pares **texto** em <strong>texto</strong>. Unico markup aceito."""
    partes = s.split("**")
    assert len(partes) % 2 == 1, f"[md_bold] ** desbalanceado em: {s[:80]!r}"
    out = []
    for i, p in enumerate(partes):
        out.append(f"<strong>{p}</strong>" if i % 2 else p)
    return "".join(out)


def build_pg3_editorial(C):
    """Pagina 3 editorial (4.0.0): blocos por item a partir de C['pagina3_editorial']."""
    E = C["pagina3_editorial"]
    validate_editorial(E)
    frag = (TPL_DIR / "pg3_servicos_editorial.html").read_text(encoding="utf-8")
    m = re.search(r"<!-- ITEM -->(.*?)<!-- /ITEM -->", frag, re.S)
    assert m, "pg3_servicos_editorial.html sem marcadores ITEM"
    item_tpl = m.group(1)

    blocos = []
    for i, it in enumerate(E["itens"], 1):
        titulo_html = it["titulo"]
        ti = it.get("titulo_italico", "")
        if ti:
            titulo_html = titulo_html.replace(
                ti, f'<span class="italic">{ti}</span>', 1)
        p_int, p_cent = fmt_partes(it["preco"])
        preco_html = f"R$ {p_int}" + (f'<span class="ed-cent">,{p_cent}</span>' if p_cent else "")
        checklist_html = "".join(f"<li>{x}</li>" for x in it.get("checklist", []))
        b = (item_tpl
             .replace("{{NUM}}", f"{i:02d}")
             .replace("{{CATEGORIA}}", it["categoria"])
             .replace("{{TITULO_HTML}}", titulo_html)
             .replace("{{DESCRICAO_HTML}}", md_bold(it["descricao"]))
             .replace("{{CHECKLIST_HTML}}", checklist_html)
             .replace("{{QTD_ROTULO}}", it.get("qtd_rotulo", f"QTD. {it['qtd']:02d}"))
             .replace("{{PRECO_HTML}}", preco_html))
        blocos.append(b)
    frag = frag[:m.start()] + "".join(blocos) + frag[m.end():]

    n = len(E["itens"])
    v_int, v_cent = fmt_partes(E["total"])
    cent_sup = (f'<span style="font-family:\'Fraunces\',serif;font-size:22pt;'
                f'color:var(--azul);vertical-align:top;">,{v_cent}</span>') if v_cent else ""
    fp = E.get("forma_pagamento", {"origem": "canonico"})
    pagamento = PAGAMENTO_CANONICO if fp.get("origem", "canonico") == "canonico" else md_bold(fp["texto"])

    desconto = round(float(E.get("desconto", 0)), 2)
    if desconto > 0:
        soma_itens = round(sum(it["preco"] for it in E["itens"]), 2)
        linha_desc = ('<div class="ed-desconto">'
                      f'<span>Soma dos itens {fmt_moeda(soma_itens)}</span>'
                      f'<span>Desconto conforme orçamento <span class="ed-desconto-valor">− {fmt_moeda(desconto)}</span></span>'
                      '</div>')
    else:
        linha_desc = ""

    repls = {
        "{{LINHA_DESCONTO}}": linha_desc,
        "{{NUMERO}}": C["numero"],
        "{{CLIENTE}}": C["cliente"],
        "{{ESCOPO_INTRO}}": C.get("escopo_intro", ""),
        "{{ESCOPO_HEADER_ESQ}}": f"ESCOPO CONTRATADO · {n} {'ITENS' if n > 1 else 'ITEM'}",
        "{{TOTAL_FMT}}": fmt_moeda(E["total"]),
        "{{ESCOPO_NOTA}}": E.get("observacao_tecnica", ""),
        "{{INVEST_SUBLABEL}}": E.get("investimento", {}).get("subtitulo_itens", C.get("service_summary", "")),
        "{{VALOR_GRANDE}}": v_int,
        "{{CENT_SUP}}": cent_sup,
        "{{PAGAMENTO_HTML}}": pagamento,
    }
    for k, v in repls.items():
        frag = frag.replace(k, v)
    assert "{{" not in frag, f"pg3_editorial: token nao preenchido -> {frag[frag.index('{{'):frag.index('{{')+50]}"
    return frag


def build_pg3_servicos(C):
    itens_tab = C.get("itens", [])
    assert 5 <= len(itens_tab) <= 7, \
        f"[servicos-tabela] {len(itens_tab)} itens: a tabela legada e para 5 a 7; com 1 a 4 use pagina3_editorial, com 8+ reporte e nao gere."
    # Guarda aritmetica da tabela (licao GD 36148): soma - desconto == total
    soma_tab = round(sum(parse_moeda(i["subtotal"]) for i in itens_tab), 2)
    desconto_tab = round(float(C.get("desconto", 0)), 2)
    assert desconto_tab >= 0, "[servicos-tabela] desconto negativo nao existe no orcamento."
    total_tab = parse_moeda(f"{C['total_int']},{C['total_cent']}")
    assert abs(soma_tab - desconto_tab - total_tab) < 0.01, \
        f"[servicos-tabela] soma dos subtotais ({soma_tab}) menos desconto ({desconto_tab}) diverge do total ({total_tab}): fidelidade aritmetica ao orcamento."
    frag = (TPL_DIR / "pg3_servicos.html").read_text(encoding="utf-8")
    m = re.search(r"<!-- ROW -->(.*?)<!-- /ROW -->", frag, re.S)
    assert m, "pg3_servicos.html sem marcadores ROW"
    row_tpl = m.group(1)

    itens = C["itens"]
    assert itens, "campos['itens'] vazio na variante servicos"
    linhas = []
    for i, it in enumerate(itens, 1):
        r = (row_tpl
             .replace("{{NUM}}", f"{i:02d}")
             .replace("{{SERVICO}}", it["servico"])
             .replace("{{NORMA}}", it.get("norma", ""))
             .replace("{{ESPEC}}", it["especificacao"])
             .replace("{{QTD}}", str(it["qtd"]))
             .replace("{{VLR_UNIT}}", fmt_moeda(parse_moeda(it["vlr_unit"])))
             .replace("{{SUBTOTAL}}", fmt_moeda(parse_moeda(it["subtotal"]))))
        linhas.append(r)
    frag = frag[:m.start()] + "".join(linhas) + frag[m.end():]

    repls = {
        "{{NUMERO}}": C["numero"],
        "{{CLIENTE}}": C["cliente"],
        "{{ESCOPO_INTRO}}": C.get("escopo_intro", ""),
        "{{N_ITENS}}": f"{len(itens):02d}",
        "{{ESCOPO_TAG}}": C.get("escopo_tag", "ESCOPO TÉCNICO"),
        "{{ESCOPO_TITULO}}": C.get("escopo_titulo", "Serviços <span class=\"italic\">contratados</span>"),
        "{{ESCOPO_DESCRICAO}}": C.get("escopo_descricao", ""),
        "{{LINHA_DESCONTO}}": (
            '<tr><td class="total-rotulo" colspan="5" style="border-bottom:none;color:var(--cinza-500);font-size:7pt;">Soma dos itens</td>'
            f'<td class="total-valor" style="border-bottom:none;font-size:9pt;color:var(--cinza-700);">{fmt_moeda(soma_tab)}</td></tr>'
            '<tr><td class="total-rotulo" colspan="5" style="border-bottom:none;color:var(--cinza-500);font-size:7pt;">Desconto conforme orçamento</td>'
            f'<td class="total-valor" style="border-bottom:none;font-size:9pt;color:var(--cinza-700);">− {fmt_moeda(desconto_tab)}</td></tr>'
        ) if desconto_tab > 0 else "",
        "{{TOTAL_INT}}": C["total_int"],
        "{{CENT_TOT}}": (f'<span class="cent-tot">,{C["total_cent"]}</span>'
                          if C["total_cent"] != "00" else ""),
        "{{CENT_GRANDE}}": (f'<span style="font-family:\'Fraunces\',serif;font-size:22pt;'
                            f'color:var(--azul);vertical-align:top;">,{C["total_cent"]}</span>'
                            if C["total_cent"] != "00" else ""),
        "{{ESCOPO_NOTA}}": C.get("escopo_nota",
            "As quantidades refletem o levantamento atual; variações no efetivo na data de realização podem alterar o valor final."),
        "{{INVEST_SUBLABEL}}": C.get("invest_sublabel", C.get("service_summary", "")),
        "{{VALOR_GRANDE}}": C["valor_grande"],
    }
    for k, v in repls.items():
        frag = frag.replace(k, v)
    assert "{{" not in frag, f"pg3_servicos: token nao preenchido -> {frag[frag.index('{{'):frag.index('{{')+50]}"
    return frag


def replace_pg3(html, new_pg3):
    DELIM = '<div class="page pagina-interna">'
    anchor = "— 03 / Escopo Técnico"
    idx = html.index(anchor)
    start = html.rindex(DELIM, 0, idx)
    nxt = html.index(DELIM, idx)
    return html[:start] + new_pg3.rstrip() + "\n\n" + html[nxt:]


def main():
    template, campos_path, saida = map(Path, sys.argv[1:4])
    C = json.loads(campos_path.read_text(encoding="utf-8"))

    # 4.1.3: valor_moeda e valor_grande sao DERIVADOS do total, nao escritos
    # pelo agente (elimina a classe de erro de duplicata dessincronizada e
    # aplica a regra de centavos tambem nos CTAs e na mensagem de entrega).
    if "pagina3_editorial" in C:
        _total = float(C["pagina3_editorial"]["total"])
    elif "total_int" in C and "total_cent" in C:
        _total = parse_moeda(f"{C['total_int']},{C['total_cent']}")
    else:
        _total = parse_moeda(C["valor_moeda"])
    C["valor_moeda"] = fmt_moeda(_total)
    C["valor_grande"] = fmt_partes(_total)[0]
    html = template.read_text(encoding="utf-8")
    variante = C.get("variante", "single")

    # --- reps globais (contagens validas no template single completo) ---
    html = rep(html, "<strong>AGIS Construção S.A.</strong>", f"<strong>{C['cliente_caps']}</strong>")
    html = rep(html, '<span style="color:var(--cinza-500);font-size:8.5pt;">FISCAL@GRUPOAGIS.COM.BR</span>',
               f'<span style="color:var(--cinza-500);font-size:8.5pt;">{C["ac_email"]}</span>')
    html = rep(html, '<div class="conteudo">Eduarda<br>', f'<div class="conteudo">{C["ac_contato"]}<br>')
    html = rep(html, '<div class="valor">19.05.2026</div>', f'<div class="valor">{C["data_emissao"]}</div>')
    html = rep(html, '<div class="valor">26.05.2026</div>', f'<div class="valor">{C["validade"]}</div>')
    html = rep(html, "Válida até 26/05/2026", f"Válida até {C['validade_barra']}")
    html = rep(html, '<span class="valor-grande">1.750</span>', f'<span class="valor-grande">{C["valor_grande"]}</span>')
    html = rep(html, "61.099.826/0012-05", C["cnpj"])
    html = rep(html, "35341", C["numero"], n=8)
    html = rep(html, "AGIS Construção S.A.", C["cliente"], n=4)

    # --- chamada da capa e verbo setorial (opcionais) ---
    if C.get("lead_apresentacao"):
        html = rep(html, LEAD_LTIP, C["lead_apresentacao"])
    if C.get("setor_verbo"):
        # Trava 4.0.0: o template ja fecha com "o Brasil."; um setor_verbo contendo
        # "Brasil" (ex. "move o Brasil") produz a duplicacao "quem move o Brasil o Brasil".
        # Para a manchete padrao, o valor correto e setor_verbo = "move".
        assert "brasil" not in C["setor_verbo"].lower(), \
            f"[manchete] setor_verbo {C['setor_verbo']!r} contem 'Brasil'; o template ja fecha com 'o Brasil.'. Use so o verbo (ex. 'move')."
        html = rep(html, '<span class="italic" style="color:var(--azul);">quem constrói</span>',
                   f'<span class="italic" style="color:var(--azul);">quem {C["setor_verbo"]}</span>')

    # --- pilares da pagina 2 (descricoes opcionais; titulos sao fixos) ---
    pil = C.get("pilares") or {}
    if pil.get("juridica"):
        html = rep(html, "Laudos tecnicamente robustos que protegem sua empresa em fiscalizações, ações trabalhistas e auditorias do MTE.", pil["juridica"])
    if pil.get("agilidade"):
        html = rep(html, "Previsão de entrega de até 10 dias úteis após a visita técnica, sem comprometer o rigor metodológico.", pil["agilidade"])
    if pil.get("tecnico"):
        html = rep(html, "Equipe especializada, com aplicação criteriosa das NR-15 e NR-16 e metodologias reconhecidas pelo MTE.", pil["tecnico"])
    if pil.get("esg"):
        html = rep(html, "Entregas 100% digitais com certificação ICP-Brasil, reduzindo o uso de papel e a pegada ambiental.", pil["esg"])

    # --- pagina 3 por variante ---
    # 4.0.0: a variante servicos usa o layout editorial (bloco pagina3_editorial).
    # A tabela antiga permanece apenas como fallback interno para campos legados
    # (sem o bloco editorial), decisao registrada no VERSION.
    if variante == "servicos":
        if "pagina3_editorial" in C:
            html = replace_pg3(html, build_pg3_editorial(C))
        else:
            html = replace_pg3(html, build_pg3_servicos(C))
    elif variante != "single":
        raise SystemExit(f"variante desconhecida: {variante!r} (use single ou servicos)")

    # --- CTAs (pagina 5) ---
    subject = f"APROVADO - Proposta {C['numero']} - {C['cliente_display']}"
    body = ("Olá, Super Seg!\n\n"
            f"Aprovamos a Proposta nº {C['numero']} referente a {C['service_summary']}.\n\n"
            f"Empresa: {C['cliente']}\nCNPJ: {C['cnpj']}\nValor: {C['valor_moeda']}\n\n"
            "Por favor, podem dar sequência à programação técnica e emissão da NF/boleto.\n\nAguardo retorno.")
    mailto = f"mailto:comercial@super-seg.com?subject={quote(subject)}&body={quote(body)}"
    html = rebuild_href(html, r'href="mailto:comercial@super-seg\.com\?[^"]*"', mailto, "mailto")

    wa_text = (f"Olá, Super Seg! Aprovamos a Proposta nº {C['numero']} "
               f"({C['service_summary_wa']} - {C['cliente']}). Podemos dar sequência?")
    wa = f"https://wa.me/551134215870?text={quote(wa_text)}"
    html = rebuild_href(html, r'href="https://wa\.me/551134215870\?[^"]*"', wa, "whatsapp")

    saida.write_text(html, encoding="utf-8")
    print(f"OK [{variante}] -> {saida} ({len(html):,} bytes)")


if __name__ == "__main__":
    main()
