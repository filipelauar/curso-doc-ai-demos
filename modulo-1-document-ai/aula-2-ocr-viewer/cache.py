"""Cache das chamadas e fallback para as respostas gravadas.

Duas razões para existir:

1. Custo — trocar de página na UI não deve refazer (e repagar) o OCR.
2. Sala de aula — sem chave, ou sem internet, a demo continua rodando a
   partir dos JSONs em `exemplos/`. É o plano B da aula.
"""

from __future__ import annotations

import hashlib
from pathlib import Path

import streamlit as st

from modelos import ResultadoOCR

EXEMPLOS = Path(__file__).parent / "exemplos"


def sha(dados: bytes) -> str:
    return hashlib.sha256(dados).hexdigest()[:16]


def caminho_gravado(pdf_hash: str, provider: str) -> Path:
    return EXEMPLOS / f"{pdf_hash}.{provider}.json"


def carregar_gravado(pdf_hash: str, provider: str) -> ResultadoOCR | None:
    caminho = caminho_gravado(pdf_hash, provider)
    if not caminho.exists():
        return None
    try:
        res = ResultadoOCR.de_json(caminho.read_text(encoding="utf-8"))
    except Exception:  # noqa: BLE001 — arquivo corrompido não derruba a demo
        return None
    res.gravado = True
    return res


def gravar(pdf_hash: str, res: ResultadoOCR) -> Path:
    EXEMPLOS.mkdir(exist_ok=True)
    caminho = caminho_gravado(pdf_hash, res.provider)
    caminho.write_text(res.para_json(), encoding="utf-8")
    return caminho


@st.cache_data(show_spinner=False)
def azure_cached(pdf_bytes: bytes, pdf_hash: str) -> ResultadoOCR:
    from providers import azure_di

    return azure_di.analisar(pdf_bytes)


@st.cache_data(show_spinner=False)
def datalab_cached(
    pdf_bytes: bytes, pdf_hash: str, modo: str, max_paginas: int
) -> ResultadoOCR:
    from providers import datalab

    return datalab.analisar(pdf_bytes, modo=modo, max_paginas=max_paginas)


@st.cache_data(show_spinner=False)
def nativo_cached(pdf_bytes: bytes, pdf_hash: str) -> ResultadoOCR:
    from providers import nativo

    return nativo.analisar(pdf_bytes)
