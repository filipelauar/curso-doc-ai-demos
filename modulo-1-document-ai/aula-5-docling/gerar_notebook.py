"""Gera o notebook da aula 5 (Docling)."""
import json
import pathlib

DEST = pathlib.Path(__file__).parent / "aula-5-docling.ipynb"

C = []


def _linhas(texto):
    """Cada elemento de `source` precisa terminar em \\n (menos o último)."""
    partes = texto.split("\n")
    return [l + "\n" for l in partes[:-1]] + [partes[-1]]


def md(src):
    C.append({"cell_type": "markdown", "id": f"c{len(C):02d}", "metadata": {},
              "source": _linhas(src.strip())})


def code(src):
    C.append({
        "cell_type": "code", "id": f"c{len(C):02d}", "metadata": {},
        "execution_count": None, "outputs": [], "source": _linhas(src.strip("\n")),
    })


md("""
# Docling na prática

**Curso Document AI · Aula 5**

[Docling](https://github.com/docling-project/docling) é da IBM Research, licença **MIT**
(código *e* modelos), e roda **no seu laptop** — sem API, sem chave, sem custo por página.

Converte PDF, DOCX, PPTX, XLSX, HTML, EPUB e imagens em Markdown/HTML/JSON, reconhecendo
título, parágrafo, lista, **tabela**, fórmula, figura e a **ordem de leitura**.

> Rode célula a célula (`Shift+Enter`). As células marcadas com ⏳ são lentas na primeira
> execução, porque baixam modelos.
""")

code("""
import time
from pathlib import Path

# Reusamos os mesmos PDFs da demo da aula 2 — assim dá para ver o MESMO
# documento passando por Azure, Chandra e Docling.
DADOS = Path("../aula-2-ocr-viewer/exemplos")
SAIDAS = Path("saidas"); SAIDAS.mkdir(exist_ok=True)

NOTA      = DADOS / "nota-fiscal.pdf"        # nativo, com tabela
CONTRATO  = DADOS / "contrato.pdf"           # nativo, duas colunas
ESCANEADO = DADOS / "recibo-escaneado.pdf"   # rasterizado e torto

for p in (NOTA, CONTRATO, ESCANEADO):
    print(f"{p.name:24} {p.stat().st_size/1024:6.1f} KB  {'ok' if p.exists() else 'FALTANDO'}")
""")

md("""
## 1. A conversão básica

`DocumentConverter()` escolhe sozinho o backend pela extensão do arquivo.

⏳ **A primeira execução baixa os modelos de layout e de tabela** (algumas centenas de MB).
Para uma aula, rode isto na véspera — ou, melhor ainda, `docling-tools models download`.
""")

code("""
from docling.document_converter import DocumentConverter

conversor = DocumentConverter()

t = time.perf_counter()
resultado = conversor.convert(NOTA)
doc = resultado.document
print(f"convertido em {time.perf_counter() - t:.1f}s")

markdown = doc.export_to_markdown()
print(markdown[:1500])
""")

md("""
Repare no que aconteceu com a **tabela**: ela voltou como markdown, com as colunas
alinhadas. Compare com a aula 2 — o OCR tradicional devolveu células soltas, e remontar
a tabela era trabalho nosso.

## 2. O ponto da aula: Docling não devolve uma string

Devolve um `DoclingDocument` — uma **árvore** de elementos, cada um com tipo, conteúdo e
`prov` (a página e o *bounding box* de onde veio).

Ou seja: markdown **e** grounding, do mesmo objeto.
""")

code("""
d = doc.export_to_dict()
print("chaves do documento:", [k for k in d.keys()])
print()
print(f"texts:    {len(doc.texts)}")
print(f"tables:   {len(doc.tables)}")
print(f"pictures: {len(doc.pictures)}")
print(f"páginas:  {len(doc.pages)}")
""")

code("""
# Cada elemento sabe o que é e ONDE está.
for item in doc.texts[:10]:
    prov = item.prov[0] if item.prov else None
    origem = f"pág {prov.page_no}  bbox=({prov.bbox.l:.0f},{prov.bbox.t:.0f})" if prov else "—"
    print(f"{item.label:22} {origem:28} {item.text[:52]}")
""")

code("""
(SAIDAS / "nota-fiscal.md").write_text(markdown, encoding="utf-8")
print(markdown)
""")

