"""Testa quais perguntas de demonstração funcionam no acervo que você baixou.

O acervo é baixado na hora, então os documentos mudam. Este script sonda o
índice e diz se cada arquétipo de pergunta tem material para funcionar —
rode antes da aula, e ajuste as perguntas conforme a saída.

    uv run python perguntas.py
"""

from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from agente.indice import Indice


def linha(rotulo: str, ok: bool, detalhe: str = "") -> None:
    print(f"  {'OK  ' if ok else 'FRACO'}  {rotulo}{('  — ' + detalhe) if detalhe else ''}")


def main() -> int:
    ix = Indice()
    if not ix.pronto:
        print("Índice ausente. Rode antes:\n"
              "  uv run python -m ingest.baixar_corpus --fonte camara --quantidade 300\n"
              "  uv run python -m ingest.ingerir")
        return 1

    paginas = sum(d.get("paginas", 0) for d in ix.documentos.values())
    print(f"Acervo: {len(ix.documentos)} documentos · {paginas} páginas · {len(ix.chunks)} chunks\n")

    print("1. COMBINAR AS DUAS BUSCAS — um termo exato que aparece, e o conceito em volta")
    for termo in ("LGPD", "dados pessoais", "proteção de dados"):
        n = len(ix.buscar_texto(termo, max_resultados=30))
        linha(f'grep "{termo}"', n > 0, f"{n} ocorrência(s)")

    print("\n2. REGEX E NÚMEROS — valores monetários para agregar")
    achados = ix.buscar_texto(r"R\$\s?[\d.,]+", max_resultados=60)
    docs = {a["doc_id"] for a in achados}
    linha("valores em R$", len(achados) >= 5, f"{len(achados)} em {len(docs)} documento(s)")

    print("\n3. MULTI-DOCUMENTO — um tema presente em vários documentos")
    for consulta in ("prazo de entrada em vigor", "penalidades e multas", "obrigações do infrator"):
        trechos = ix.buscar_semantica(consulta, k=8)
        n_docs = len({t.doc_id for t in trechos})
        linha(f'"{consulta}"', n_docs >= 3, f"{n_docs} documento(s) distintos")

    print("\n4. LEITURA E CITAÇÃO — um documento longo o bastante para resumir")
    longos = sorted(ix.documentos.values(), key=lambda d: -d.get("paginas", 0))[:3]
    linha("documento longo", longos and longos[0].get("paginas", 0) >= 10,
          ", ".join(f"{d['doc_id']} ({d['paginas']}p)" for d in longos))

    print("\n5. O AGENTE SE RECUPERA — grep vazio, semântica resgata (a melhor da demo)")
    pares = [
        ("trabalho remoto", "teletrabalho"),
        ("home office", "teletrabalho"),
        ("propina", "corrupção"),
        ("multa", "sanção"),
    ]
    achou_par = False
    for ausente, presente in pares:
        n_a = len(ix.buscar_texto(ausente, max_resultados=3))
        n_p = len(ix.buscar_texto(presente, max_resultados=3))
        if n_a == 0 and n_p > 0:
            linha(f'"{ausente}" (0) mas "{presente}" ({n_p})', True,
                  f'use: O acervo fala sobre "{ausente}"? Se não usa esse termo, qual usa?')
            achou_par = True
    if not achou_par:
        linha("nenhum par sinônimo pronto", False,
              "procure um termo ausente cujo sinônimo exista — veja listar_documentos")

    print("\nAjuste as perguntas do app.py (lista PERGUNTAS) com o que ficou OK acima.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
