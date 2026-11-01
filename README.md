# Curso Document AI — Demos

Código das demos do **Curso Document AI**. Os slides e o material das aulas ficam na
plataforma do curso. Aqui está só o que você roda na sua máquina.

## Demos do Módulo 1

| Aula | Pasta | O que mostra | Stack | Chave necessária |
|---|---|---|---|---|
| 2 — OCR | [`aula-2-ocr-viewer`](./modulo-1-document-ai/aula-2-ocr-viewer/) | OCR tradicional vs OCR de LLM, lado a lado | Streamlit | Azure DI e Datalab (a demo degrada sem elas) |
| 4 — Extração | [`aula-4-extracao`](./modulo-1-document-ai/aula-4-extracao/) | extração com JSON schema e grounding (valor destacado no PDF) | FastAPI + React | `OPENAI_API_KEY` |
| 5 — Frameworks | [`aula-5-docling`](./modulo-1-document-ai/aula-5-docling/) | Docling célula a célula, até uma extração para JSON | Jupyter | só na célula de extração (`OPENAI_API_KEY`); o resto roda local |
| 6 — Agentic | [`aula-6-agentic`](./modulo-1-document-ai/aula-6-agentic/) | agente respondendo sobre um acervo de documentos, com o trace passo a passo | Streamlit | `OPENAI_API_KEY` |

Cada pasta tem um `README.md` com o passo a passo da demo.

## Preparação

1. Instale o [`uv`](https://docs.astral.sh/uv/). Ele cuida do Python e das dependências.
   Para a aula 4 você também precisa do [Node.js](https://nodejs.org/) 18+.
2. Clone o repositório e crie o seu `.env` **na raiz**:

   ```bash
   git clone https://github.com/filipelauar/curso-doc-ai-demos.git
   cd curso-doc-ai-demos
   cp .env.example .env    # e preencha as chaves que for usar
   ```

3. Instale só o grupo de dependências da demo que você vai rodar:

   ```bash
   uv sync --group ocr       # aula 2
   uv sync --group extracao  # aula 4 (backend)
   uv sync --group docling   # aula 5 (puxa torch, ~2 GB)
   uv sync --group agente    # aula 6
   ```

Todas as demos leem o mesmo `.env` da raiz. **Nunca faça commit do `.env`.** Ele já está
no `.gitignore`.

## Custos

As APIs usadas nas demos são pagas: Azure AI Document Intelligence, Datalab e OpenAI.
Os documentos de exemplo são pequenos e as demos têm travas de custo (por exemplo,
`DATALAB_MAX_PAGES`), mas confira os preços de cada provedor antes de rodar em volume.

Na aula 6, baixar e indexar o acervo roda **offline e demora** (minutos, por causa do
OCR). Faça isso antes de abrir a interface.