md("""
É essa estrutura que permite o **recorte por bloco** da aula 4: em vez de mandar a página
inteira para o modelo, você recorta só a região da tabela e manda a imagem dela.

## 3. Tabelas direto para DataFrame
""")

code("""
import pandas as pd

for i, tabela in enumerate(doc.tables):
    prov = tabela.prov[0] if tabela.prov else None
    print(f"Tabela {i + 1} — página {prov.page_no if prov else '?'}")
    display(tabela.export_to_dataframe(doc=doc))
""")

md("""
## 4. Os formatos de saída

- **Markdown** — para o modelo *ler*. É o que a aula 2 defendeu.
- **HTML** — para mostrar a um humano.
- **DocTags** — conteúdo **e** posição juntos. Grounding embutido no formato.
""")

code("""
doctags = doc.export_to_doctags()
print(doctags[:1200])
""")

code("""
# Guardar as saídas: além de útil, serve de plano B se um modelo falhar na aula.
(SAIDAS / "nota-fiscal.md").write_text(markdown, encoding="utf-8")
(SAIDAS / "nota-fiscal.html").write_text(doc.export_to_html(), encoding="utf-8")
(SAIDAS / "nota-fiscal.doctags.txt").write_text(doctags, encoding="utf-8")
print(*(f"{p.name}  {p.stat().st_size/1024:.1f} KB" for p in sorted(SAIDAS.iterdir())), sep="\\n")
""")

md("""
## 5. Quando ligar o OCR

Até aqui o Docling leu a **camada de texto nativa** — não rodou OCR nenhum, e por isso
foi rápido e exato. Agora o documento escaneado, que não tem camada de texto.

`do_ocr=True` liga o backend de OCR (por padrão, o do sistema ou o EasyOCR).
""")

code("""
from docling.datamodel.base_models import InputFormat
from docling.datamodel.pipeline_options import PdfPipelineOptions
from docling.document_converter import PdfFormatOption

# Sem OCR: o documento escaneado não tem nada a oferecer.
sem_ocr = DocumentConverter(format_options={
    InputFormat.PDF: PdfFormatOption(
        pipeline_options=PdfPipelineOptions(do_ocr=False, do_table_structure=True)
    )
})
md_sem = sem_ocr.convert(ESCANEADO).document.export_to_markdown()
print(f"SEM OCR -> {len(md_sem.strip())} caracteres")
print(repr(md_sem[:200]))
""")

code("""
# Com OCR ligado. ⏳ mais lento — ele lê os pixels.
com_ocr = DocumentConverter(format_options={
    InputFormat.PDF: PdfFormatOption(
        pipeline_options=PdfPipelineOptions(do_ocr=True, do_table_structure=True)
    )
})
t = time.perf_counter()
md_com = com_ocr.convert(ESCANEADO).document.export_to_markdown()
print(f"COM OCR -> {len(md_com.strip())} caracteres em {time.perf_counter() - t:.1f}s\\n")
print(md_com[:700])
""")

md("""
Essa é, em duas células, a lição da aula 2: **página nativa não precisa de OCR; página
escaneada não existe sem ele.**

## 6. O pipeline VLM

⏳ **Célula lenta.** Em vez de modelos especializados em cadeia, um único modelo
multimodal ponta a ponta — o `granite-docling-258M` (Apache 2.0, 258M parâmetros).

Melhor em documento difícil, bem mais lento. Se estiver demorando demais na aula,
**pule** — as saídas já estão em `saidas/`.
""")

code("""
from docling.datamodel.pipeline_options import VlmPipelineOptions
from docling.pipeline.vlm_pipeline import VlmPipeline

vlm = DocumentConverter(format_options={
    InputFormat.PDF: PdfFormatOption(
        pipeline_cls=VlmPipeline, pipeline_options=VlmPipelineOptions()
    )
})

t = time.perf_counter()
md_vlm = vlm.convert(NOTA, page_range=(1, 1)).document.export_to_markdown()
print(f"VLM em {time.perf_counter() - t:.1f}s\\n")
print(md_vlm[:1200])
""")

