# Demo da Aula 4 — Extração de informação com schema e grounding

Uma aplicação web para extrair informação estruturada de PDFs usando um **JSON schema
como contrato** e o **output estruturado** da OpenAI.

- **Editor de schema**: escreva o JSON schema e veja o formulário gerado a partir dele.
- **Vários schemas**: crie e alterne entre schemas (já vêm dois de exemplo: *Invoices* e
  *Notas Fiscais (NF-e)*, com três documentos cada).
- **Documentos**: envie PDFs ou cole texto (convertido para PDF automaticamente).
- **Grounding**: cada campo extraído volta com a **página** e a **transcrição exata** do
  trecho. Clique no campo para ver o trecho destacado no PDF (bounding box).
- **Modelo e prompts editáveis**: troque o modelo, o esforço de raciocínio, o system
  prompt e o prompt de extração na aba "Modelo & Prompt".

Os documentos de exemplo são **sintéticos**: as empresas e os dados são fictícios.

## Arquitetura

```
aula-4-extracao/
├── backend/app/          # FastAPI
│   ├── main.py           # rotas da API
│   ├── models.py         # modelos Pydantic
│   ├── storage.py        # armazenamento em arquivos (pasta data/)
│   ├── extraction.py     # chamada com output estruturado + schema aumentado com página/transcrição
│   └── pdf_utils.py      # texto do PDF e cálculo do bounding box
├── frontend/             # React + TypeScript + Tailwind
└── data/                 # schemas e documentos de exemplo; as extrações são geradas aqui
```

O truque do grounding está em `extraction.py`: antes de chamar o modelo, cada campo do
seu schema (cada campo primitivo) é trocado por um objeto `{value, page, transcription}`. O backend então
procura a transcrição no texto da página (`pdf_utils.py`) para desenhar a caixa.

## Pré-requisitos

- [`uv`](https://docs.astral.sh/uv/) (Python 3.11+)
- Node.js 18+
- `OPENAI_API_KEY` no `.env` da **raiz do repositório** (copie de `.env.example`)

## Como rodar

São dois terminais, ambos a partir da **raiz do repositório**.

**1. Backend (porta 8000)**

```bash
uv sync --group extracao
uv run uvicorn app.main:app --app-dir modulo-1-document-ai/aula-4-extracao/backend --reload --port 8000
```

**2. Frontend (porta 5173)**

```bash
cd modulo-1-document-ai/aula-4-extracao/frontend
npm install
npm run dev
```

Abra http://localhost:5173.

## Como usar

1. Escolha um schema de exemplo ou clique em **Novo** para criar o seu.
2. Edite o JSON schema no painel da esquerda. Lembre da aula: o schema também é prompt.
   Escreva descrições, use `enum` e aceite campos nulos.
3. (Opcional) Na aba **Modelo & Prompt**, ajuste o modelo e os prompts.
4. Adicione documentos (PDF ou texto).
5. Clique em **Executar Extração**.
6. Clique num campo extraído para ver de onde ele veio no PDF.

## Modelos

| Modelo | Observação |
|---|---|
| `gpt-6-luna` (padrão) | melhor custo-benefício para extração, com raciocínio ajustável |
| `gpt-5-mini` | alternativa barata, com raciocínio ajustável |
| `gpt-5.2` | sem raciocínio |

Cada extração é uma chamada paga à API da OpenAI. Os documentos de exemplo são curtos
(1–2 páginas), então o custo por extração é baixo.

## API

| Método | Rota | O que faz |
|---|---|---|
| GET | `/api/schemas` | lista os schemas |
| POST | `/api/schemas` | cria um schema |
| GET / PUT / DELETE | `/api/schemas/:id` | lê, atualiza ou apaga um schema |
| GET | `/api/schemas/:id/documents` | lista os documentos |
| POST | `/api/schemas/:id/documents` | envia um PDF |
| POST | `/api/schemas/:id/documents/text` | adiciona um documento de texto |
| DELETE | `/api/schemas/:id/documents/:docId` | apaga um documento |
| GET | `/api/schemas/:id/documents/:docId/file` | baixa o PDF |
| POST | `/api/schemas/:id/extract` | roda a extração |
| GET | `/api/schemas/:id/extractions` | lista as extrações |
| GET | `/api/schemas/:id/extractions/:docId` | lê uma extração |
