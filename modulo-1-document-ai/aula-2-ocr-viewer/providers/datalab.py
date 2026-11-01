"""Datalab / Chandra — o OCR de LLM da demo.

Devolve markdown com o layout já montado. Chamamos a API na mão
(submit + poll) de propósito: o SDK esconde o polling, e mostrar que
OCR de LLM é um *job assíncrono* — e não uma chamada instantânea como o
OCR tradicional — é parte do que a aula 2 quer ensinar.

Pedimos `output_format=markdown,json` numa chamada só (mesmo preço): o
markdown é o que a coluna da direita mostra, e o json traz os *blocos
de layout* com bbox — o que alimenta a aba "Layout" da demo. Repare na
diferença de granularidade contra o Azure: lá a caixa é a palavra, aqui
é o bloco ("Table", "SectionHeader"), e é isso que faz o markdown sair
montado.

    POST /api/v1/convert   -> {"request_check_url": ...}
    GET  <request_check_url> até status == "complete"

Preço (set/2026): Convert fast/balanced ~$4/1.000 páginas,
accurate ~$10/1.000 páginas. Processamento na UE custa +25%.
"""

from __future__ import annotations

import os
import re
import time

from modelos import Caixa, PaginaOCR, ResultadoOCR, estimar_custo

URL_CONVERT = "https://www.datalab.to/api/v1/convert"
INTERVALO_POLL = 2.0
TIMEOUT_TOTAL = 180.0


def analisar(
    pdf_bytes: bytes,
    modo: str = "balanced",
    max_paginas: int = 5,
    progresso=None,
) -> ResultadoOCR:
    """`progresso` é um callable opcional (texto) -> None, para a UI."""
    res = ResultadoOCR(provider="datalab", rotulo=f"Chandra · Datalab ({modo})")

    chave = os.getenv("DATALAB_API_KEY")
    if not chave:
        res.erro = "DATALAB_API_KEY não configurada no .env"
        return res

    try:
        import requests
    except ImportError:
        res.erro = "Pacote requests ausente. Rode: uv sync --group ocr"
        return res

    def avisar(texto: str) -> None:
        if progresso:
            progresso(texto)

    inicio = time.perf_counter()
    headers = {"X-API-Key": chave}

    try:
        avisar("enviando o documento...")
        envio = requests.post(
            URL_CONVERT,
            headers=headers,
            files={"file": ("documento.pdf", pdf_bytes, "application/pdf")},
            data={
                "output_format": "markdown,json",
                "mode": modo,
                "max_pages": str(max_paginas),
                "paginate": "true",
            },
            timeout=120,
        )
        envio.raise_for_status()
        submissao = envio.json()
        if not submissao.get("success", True):
            res.erro = f"Datalab recusou o envio: {submissao.get('error')}"
            return res

        check_url = submissao.get("request_check_url")
        if not check_url:
            res.erro = f"Resposta sem request_check_url: {submissao}"
            return res

        # ── polling ──────────────────────────────────────────────
        tentativa = 0
        dados = {}
        while time.perf_counter() - inicio < TIMEOUT_TOTAL:
            tentativa += 1
            avisar(f"processando... (verificação {tentativa})")
            time.sleep(INTERVALO_POLL)
            r = requests.get(check_url, headers=headers, timeout=60)
            r.raise_for_status()
            dados = r.json()
            if dados.get("status") == "complete":
                break
        else:
            res.erro = f"Tempo esgotado ({TIMEOUT_TOTAL:.0f}s) esperando a Datalab"
            return res

    except Exception as exc:  # noqa: BLE001
        res.erro = f"{type(exc).__name__}: {exc}"
        res.segundos = time.perf_counter() - inicio
        return res

    res.segundos = time.perf_counter() - inicio

    if not dados.get("success", True):
        res.erro = f"Datalab retornou erro: {dados.get('error')}"
        return res

    markdown = dados.get("markdown") or ""
    res.markdown = _limpar_marcas(markdown)
    res.paginas = _montar_paginas(markdown, dados.get("json"), dados.get("page_count"))

    # Se a API informou o custo real, ele ganha da nossa estimativa.
    custo = _custo_da_resposta(dados)
    if custo is not None:
        res.custo_usd, res.custo_estimado = custo, False
    else:
        res.custo_usd = estimar_custo(f"datalab:{modo}", len(res.paginas) or 1)

    res.extra = {
        "modo": modo,
        "n_blocos": sum(len(p.caixas) for p in res.paginas),
        "page_count": dados.get("page_count"),
        "runtime": dados.get("runtime"),
        "parse_quality_score": dados.get("parse_quality_score"),
    }
    return res


# ── markdown paginado ────────────────────────────────────────────
# Com paginate=true a Datalab separa as páginas por uma linha
# `{0}------...` (índice 0-based da página).
MARCA_PAGINA = re.compile(r"\n*\{(\d+)\}-{6,}\n*")


