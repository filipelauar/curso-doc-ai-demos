"""Os eventos que o loop emite para a UI.

O loop é um *generator* de eventos — é isso que permite mostrar o trace
do agente ao vivo, passo a passo, em vez de só o resultado final.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Literal

Tipo = Literal["texto", "ferramenta", "resultado", "uso", "fim", "erro"]


@dataclass
class Evento:
    tipo: Tipo
    texto: str = ""
    # ferramenta / resultado
    nome: str = ""
    argumentos: dict[str, Any] = field(default_factory=dict)
    id_chamada: str = ""
    erro: bool = False
    segundos: float = 0.0
    # uso
    uso: dict[str, int] = field(default_factory=dict)
    turno: int = 0
