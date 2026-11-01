"""Providers de OCR da demo.

Cada provider expõe `analisar(pdf_bytes, **opcoes) -> ResultadoOCR` e
nunca levanta exceção para fora: erro vira `ResultadoOCR.erro`, para que
uma coluna quebrada não derrube a outra durante a aula.
"""

import os

from . import azure_di, datalab, nativo

PROVIDERS = {
    "azure": azure_di,
    "datalab": datalab,
    "nativo": nativo,
}


def disponiveis() -> dict[str, bool]:
    """Quais providers têm chave configurada no .env.

    `nativo` não precisa de chave — está sempre disponível, e é o
    fallback da coluna da esquerda.
    """
    return {
        "azure": bool(os.getenv("AZURE_DI_ENDPOINT") and os.getenv("AZURE_DI_KEY")),
        "datalab": bool(os.getenv("DATALAB_API_KEY")),
        "nativo": True,
    }