def _fatiar_markdown(markdown: str) -> dict[int, str]:
    """Markdown por número de página (1-based)."""
    if not markdown:
        return {}
    partes = MARCA_PAGINA.split(markdown)
    if len(partes) == 1:  # não veio paginado
        return {1: markdown.strip()}
    # split com grupo devolve [antes, idx, texto, idx, texto, ...]
    fatias: dict[int, str] = {}
    for indice, texto in zip(partes[1::2], partes[2::2]):
        fatias[int(indice) + 1] = texto.strip()
    return fatias


def _texto_do_html(bruto: str) -> str:
    """HTML do bloco -> texto legível para a caixinha de hover."""
    if not bruto:
        return ""
    texto = re.sub(r"<br\s*/?>", "\n", bruto)
    texto = re.sub(r"</(tr|p|h[1-6]|div|li)>", "\n", texto)
    texto = re.sub(r"</t[dh]>", " | ", texto)
    texto = re.sub(r"<[^>]+>", "", texto)
    texto = re.sub(r"[ \t]+", " ", texto)
    texto = re.sub(r"\s*\|\s*\n", "\n", texto)  # fim de linha da tabela
    return re.sub(r"\n{2,}", "\n", texto).strip(" |\n")


def _limpar_marcas(markdown: str) -> str:
    """Tira as marcas de página, para exibir o documento inteiro."""
    return MARCA_PAGINA.sub("\n\n", markdown or "").strip()


def _montar_paginas(markdown: str, arvore, page_count) -> list[PaginaOCR]:
    """Junta o markdown (por página) com os blocos de layout do json.

    O json vem como uma árvore: raiz -> Page -> blocos. Ficamos nos
    blocos de primeiro nível da página: são eles o "layout" que o
    modelo enxergou. As células de tabela viriam aninhadas e só
    poluiriam a tela.
    """
    fatias = _fatiar_markdown(markdown)
    paginas: list[PaginaOCR] = []

    for i, bloco_pagina in enumerate(_paginas_do_json(arvore), start=1):
        x0, y0, x1, y1 = (bloco_pagina.get("bbox") or [0, 0, 0, 0])[:4]
        pagina = PaginaOCR(
            numero=i,
            largura=float(x1 - x0),
            altura=float(y1 - y0),
            unidade="pixel",
            markdown=fatias.get(i, ""),
        )
        for filho in bloco_pagina.get("children") or []:
            poligono = _achatar(filho.get("polygon"), filho.get("bbox"))
            if not poligono:
                continue
            pagina.caixas.append(
                Caixa(
                    texto=_texto_do_html(filho.get("html") or ""),
                    poligono=poligono,
                    tipo="bloco",
                    rotulo=filho.get("block_type") or "bloco",
                )
            )
        pagina.texto = "\n".join(c.texto for c in pagina.caixas)
        paginas.append(pagina)

    if paginas:
        return paginas

    # Sem json (ou json vazio): ainda dá para paginar o markdown.
    if fatias:
        return [
            PaginaOCR(numero=n, largura=0, altura=0, markdown=md)
            for n, md in sorted(fatias.items())
        ]
    if markdown:
        return [PaginaOCR(numero=1, largura=0, altura=0, markdown=markdown.strip())]
    return []


def _paginas_do_json(arvore) -> list[dict]:
    if not isinstance(arvore, dict):
        return []
    return [
        f
        for f in (arvore.get("children") or [])
        if isinstance(f, dict) and f.get("block_type") == "Page"
    ]


def _achatar(poligono, bbox) -> list[float]:
    """Polígono da Datalab ([[x,y], ...]) -> lista achatada de 8 números."""
    if isinstance(poligono, list) and len(poligono) >= 4:
        pontos = [float(v) for par in poligono[:4] for v in par[:2]]
        if len(pontos) == 8:
            return pontos
    if isinstance(bbox, list) and len(bbox) >= 4:
        x0, y0, x1, y1 = (float(v) for v in bbox[:4])
        return [x0, y0, x1, y0, x1, y1, x0, y1]
    return []


def _custo_da_resposta(dados: dict) -> float | None:
    """Custo real em USD, se a Datalab informou.

    Atenção: a API responde em **centavos** (`total_cost`,
    `cost_breakdown.final_cost_cents`). E um cache hit volta com custo
    zero — nesse caso devolvemos None para a UI cair na estimativa, que
    é o número que interessa na aula.
    """
    centavos = dados.get("total_cost")
    if not isinstance(centavos, (int, float)):
        bruto = dados.get("cost_breakdown")
        if isinstance(bruto, dict):
            for chave in ("final_cost_cents", "total_cost", "total", "cost"):
                valor = bruto.get(chave)
                if isinstance(valor, (int, float)):
                    centavos = valor
                    break
        elif isinstance(bruto, (int, float)):
            centavos = bruto
    if not isinstance(centavos, (int, float)) or centavos <= 0:
        return None
    return centavos / 100
