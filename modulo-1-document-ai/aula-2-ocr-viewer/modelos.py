"""Contrato comum entre os providers de OCR.

Os dois providers (Azure DI e Datalab/Chandra) devolvem coisas muito
diferentes — um devolve caixas, o outro devolve markdown. Estas
dataclasses são o denominador comum que a UI consome, para que `app.py`
não precise saber de qual provider veio o resultado.
"""

from __future__ import annotations

import json
from dataclasses import asdict, dataclass, field
from typing import Any


# ── Tabela de preços (set/2026) ──────────────────────────────────
# Fonte: portais de preço da Azure e da Datalab. Usada só como
# estimativa na UI — quando a resposta da API traz o custo real
# (Datalab manda `cost_breakdown`), esse valor tem prioridade.
PRECO_POR_1K_PAGINAS = {
    # A demo usa só o `prebuilt-read`: é o OCR tradicional puro (texto +
    # posição + confiança). O `prebuilt-layout` fica aqui como
    # referência de preço — 6,7x mais caro pela mesma página.
    "azure:prebuilt-read": 1.50,
    "azure:prebuilt-layout": 10.00,
    "datalab:fast": 4.00,
    "datalab:balanced": 4.00,
    "datalab:accurate": 10.00,
}


@dataclass
class Caixa:
    """Uma região da página com texto, na escala da página do OCR."""

    texto: str
    # polígono de 4 cantos, achatado: [x1,y1,x2,y2,x3,y3,x4,y4]
    poligono: list[float]
    tipo: str = "palavra"  # palavra | linha | bloco
    confianca: float | None = None
    # rótulo específico do provider, quando existe: o Chandra devolve o
    # tipo do bloco ("Table", "SectionHeader"...), e é o que a caixinha
    # de hover mostra.
    rotulo: str | None = None


@dataclass
class PaginaOCR:
    numero: int  # 1-based
    largura: float  # na unidade do provider
    altura: float
    unidade: str = "inch"  # "inch" para PDF, "pixel" para imagem
    caixas: list[Caixa] = field(default_factory=list)
    texto: str = ""
    markdown: str = ""


@dataclass
class ResultadoOCR:
    provider: str  # "azure" | "datalab"
    rotulo: str  # o que aparece no cabeçalho da coluna
    paginas: list[PaginaOCR] = field(default_factory=list)
    markdown: str = ""  # documento inteiro, quando o provider devolve assim
    segundos: float = 0.0
    custo_usd: float | None = None
    custo_estimado: bool = True
    erro: str | None = None
    gravado: bool = False  # veio de exemplos/, não da API
    extra: dict[str, Any] = field(default_factory=dict)

    @property
    def ok(self) -> bool:
        return self.erro is None and bool(self.paginas or self.markdown)

    def pagina(self, numero: int) -> PaginaOCR | None:
        for p in self.paginas:
            if p.numero == numero:
                return p
        return None

    # ── serialização (para as respostas gravadas) ────────────────
    def para_json(self) -> str:
        return json.dumps(asdict(self), ensure_ascii=False, indent=2)

    @classmethod
    def de_json(cls, texto: str) -> "ResultadoOCR":
        d = json.loads(texto)
        paginas = [
            PaginaOCR(
                **{**p, "caixas": [Caixa(**c) for c in p.get("caixas", [])]}
            )
            for p in d.pop("paginas", [])
        ]
        return cls(paginas=paginas, **d)


def estimar_custo(chave: str, n_paginas: int) -> float | None:
    """Custo estimado em USD para n páginas, pela tabela acima."""
    preco = PRECO_POR_1K_PAGINAS.get(chave)
    if preco is None:
        return None
    return preco * n_paginas / 1000
