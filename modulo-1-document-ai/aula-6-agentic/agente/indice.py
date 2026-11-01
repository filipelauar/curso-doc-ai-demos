"""O índice do acervo: manifesto, chunks, embeddings e as duas buscas.

Formato em disco — tudo texto ou numpy, nenhum banco:

    indice/manifesto.jsonl   um documento por linha (id, arquivo, hash, páginas)
    indice/chunks.jsonl      um chunk por linha (doc_id, páginas, texto)
    indice/embeddings.npy    float32 [N, dim], L2-normalizado
    indice/markdown/<id>.md  o documento convertido

Com algumas centenas de PDFs isso dá ~10k–40k chunks, e `embeddings @ q`
em numpy leva menos de 10 ms. FAISS/Chroma seriam complexidade (e uma
dependência a mais para falhar em sala) sem ganho nenhum nesta escala.

E `.jsonl` + `.md` é inspecionável ao vivo: `head chunks.jsonl` é um slide.
"""

from __future__ import annotations

import json
import os
import re
from dataclasses import dataclass
from functools import lru_cache
from pathlib import Path

import numpy as np

AQUI = Path(__file__).resolve().parent.parent
INDICE = AQUI / "indice"
ESPACOS = re.compile(r"[ \t]{2,}")

MODELO_PADRAO = "intfloat/multilingual-e5-base"


# ─────────────────────────────────────────────────────────────────
# Embeddings
# ─────────────────────────────────────────────────────────────────
# ATENÇÃO: os modelos e5 exigem os prefixos "query: " e "passage: ".
# Esquecer isso não dá erro — só degrada o recall, em silêncio. Por isso
# tudo passa por estas duas funções, e nada chama encode() direto.
@lru_cache(maxsize=1)
def _encoder(nome: str | None = None):
    from sentence_transformers import SentenceTransformer

    return SentenceTransformer(nome or os.getenv("EMBEDDING_MODEL", MODELO_PADRAO))


def _prefixo(nome: str) -> tuple[str, str]:
    if "e5" in nome.lower():
        return "query: ", "passage: "
    return "", ""  # bge-m3 e outros não usam prefixo


def embutir_passagens(textos: list[str], nome: str | None = None) -> np.ndarray:
    nome = nome or os.getenv("EMBEDDING_MODEL", MODELO_PADRAO)
    _, pref = _prefixo(nome)
    vetores = _encoder(nome).encode(
        [pref + t for t in textos],
        batch_size=32, show_progress_bar=False, normalize_embeddings=True,
    )
    return np.asarray(vetores, dtype=np.float32)


def embutir_consulta(texto: str, nome: str | None = None) -> np.ndarray:
    nome = nome or os.getenv("EMBEDDING_MODEL", MODELO_PADRAO)
    pref, _ = _prefixo(nome)
    vetor = _encoder(nome).encode([pref + texto], normalize_embeddings=True)
    return np.asarray(vetor, dtype=np.float32)[0]


# ─────────────────────────────────────────────────────────────────
# Índice
# ─────────────────────────────────────────────────────────────────
@dataclass
class Trecho:
    chunk_id: str
    doc_id: str
    titulo: str
    pagina_ini: int
    pagina_fim: int
    texto: str
    score: float = 0.0

    @property
    def citacao(self) -> str:
        if self.pagina_ini == self.pagina_fim:
            return f"[{self.doc_id} p.{self.pagina_ini}]"
        return f"[{self.doc_id} p.{self.pagina_ini}-{self.pagina_fim}]"


