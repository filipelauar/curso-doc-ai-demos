"""Camada de texto nativa via pymupdf — o "OCR que você não precisa rodar".

Não é OCR. Lê o texto que já está dentro do PDF, com a posição de cada
palavra. A forma da saída é a mesma do OCR tradicional (caixa +
transcrição), o que permite usá-lo como coluna da esquerda quando não
há chave da Azure configurada.

E isso é justamente o ponto da aula 2: numa página nativa digital, este
provider entrega o texto *melhor* que qualquer OCR — de graça,
instantaneamente e sem erro. Numa página escaneada, ele não entrega
nada — e é aí que o OCR passa a ser necessário.
"""

from __future__ import annotations

import time

import fitz  # pymupdf

from modelos import Caixa, PaginaOCR, ResultadoOCR

LIMIAR_TEXTO = 100  # caracteres abaixo dos quais a página é considerada escaneada


def analisar(pdf_bytes: bytes, **_) -> ResultadoOCR:
    res = ResultadoOCR(
        provider="nativo",
        rotulo="Camada nativa · pymupdf (sem OCR)",
        custo_usd=0.0,
        custo_estimado=False,
    )
    inicio = time.perf_counter()

    try:
        doc = fitz.open(stream=pdf_bytes, filetype="pdf")
    except Exception as exc:  # noqa: BLE001
        res.erro = f"{type(exc).__name__}: {exc}"
        return res

    partes: list[str] = []
    escaneadas: list[int] = []

    with doc:
        for page in doc:
            pagina = PaginaOCR(
                numero=page.number + 1,
                largura=page.rect.width,
                altura=page.rect.height,
                unidade="point",
            )
            for x0, y0, x1, y1, palavra, *_resto in page.get_text("words"):
                pagina.caixas.append(
                    Caixa(
                        texto=palavra,
                        poligono=[x0, y0, x1, y0, x1, y1, x0, y1],
                        tipo="palavra",
                    )
                )
            for bloco in page.get_text("blocks"):
                x0, y0, x1, y1, texto = bloco[0], bloco[1], bloco[2], bloco[3], bloco[4]
                if texto.strip():
                    pagina.caixas.append(
                        Caixa(
                            texto=texto.strip(),
                            poligono=[x0, y0, x1, y0, x1, y1, x0, y1],
                            tipo="linha",
                        )
                    )

            pagina.texto = page.get_text()
            if len(pagina.texto.strip()) < LIMIAR_TEXTO:
                escaneadas.append(pagina.numero)
            partes.append(pagina.texto)
            res.paginas.append(pagina)

    res.segundos = time.perf_counter() - inicio
    res.markdown = "\n\n".join(partes)
    res.extra = {"paginas_escaneadas": escaneadas}

    if escaneadas and len(escaneadas) == len(res.paginas):
        res.erro = (
            "Nenhuma camada de texto neste documento — ele é escaneado. "
            "É exatamente o caso em que você *precisa* de OCR de verdade. "
            "Configure AZURE_DI_KEY no .env para ver o OCR tradicional aqui."
        )
    return res
