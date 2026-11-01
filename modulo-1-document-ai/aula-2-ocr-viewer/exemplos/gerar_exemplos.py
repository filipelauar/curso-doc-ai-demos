"""Gera os documentos de exemplo da demo da aula 2.

Três documentos que exercitam coisas diferentes do OCR:

  nota-fiscal.pdf   nativo digital, com tabela  -> o caso fácil
  contrato.pdf      nativo, duas colunas        -> ordem de leitura
  recibo-escaneado.pdf  rasterizado e torto     -> precisa de OCR

    uv run python modulo-1-document-ai/aula-2-ocr-viewer/exemplos/gerar_exemplos.py
"""

from __future__ import annotations

import math
from pathlib import Path

import fitz

AQUI = Path(__file__).parent
A4 = fitz.paper_rect("a4")

PRETO = (0, 0, 0)
CINZA = (0.35, 0.35, 0.35)
AZUL = (0.03, 0.57, 0.70)


def _texto(page, x, y, txt, tam=10, cor=PRETO, negrito=False):
    page.insert_text(
        (x, y), txt, fontsize=tam, fontname="hebo" if negrito else "helv", color=cor
    )


# ── 1. Nota fiscal — nativo, com tabela ──────────────────────────
def nota_fiscal(caminho: Path) -> None:
    doc = fitz.open()
    page = doc.new_page(width=A4.width, height=A4.height)

    page.draw_rect(fitz.Rect(40, 40, 555, 100), color=AZUL, width=1.2)
    _texto(page, 55, 65, "NOTA FISCAL DE SERVIÇOS ELETRÔNICA", 14, AZUL, True)
    _texto(page, 55, 85, "Número 2026/001482    Série 1    Emissão 10/03/2026", 9, CINZA)

    _texto(page, 40, 130, "PRESTADOR", 9, AZUL, True)
    for i, linha in enumerate([
        "EMPRESA XYZ SERVIÇOS LTDA",
        "CNPJ: 12.345.678/0001-99     Inscrição Municipal: 4.821.337",
        "Av. Afonso Pena, 1500 — Centro — Belo Horizonte/MG — CEP 30130-921",
    ]):
        _texto(page, 40, 148 + i * 14, linha, 9, negrito=(i == 0))

    _texto(page, 40, 210, "TOMADOR", 9, AZUL, True)
    for i, linha in enumerate([
        "CLIENTE ABC COMÉRCIO S.A.",
        "CNPJ: 98.765.432/0001-10",
        "Rua Oscar Freire, 220 — Jardins — São Paulo/SP — CEP 01426-000",
    ]):
        _texto(page, 40, 228 + i * 14, linha, 9, negrito=(i == 0))

    _texto(page, 40, 295, "DISCRIMINAÇÃO DOS SERVIÇOS", 9, AZUL, True)

    colunas = [40, 300, 360, 440, 555]
    cabecalho = ["Descrição", "Qtd", "Valor unit.", "Total"]
    linhas = [
        ["Consultoria em arquitetura de dados", "2", "500,00", "1.000,00"],
        ["Implantação de pipeline de ingestão", "1", "250,00", "250,00"],
        ["Treinamento da equipe técnica (8h)", "1", "800,00", "800,00"],
    ]

    y = 312
    page.draw_rect(fitz.Rect(colunas[0], y, colunas[-1], y + 20), fill=(0.94, 0.96, 0.98))
    for i, titulo in enumerate(cabecalho):
        _texto(page, colunas[i] + 6, y + 14, titulo, 9, AZUL, True)

    y += 20
    for linha in linhas:
        page.draw_line(fitz.Point(colunas[0], y), fitz.Point(colunas[-1], y), color=(0.8, 0.8, 0.8))
        for i, celula in enumerate(linha):
            _texto(page, colunas[i] + 6, y + 15, celula, 9)
        y += 22
    page.draw_rect(fitz.Rect(colunas[0], 312, colunas[-1], y), color=(0.7, 0.7, 0.7), width=0.8)
    for x in colunas[1:-1]:
        page.draw_line(fitz.Point(x, 312), fitz.Point(x, y), color=(0.8, 0.8, 0.8))

    y += 25
    for rotulo, valor, neg in [
        ("Valor dos serviços", "R$ 2.050,00", False),
        ("ISS (5%)", "R$ 102,50", False),
        ("VALOR TOTAL DA NOTA", "R$ 1.947,50", True),
    ]:
        _texto(page, 360, y, rotulo, 9, negrito=neg)
        _texto(page, 480, y, valor, 9, negrito=neg)
        y += 18

    _texto(page, 40, y + 30, "Vencimento: 10/04/2026     Forma de pagamento: Boleto bancário", 9)
    _texto(page, 40, y + 48, "Código de verificação: 7F3A-99C1-B20D", 8, CINZA)

    doc.save(caminho)
    doc.close()


