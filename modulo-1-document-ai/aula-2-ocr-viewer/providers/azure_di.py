"""Azure AI Document Intelligence — o OCR tradicional da demo.

Usamos **só o `prebuilt-read`**, de propósito: ele é o OCR tradicional
puro. Devolve, para cada palavra, uma caixa (bbox), a transcrição e a
confiança — e nada mais. Montar título, tabela e ordem de leitura a
partir disso é problema seu, e é exatamente o contraste que a aula 2
quer mostrar contra o OCR de LLM.

Preço por 1.000 páginas (set/2026):
    prebuilt-read    $1,50   só texto + posição
    prebuilt-layout  $10,00  texto + tabelas + estrutura (fora da demo)
"""

from __future__ import annotations

import os
import time

from modelos import Caixa, PaginaOCR, ResultadoOCR, estimar_custo

MODELO = "prebuilt-read"
ROTULO = "Azure DI · prebuilt-read"


def analisar(pdf_bytes: bytes) -> ResultadoOCR:
    res = ResultadoOCR(provider="azure", rotulo=ROTULO)

    endpoint = os.getenv("AZURE_DI_ENDPOINT")
    chave = os.getenv("AZURE_DI_KEY")
    if not endpoint or not chave:
        res.erro = "AZURE_DI_ENDPOINT / AZURE_DI_KEY não configurados no .env"
        return res

    try:
        from azure.ai.documentintelligence import DocumentIntelligenceClient
        from azure.ai.documentintelligence.models import AnalyzeDocumentRequest
        from azure.core.credentials import AzureKeyCredential
    except ImportError:
        res.erro = "Pacote azure-ai-documentintelligence ausente. Rode: uv sync --group ocr"
        return res

    inicio = time.perf_counter()
    try:
        client = DocumentIntelligenceClient(endpoint, AzureKeyCredential(chave))
        poller = client.begin_analyze_document(
            MODELO, AnalyzeDocumentRequest(bytes_source=pdf_bytes)
        )
        resultado = poller.result()
    except Exception as exc:  # noqa: BLE001 — a UI mostra o erro, não derruba a aula
        res.erro = f"{type(exc).__name__}: {exc}"
        res.segundos = time.perf_counter() - inicio
        return res

    res.segundos = time.perf_counter() - inicio
    res.paginas = [_converter_pagina(p) for p in (resultado.pages or [])]
    res.markdown = _montar_markdown(resultado, res)
    res.custo_usd = estimar_custo(f"azure:{MODELO}", len(res.paginas))
    res.extra = {
        "modelo": MODELO,
        "n_paragrafos": len(resultado.paragraphs or []),
    }
    return res


def _converter_pagina(p) -> PaginaOCR:
    pagina = PaginaOCR(
        numero=p.page_number,
        largura=p.width or 0,
        altura=p.height or 0,
        # `p.unit` é um enum (LengthUnit.INCH); normalizamos para
        # "inch" / "pixel", que é o que a UI escreve na caixinha.
        unidade=str(getattr(p.unit, "value", p.unit) or "inch").lower(),
    )
    for palavra in p.words or []:
        pagina.caixas.append(
            Caixa(
                texto=palavra.content,
                poligono=list(palavra.polygon or []),
                tipo="palavra",
                confianca=palavra.confidence,
                rotulo="palavra",
            )
        )
    for linha in p.lines or []:
        pagina.caixas.append(
            Caixa(
                texto=linha.content,
                poligono=list(linha.polygon or []),
                tipo="linha",
                rotulo="linha",
            )
        )
    pagina.texto = "\n".join(l.content for l in (p.lines or []))
    return pagina


def _montar_markdown(resultado, res: ResultadoOCR) -> str:
    """Reconstrói um markdown simples a partir dos parágrafos do `read`.

    É de propósito que isto seja feito na mão, e que fique pobre: o
    `prebuilt-read` não sabe o que é tabela nem título — o papel
    (`role`) que ele preenche é raro. Este é o trabalho que o OCR de
    LLM já entrega pronto, e mostrar o contraste é o ponto da aula.
    """
    partes: list[str] = []
    for paragrafo in resultado.paragraphs or []:
        papel = getattr(paragrafo, "role", None)
        texto = paragrafo.content or ""
        if papel == "title":
            partes.append(f"# {texto}")
        elif papel == "sectionHeading":
            partes.append(f"## {texto}")
        elif papel in ("pageHeader", "pageFooter", "pageNumber"):
            continue
        else:
            partes.append(texto)

    if partes:
        return "\n\n".join(partes)
    return "\n\n".join(p.texto for p in res.paginas)
