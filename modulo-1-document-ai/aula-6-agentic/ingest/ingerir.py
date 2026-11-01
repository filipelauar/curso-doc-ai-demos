"""Converte o acervo em índice: PDF -> markdown -> chunks -> embeddings.

Esta é a "metade invisível" da aula 6. É offline, demora, e é onde mora a
qualidade — o agente é só a parte visível.

    uv run python -m ingest.ingerir              # incremental
    uv run python -m ingest.ingerir --forcar     # reprocessa tudo

Incremental de verdade: o hash SHA-256 do arquivo entra no manifesto, e
um documento já ingerido com o mesmo hash é pulado. Reindexar um acervo
que cresce não pode custar o acervo inteiro toda noite.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import sys
import time
from datetime import datetime, timezone
from pathlib import Path

import numpy as np

AQUI = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(AQUI))

from agente.indice import embutir_passagens  # noqa: E402

CORPUS = AQUI / "corpus"
INDICE = AQUI / "indice"
MAX_TOKENS_CHUNK = 384


def sha256(caminho: Path) -> str:
    h = hashlib.sha256()
    with caminho.open("rb") as f:
        for bloco in iter(lambda: f.read(1 << 20), b""):
            h.update(bloco)
    return h.hexdigest()


def carregar_metadados(corpus: Path) -> dict[str, dict]:
    caminho = corpus / "_metadados.json"
    if not caminho.exists():
        return {}
    try:
        return {m["arquivo"]: m for m in json.loads(caminho.read_text(encoding="utf-8"))}
    except (ValueError, KeyError):
        return {}


def ler_jsonl(caminho: Path) -> list[dict]:
    if not caminho.exists():
        return []
    return [json.loads(l) for l in caminho.read_text(encoding="utf-8").splitlines() if l.strip()]


def escrever_jsonl(caminho: Path, registros: list[dict]) -> None:
    caminho.write_text(
        "".join(json.dumps(r, ensure_ascii=False) + "\n" for r in registros), encoding="utf-8"
    )


def ingerir(corpus: Path, indice: Path, forcar: bool = False, limite: int | None = None) -> int:
    indice.mkdir(parents=True, exist_ok=True)
    (indice / "markdown").mkdir(exist_ok=True)

    from docling.chunking import HybridChunker
    from docling.document_converter import DocumentConverter

    conversor = DocumentConverter()
    chunker = HybridChunker(max_tokens=MAX_TOKENS_CHUNK)
    metadados = carregar_metadados(corpus)

    manifesto = {d["doc_id"]: d for d in ler_jsonl(indice / "manifesto.jsonl")}
    chunks_antigos = ler_jsonl(indice / "chunks.jsonl")
    por_hash = {d["sha256"]: d["doc_id"] for d in manifesto.values()}

    pdfs = sorted(p for p in corpus.glob("*.pdf"))
    if limite:
        pdfs = pdfs[:limite]
    if not pdfs:
        print(f"Nenhum PDF em {corpus}. Rode antes:\n"
              f"  uv run python -m ingest.baixar_corpus --fonte camara")
        return 0

    print(f"{len(pdfs)} PDFs em {corpus}\n")

    novos_chunks: list[dict] = []
    falhas: list[dict] = []
    processados = pulados = 0

    for i, pdf in enumerate(pdfs, 1):
        h = sha256(pdf)
        if not forcar and h in por_hash:
            pulados += 1
            continue

        doc_id = pdf.name.split("__")[0]
        meta = metadados.get(pdf.name, {})
        t = time.perf_counter()
        try:
            doc = conversor.convert(pdf).document
            markdown = doc.export_to_markdown()
            pedacos = list(chunker.chunk(doc))
        except Exception as exc:  # noqa: BLE001 — um PDF ruim não derruba a ingestão
            falhas.append({"arquivo": pdf.name, "erro": f"{type(exc).__name__}: {exc}"})
            print(f"[{i:4}/{len(pdfs)}] FALHOU  {pdf.name[:60]} — {type(exc).__name__}")
            continue

        (indice / "markdown" / f"{doc_id}.md").write_text(markdown, encoding="utf-8")
        n_paginas = len(doc.pages) or 1

        # Chunks antigos deste doc_id saem (reingestão substitui).
        chunks_antigos = [c for c in chunks_antigos if c["doc_id"] != doc_id]

        for j, pedaco in enumerate(pedacos):
            paginas = sorted({p.page_no for it in pedaco.meta.doc_items for p in it.prov}) or [1]
            novos_chunks.append({
                "chunk_id": f"{doc_id}#{j:04d}",
                "doc_id": doc_id,
                "ordem": j,
                "pagina_ini": paginas[0],
                "pagina_fim": paginas[-1],
                # contextualize() traz os títulos da seção junto — melhora muito
                # a busca semântica, porque o chunk deixa de ser um trecho solto.
                "texto": chunker.contextualize(pedaco),
            })

        manifesto[doc_id] = {
            "doc_id": doc_id,
            "arquivo": pdf.name,
            "titulo": meta.get("titulo") or meta.get("objeto") or doc_id,
            "resumo": (meta.get("ementa") or meta.get("objeto") or "")[:400],
            "fonte": meta.get("fonte", "?"),
            "paginas": n_paginas,
            "sha256": h,
            "chars": len(markdown),
            "n_chunks": len(pedacos),
            "url": meta.get("url"),
            "ingerido_em": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        }
        processados += 1
        print(f"[{i:4}/{len(pdfs)}] {time.perf_counter() - t:5.1f}s  "
              f"{n_paginas:3} pág  {len(pedacos):3} chunks  {pdf.name[:56]}")

    if not processados:
        print(f"\nNada novo ({pulados} já estavam no índice). Use --forcar para reprocessar.")
        return 0

    todos = chunks_antigos + novos_chunks
    print(f"\nGerando embeddings de {len(todos)} chunks...")
    t = time.perf_counter()
    vetores = embutir_passagens([c["texto"] for c in todos])
    print(f"  {vetores.shape} em {time.perf_counter() - t:.1f}s")

    # A ordem importa: linha i de embeddings.npy == linha i de chunks.jsonl.
    escrever_jsonl(indice / "chunks.jsonl", todos)
    np.save(indice / "embeddings.npy", vetores)
    escrever_jsonl(indice / "manifesto.jsonl", list(manifesto.values()))
    (indice / "embeddings_meta.json").write_text(json.dumps({
        "modelo": __import__("os").getenv("EMBEDDING_MODEL", "intfloat/multilingual-e5-base"),
        "dim": int(vetores.shape[1]),
        "n": int(vetores.shape[0]),
        "criado_em": datetime.now(timezone.utc).isoformat(timespec="seconds"),
    }, ensure_ascii=False, indent=2), encoding="utf-8")

    if falhas:
        (indice / "falhas.json").write_text(
            json.dumps(falhas, ensure_ascii=False, indent=2), encoding="utf-8")

    print(f"\n{'=' * 62}")
    print(f"documentos no índice : {len(manifesto)}")
    print(f"processados agora    : {processados}   pulados: {pulados}")
    print(f"chunks               : {len(todos)}")
    print(f"páginas              : {sum(d['paginas'] for d in manifesto.values())}")
    if falhas:
        # Cobertura é o que importa: um documento que falhou e ninguém viu
        # é uma resposta errada esperando para acontecer.
        print(f"FALHAS               : {len(falhas)}  -> {indice / 'falhas.json'}")
    print(f"{'=' * 62}")
    return processados


def main() -> int:
    ap = argparse.ArgumentParser(description="Converte e indexa o acervo")
    ap.add_argument("--corpus", type=Path, default=CORPUS)
    ap.add_argument("--indice", type=Path, default=INDICE)
    ap.add_argument("--forcar", action="store_true", help="reprocessa tudo")
    ap.add_argument("--limite", type=int, help="processa só os N primeiros (para testar)")
    args = ap.parse_args()
    ingerir(args.corpus, args.indice, args.forcar, args.limite)
    return 0


if __name__ == "__main__":
    sys.exit(main())