code("""
# Do markdown ao JSON: o texto do VLM vira entrada de um LLM com saída estruturada.
# Precisa de OPENAI_API_KEY no .env da raiz (o mesmo da aula 6).
import os
from dotenv import find_dotenv, load_dotenv
from openai import OpenAI
from pydantic import BaseModel

load_dotenv(find_dotenv(usecwd=True))


class Item(BaseModel):
    descricao: str
    quantidade: float
    valor_unitario: float
    total: float


class NotaFiscal(BaseModel):
    numero: str
    data_emissao: str
    prestador_nome: str
    prestador_cnpj: str
    tomador_nome: str
    tomador_cnpj: str
    itens: list[Item]
    valor_servicos: float
    iss: float
    valor_total: float
    vencimento: str


resposta = OpenAI().responses.parse(
    model=os.getenv("OPENAI_MODEL", "gpt-5.6-luna"),
    instructions="Extraia os campos da nota fiscal. Valores em número (ponto decimal). "
                 "Se um campo não estiver no documento, deixe vazio.",
    input=md_vlm,
    text_format=NotaFiscal,
)
nota = resposta.output_parsed

json_nota = nota.model_dump_json(indent=2)
(SAIDAS / "nota-fiscal.json").write_text(json_nota, encoding="utf-8")
print(json_nota)
""")

md("""
## 7. Chunking — a ponte para a aula 6

Para indexar um acervo você não guarda o documento inteiro: guarda **pedaços**. E o
pedaço precisa saber de onde veio.

O `HybridChunker` respeita a estrutura do documento (não corta no meio de uma tabela) e
`contextualize()` devolve o trecho **com os títulos da seção** em volta — o que melhora
muito a busca semântica.
""")

code("""
from docling.chunking import HybridChunker

chunker = HybridChunker(max_tokens=384)
chunks = list(chunker.chunk(doc))
print(f"{len(chunks)} chunks\\n")

for i, chunk in enumerate(chunks[:3]):
    paginas = sorted({p.page_no for it in chunk.meta.doc_items for p in it.prov})
    print(f"--- chunk {i}  páginas {paginas} ---")
    print(chunker.contextualize(chunk)[:420])
    print()
""")

md("""
É exatamente esta saída que a demo da aula 6 indexa: o texto contextualizado vira o
embedding, e `doc_id + página` vira a citação.

## 8. Em lote, e o comparativo
""")

code("""
linhas = []
for caminho in (NOTA, CONTRATO, ESCANEADO):
    t = time.perf_counter()
    d = conversor.convert(caminho).document
    m = d.export_to_markdown()
    linhas.append({
        "documento": caminho.name,
        "páginas": len(d.pages),
        "segundos": round(time.perf_counter() - t, 1),
        "caracteres": len(m),
        "tabelas": len(d.tables),
        "chunks": len(list(chunker.chunk(d))),
    })
    (SAIDAS / f"{caminho.stem}.md").write_text(m, encoding="utf-8")

pd.DataFrame(linhas)
""")

md("""
## Recapitulando

| | Azure DI | Chandra (Datalab) | Docling |
|---|---|---|---|
| **Onde roda** | nuvem | nuvem | **seu laptop** |
| **Custo** | $1,50–$10 / 1K pág. | ~$4 / 1K pág. | **$0** + seu compute |
| **Licença** | serviço pago | pesos restritos (< $2M) | **MIT, sem limiar** |
| **Layout** | com `prebuilt-layout` | sim | sim |
| **Grounding** | bbox por palavra | não, de graça | **bbox por elemento** |
| **Dado sai da sua infra** | sim | sim | **não** |

**Quando usar cada um**

- **Azure DI** — precisa de prebuilt (nota fiscal, RG) ou já está em Azure.
- **Chandra / OCR de LLM** — documento difícil, tabela complexa, manuscrito.
- **Docling** — dado sensível, volume alto, ou você quer controle e zero lock-in.

Na aula 6, o Docling volta como a **camada de ingestão** do acervo.
""")

nb = {
    "cells": C,
    "metadata": {
        "kernelspec": {
            "display_name": "Curso Document AI (.venv)",
            "language": "python",
            "name": "curso-doc-ai",
        },
        "language_info": {"name": "python", "version": "3.14"},
    },
    "nbformat": 4,
    "nbformat_minor": 5,
}
DEST.parent.mkdir(parents=True, exist_ok=True)
DEST.write_text(json.dumps(nb, ensure_ascii=False, indent=1), encoding="utf-8")
print("escrito:", DEST, f"({len(C)} células)")
