# Demo da Aula 5 — Docling

Notebook para rodar **célula a célula ao vivo**. Cada célula markdown é a fala; cada
célula de código mostra uma coisa só.

## Como rodar

```bash
uv sync --group docling
uv run jupyter lab
# abrir modulo-1-document-ai/aula-5-docling/aula-5-docling.ipynb
```

**Sem chave, sem API, sem custo por página.** O Docling roda todo local — dá para
desconectar a internet no meio da aula para provar o ponto (depois que os modelos já
baixaram). A única exceção é a célula de **extração para JSON** (logo depois do VLM),
que chama a OpenAI e precisa de `OPENAI_API_KEY` no `.env` da raiz — a mesma da aula 6.

## ⚠️ Antes da aula

A primeira execução **baixa os modelos** (layout, tabela, OCR e, se você rodar a célula
do VLM, o `granite-docling-258M`). Faça isso na véspera:

```bash
uv run docling-tools models download
uv run jupyter nbconvert --to notebook --execute --output /tmp/ensaio.ipynb aula-5-docling.ipynb
```

O segundo comando é o ensaio geral: roda o notebook inteiro e falha se alguma célula
quebrar. Tempo medido neste repo: **~2 min no total**, sendo ~73s só a célula do VLM.

## Roteiro

| # | Célula | O que mostra |
|---|---|---|
| 1 | Setup | reusa os **mesmos PDFs da aula 2** — o mesmo documento nos três motores |
| 2 | Conversão básica | markdown pronto, **com a tabela montada** |
| 3 | `export_to_dict` | o `DoclingDocument` é uma **árvore**, não uma string |
| 4 | `prov` | cada elemento sabe a **página e o bbox** — markdown *e* grounding |
| 5 | Tabelas | `export_to_dataframe()` |
| 6 | DocTags | o formato com posição embutida |
| 7 | **Sem OCR no escaneado** | **0 caracteres** |
| 8 | **Com OCR no escaneado** | **299 caracteres**, incluindo o carimbo "PAGO" |
| 9 | Pipeline VLM | `granite-docling-258M` ponta a ponta (⏳ ~73s) |
| 10 | **Extração para JSON** | o markdown do VLM + schema Pydantic → JSON via OpenAI (salvo em `saidas/nota-fiscal.json`) |
| 11 | `HybridChunker` | a **ponte para a aula 6** |
| 12 | Lote | comparativo dos 3 documentos em `DataFrame` |

## O momento da aula

As células 7 e 8, em sequência, são a lição da aula 2 em 10 segundos:

```
SEM OCR -> 0 caracteres
COM OCR -> 299 caracteres em 1.9s
```

**Página nativa não precisa de OCR. Página escaneada não existe sem ele.**

## Se algo falhar ao vivo

- As saídas ficam em `saidas/` a partir da célula 6 — dá para ler do disco e seguir.
- A célula do VLM é a única realmente lenta. **Pule sem dó** se o tempo apertar.
- Não atualize a versão do Docling entre o ensaio e a aula: os nomes em
  `pipeline_options` mudam entre versões. O `uv.lock` existe para isso.

## Regerar o notebook

O notebook é gerado por script, para o conteúdo ficar versionado como texto legível:

```bash
uv run python gerar_notebook.py
```