# ── 2. Contrato — nativo, duas colunas ───────────────────────────
def contrato(caminho: Path) -> None:
    doc = fitz.open()
    page = doc.new_page(width=A4.width, height=A4.height)

    _texto(page, 40, 60, "CONTRATO DE PRESTAÇÃO DE SERVIÇOS", 13, PRETO, True)
    _texto(page, 40, 78, "Contrato nº 2026/0047 — celebrado em 02/02/2026", 9, CINZA)
    page.draw_line(fitz.Point(40, 88), fitz.Point(555, 88), color=AZUL, width=1.2)

    esquerda = [
        ("CLÁUSULA 1 — DO OBJETO", True),
        ("O presente contrato tem por objeto a", False),
        ("prestação de serviços de consultoria", False),
        ("técnica em arquitetura de dados, conforme", False),
        ("especificações do Anexo I.", False),
        ("", False),
        ("CLÁUSULA 2 — DO PRAZO", True),
        ("A vigência é de 12 (doze) meses,", False),
        ("com início em 01/03/2026 e término em", False),
        ("28/02/2027, prorrogável por igual período", False),
        ("mediante termo aditivo.", False),
        ("", False),
        ("CLÁUSULA 3 — DO VALOR", True),
        ("O valor global do contrato é de", False),
        ("R$ 148.500,00 (cento e quarenta e oito", False),
        ("mil e quinhentos reais), pagos em 12", False),
        ("parcelas mensais de R$ 12.375,00.", False),
    ]
    direita = [
        ("CLÁUSULA 4 — DO REAJUSTE", True),
        ("Os valores serão reajustados anualmente", False),
        ("pela variação do IPCA acumulado nos", False),
        ("12 meses anteriores à data-base.", False),
        ("", False),
        ("CLÁUSULA 5 — DAS PENALIDADES", True),
        ("O atraso na execução sujeita a", False),
        ("CONTRATADA a multa de 0,5% por dia", False),
        ("sobre o valor da parcela, limitada a 10%.", False),
        ("", False),
        ("CLÁUSULA 6 — DA RESCISÃO", True),
        ("Qualquer das partes poderá rescindir o", False),
        ("contrato mediante aviso prévio de 30", False),
        ("(trinta) dias, sem ônus adicional.", False),
        ("", False),
        ("CLÁUSULA 7 — DO FORO", True),
        ("Fica eleito o foro da comarca de", False),
        ("Belo Horizonte/MG.", False),
    ]

    for coluna, x in ((esquerda, 40), (direita, 310)):
        y = 115
        for txt, neg in coluna:
            if txt:
                _texto(page, x, y, txt, 9, AZUL if neg else PRETO, neg)
            y += 15

    _texto(page, 40, 640, "_" * 34, 9)
    _texto(page, 310, 640, "_" * 34, 9)
    _texto(page, 40, 655, "EMPRESA XYZ SERVIÇOS LTDA", 8, CINZA)
    _texto(page, 310, 655, "CLIENTE ABC COMÉRCIO S.A.", 8, CINZA)
    _texto(page, 40, 670, "CONTRATADA", 8, CINZA)
    _texto(page, 310, 670, "CONTRATANTE", 8, CINZA)

    doc.save(caminho)
    doc.close()


# ── 3. Recibo escaneado — rasterizado, torto, sem camada de texto ─
def recibo_escaneado(caminho: Path) -> None:
    origem = fitz.open()
    page = origem.new_page(width=A4.width, height=A4.height)

    _texto(page, 60, 90, "RECIBO", 20, PRETO, True)
    _texto(page, 60, 130, "Recebi de CLIENTE ABC COMÉRCIO S.A., inscrito no", 11)
    _texto(page, 60, 150, "CNPJ 98.765.432/0001-10, a importância de", 11)
    _texto(page, 60, 175, "R$ 1.947,50 (mil novecentos e quarenta e sete reais", 12, PRETO, True)
    _texto(page, 60, 195, "e cinquenta centavos),", 12, PRETO, True)
    _texto(page, 60, 220, "referente à Nota Fiscal nº 2026/001482.", 11)
    _texto(page, 60, 270, "Belo Horizonte, 12 de abril de 2026.", 11)
    _texto(page, 60, 340, "_" * 40, 11)
    _texto(page, 60, 358, "EMPRESA XYZ SERVIÇOS LTDA", 9, CINZA)
    page.draw_rect(fitz.Rect(330, 300, 500, 370), color=(0.6, 0.15, 0.15), width=2)
    _texto(page, 350, 330, "PAGO", 16, (0.6, 0.15, 0.15), True)
    _texto(page, 345, 352, "12/04/2026", 9, (0.6, 0.15, 0.15))

    # Rasteriza — a partir daqui não existe mais camada de texto.
    pix = page.get_pixmap(dpi=160)
    origem.close()

    from PIL import Image

    img = Image.frombytes("RGB", (pix.width, pix.height), pix.samples)
    # inclinação e um leve cinza, como num scanner de mesa
    img = img.rotate(-1.6, expand=True, fillcolor=(247, 245, 240), resample=Image.BICUBIC)

    import io

    buf = io.BytesIO()
    img.save(buf, format="JPEG", quality=72)  # compressão de scanner

    doc = fitz.open()
    imgdoc = fitz.open(stream=buf.getvalue(), filetype="jpeg")
    pdfbytes = imgdoc.convert_to_pdf()
    imgpdf = fitz.open("pdf", pdfbytes)
    p = doc.new_page(width=A4.width, height=A4.height)
    p.show_pdf_page(p.rect, imgpdf, 0)
    doc.save(caminho)
    doc.close()


def main() -> None:
    nota_fiscal(AQUI / "nota-fiscal.pdf")
    contrato(AQUI / "contrato.pdf")
    recibo_escaneado(AQUI / "recibo-escaneado.pdf")
    for p in sorted(AQUI.glob("*.pdf")):
        with fitz.open(p) as d:
            chars = len(d[0].get_text().strip())
            tipo = "nativo" if chars > 100 else "ESCANEADO (precisa de OCR)"
            print(f"{p.name:26} {d.page_count} pág.  {chars:5} chars de texto nativo  -> {tipo}")


if __name__ == "__main__":
    main()
