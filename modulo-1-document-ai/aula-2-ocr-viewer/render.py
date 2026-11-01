"""Renderização da página do PDF como imagem.

O ponto delicado desta demo aparece na hora de casar os polígonos do
OCR com a imagem: o Azure Document Intelligence devolve os polígonos em
POLEGADAS quando a entrada é PDF e em PIXELS quando é imagem (e a
Datalab devolve em pixels do render dela). Em vez de tratar cada caso,
`viewer.py` usa a própria página como sistema de coordenadas
(`PaginaOCR.largura`/`altura`, que vêm na mesma unidade do polígono) —
agnóstico de unidade e correto em qualquer DPI.
"""

from __future__ import annotations

import io

import fitz  # pymupdf
from PIL import Image


def n_paginas(pdf_bytes: bytes) -> int:
    with fitz.open(stream=pdf_bytes, filetype="pdf") as doc:
        return doc.page_count


def pagina_para_imagem(pdf_bytes: bytes, numero: int, dpi: int = 150) -> Image.Image:
    """Renderiza a página `numero` (1-based) como imagem PIL."""
    with fitz.open(stream=pdf_bytes, filetype="pdf") as doc:
        page = doc[numero - 1]
        pix = page.get_pixmap(dpi=dpi)
        return Image.frombytes("RGB", (pix.width, pix.height), pix.samples)


def imagem_para_pdf(dados: bytes) -> bytes:
    """Converte uma imagem solta (JPG/PNG) num PDF de uma página.

    Assim o resto da demo lida com um formato só.
    """
    doc = fitz.open()
    img = fitz.open(stream=dados)
    rect = img[0].rect
    pdf = fitz.open("pdf", img.convert_to_pdf())
    page = doc.new_page(width=rect.width, height=rect.height)
    page.show_pdf_page(rect, pdf, 0)
    return doc.tobytes()


def para_png(imagem: Image.Image) -> bytes:
    buf = io.BytesIO()
    imagem.save(buf, format="PNG")
    return buf.getvalue()