class Indice:
    """Carrega o índice na memória. Read-only."""

    def __init__(self, caminho: Path | None = None):
        self.caminho = Path(caminho or INDICE)
        self.documentos: dict[str, dict] = {}
        self.chunks: list[dict] = []
        self.embeddings: np.ndarray | None = None
        self._markdown: dict[str, str] = {}
        self._carregar()

    # ── carga ────────────────────────────────────────────────────
    def _carregar(self) -> None:
        manifesto = self.caminho / "manifesto.jsonl"
        if manifesto.exists():
            for linha in manifesto.read_text(encoding="utf-8").splitlines():
                if linha.strip():
                    d = json.loads(linha)
                    self.documentos[d["doc_id"]] = d

        chunks = self.caminho / "chunks.jsonl"
        if chunks.exists():
            for linha in chunks.read_text(encoding="utf-8").splitlines():
                if linha.strip():
                    self.chunks.append(json.loads(linha))

        emb = self.caminho / "embeddings.npy"
        if emb.exists():
            self.embeddings = np.load(emb)
            if len(self.embeddings) != len(self.chunks):
                # linha i de embeddings.npy == linha i de chunks.jsonl.
                # Se isso quebrou, o índice está inconsistente.
                raise RuntimeError(
                    f"Índice inconsistente: {len(self.embeddings)} embeddings para "
                    f"{len(self.chunks)} chunks. Rode a ingestão de novo com --forcar."
                )

    @property
    def pronto(self) -> bool:
        return bool(self.chunks) and self.embeddings is not None

    def markdown(self, doc_id: str) -> str:
        if doc_id not in self._markdown:
            caminho = self.caminho / "markdown" / f"{doc_id}.md"
            texto = caminho.read_text(encoding="utf-8") if caminho.exists() else ""
            # Texto justificado no PDF vira "art.   37" no markdown — e aí o
            # grep por "art. 37" volta vazio. Colapsamos os espaços na carga.
            self._markdown[doc_id] = ESPACOS.sub(" ", texto)
        return self._markdown[doc_id]

    def _trecho(self, c: dict, score: float = 0.0) -> Trecho:
        doc = self.documentos.get(c["doc_id"], {})
        return Trecho(
            chunk_id=c["chunk_id"], doc_id=c["doc_id"],
            titulo=doc.get("titulo", c["doc_id"]),
            pagina_ini=c.get("pagina_ini", 1), pagina_fim=c.get("pagina_fim", 1),
            texto=c["texto"], score=score,
        )

    # ── busca semântica ──────────────────────────────────────────
    def buscar_semantica(self, consulta: str, k: int = 6, doc_id: str | None = None) -> list[Trecho]:
        if not self.pronto:
            return []
        q = embutir_consulta(consulta)
        scores = self.embeddings @ q  # vetores já normalizados -> cosseno

        if doc_id:
            mascara = np.array([c["doc_id"] == doc_id for c in self.chunks])
            if not mascara.any():
                return []
            scores = np.where(mascara, scores, -np.inf)

        k = max(1, min(int(k), 15))
        melhores = np.argpartition(-scores, min(k, len(scores) - 1))[:k]
        melhores = melhores[np.argsort(-scores[melhores])]
        return [self._trecho(self.chunks[i], float(scores[i]))
                for i in melhores if np.isfinite(scores[i])]

    # ── busca textual (grep) ─────────────────────────────────────
    def buscar_texto(self, padrao: str, ignorar_caixa: bool = True,
                     max_resultados: int = 20, doc_id: str | None = None) -> list[dict]:
        """Regex sobre o markdown dos documentos, com `re` em memória.

        Não usamos `subprocess grep`: além de portabilidade, passar um
        padrão escrito pelo modelo para o shell seria injeção de comando.
        """
        try:
            rx = re.compile(padrao, re.IGNORECASE if ignorar_caixa else 0)
        except re.error as exc:
            return [{"erro": f"regex inválida: {exc}"}]

        alvos = [doc_id] if doc_id else list(self.documentos)
        achados: list[dict] = []
        for did in alvos:
            texto = self.markdown(did)
            if not texto:
                continue
            for m in rx.finditer(texto):
                ini, fim = max(0, m.start() - 160), min(len(texto), m.end() + 160)
                achados.append({
                    "doc_id": did,
                    "titulo": self.documentos.get(did, {}).get("titulo", did),
                    "match": m.group(0)[:120],
                    "contexto": texto[ini:fim].replace("\n", " ").strip(),
                    "pagina": self._pagina_do_offset(did, m.start()),
                })
                if len(achados) >= max_resultados:
                    return achados
        return achados

    def _pagina_do_offset(self, doc_id: str, offset: int) -> int:
        """Aproxima a página pela posição no markdown, usando os chunks."""
        texto = self.markdown(doc_id)
        if not texto:
            return 1
        fracao = offset / max(1, len(texto))
        paginas = self.documentos.get(doc_id, {}).get("paginas", 1)
        return max(1, min(paginas, int(fracao * paginas) + 1))

    # ── leitura e listagem ───────────────────────────────────────
    def ler_documento(self, doc_id: str, pagina_ini: int = 1,
                      pagina_fim: int | None = None) -> str:
        texto = self.markdown(doc_id)
        if not texto:
            return ""
        paginas = self.documentos.get(doc_id, {}).get("paginas", 1)
        pagina_fim = min(pagina_fim or pagina_ini + 4, paginas, pagina_ini + 9)
        if paginas <= 1:
            return texto
        # O markdown não guarda quebras de página; fatiamos proporcionalmente.
        por_pagina = len(texto) / paginas
        ini = int((pagina_ini - 1) * por_pagina)
        fim = int(pagina_fim * por_pagina)
        return texto[ini:fim]

    def listar(self, filtro: str | None = None) -> list[dict]:
        docs = list(self.documentos.values())
        if filtro:
            f = filtro.lower()
            docs = [d for d in docs
                    if f in (d.get("titulo", "") + " " + d.get("resumo", "")).lower()]
        return docs
