# Demo da Aula 6 — Agente sobre um acervo de documentos

Um agente **codado na mão** (loop de tool use na **Responses API da OpenAI**, com o
modelo `gpt-5.6-luna`, sem framework) que responde perguntas sobre centenas de
documentos públicos brasileiros. A tela mostra
**cada passo**: qual ferramenta ele escolheu, com quais argumentos, o que voltou — até
a resposta final com citação de documento e página.

## Como rodar

```bash
uv sync --group agente
cd modulo-1-document-ai/aula-6-agentic

# 1. baixar o acervo (offline, alguns minutos)
uv run python -m ingest.baixar_corpus --fonte camara --quantidade 300

# 2. converter e indexar (offline, DEMORA — é o passo pesado)
uv run python -m ingest.ingerir

# 3. conferir se as perguntas de demonstração funcionam neste acervo
uv run python perguntas.py

# 4. subir a interface
uv run streamlit run app.py
```

Chave no `.env` da **raiz do repositório**: `OPENAI_API_KEY`.
Os embeddings rodam **local** (`intfloat/multilingual-e5-base`) — nenhuma chave a mais.

> ⚠️ Use o id completo **`gpt-5.6-luna`**. O alias curto `gpt-5.6` roteia para o
> `gpt-5.6-sol`, que é outro modelo (e bem mais caro).

> ⚠️ **Os passos 1 e 2 são offline e demoram.** Rode na véspera. Medido neste repo:
> 25 documentos / 219 páginas levaram ~7 min, sendo 214s num único PDF de 46 páginas
> escaneadas — OCR é caro, e é bom que os alunos vejam isso.

## O acervo

Três fontes públicas, sem chave e sem CAPTCHA:

| `--fonte` | O que é | Por que |
|---|---|---|
| **`camara`** (padrão) | Projetos de lei da Câmara dos Deputados | Centenas de documentos, **temas muito variados** — é a diversidade que faz busca semântica e grep serem úteis de formas diferentes. Vem com ementa como ground truth. |
| `pncp` | Editais e contratos do Portal Nacional de Contratações Públicas | Documentos maiores e mais ricos em layout (tabelas, anexos). **A API é instável** — já respondeu 504 por horas seguidas. |
| `bcb` | Atas do Copom | O download mais confiável, mas documentos homogêneos, o que enfraquece a demonstração de busca semântica. |

Os metadados da listagem ficam em `corpus/_metadados.json` e servem de **ground truth
de graça** para conferir as respostas do agente.

## As ferramentas

| Tool | Para que serve |
|---|---|
| 🧭 `buscar_semantica` | por **significado** — sinônimo e paráfrase |
| 🔎 `buscar_texto` | **regex**, para termo exato: valores, datas, leis, nomes |
| 📖 `ler_documento` | **abrir** o documento numa faixa de páginas |
| 🗂️ `listar_documentos` | se orientar no acervo |

As descrições das tools **são o conteúdo do slide** "as duas famílias de busca" — é
lendo-as que o modelo decide qual usar. Mexer nelas muda o comportamento da demo.

## As cinco perguntas, e o que cada uma exercita

1. **Combinar as duas buscas** — grep num termo exato, depois semântica em volta.
2. **Regex e números** — `R\$\s?[\d.,]+` e agregação.
3. **Multi-documento** — cruzar 3+ documentos. É o que RAG de um shot não faz.
4. **Leitura e citação** — resumir um documento longo citando página por página.
5. **O agente se recupera** — o grep volta **vazio**, e o agente parte sozinho para a
   busca semântica, descobre o termo que os documentos realmente usam, e volta ao grep.

> **A pergunta 5 é a melhor da demo.** É ela que mostra, ao vivo, por que um agente
> ganha de uma pipeline fixa. Confirme com `perguntas.py` que ela funciona no seu
> acervo antes da aula — o script sugere pares de sinônimos que existem ali.

## Prompt caching, ao vivo — no modo **implícito**

Na OpenAI o cache é **implícito**: não existe `cache_control` para marcar. Basta manter
o prefixo estável — `instructions` (o system prompt) e `tools` vão primeiro e nunca
mudam — que o provider reaproveita sozinho, **sem custo de escrita**. Passamos também um
`prompt_cache_key` estável, que ajuda a rotear as chamadas para o mesmo cache.

A barra lateral mostra **"Lidos do cache"** subindo a partir do segundo turno — é o
slide de `imagens/prompt_cache.png` acontecendo na frente da turma, no modo implícito
(o lado da Anthropic, explícito, fica no slide da aula 4 como comparação).

| | |
|---|---|
| Entrada | **US\$ 0,20** / 1M tokens |
| Entrada **em cache** | **US\$ 0,02** / 1M tokens — **0,1×** |
| Saída | **US\$ 1,20** / 1M tokens |
| Prefixo mínimo para cachear | **1.024 tokens** |
| TTL | **30 min** desde o último uso |

Acima de 272K tokens de entrada a OpenAI cobra 2× a entrada e 1,5× a saída — a demo fica
muito abaixo disso.

## Raciocínio

`gpt-5.6-luna` tem parâmetro de esforço (`none`, `low`, `medium`, `high`, `xhigh`,
`max`), exposto no slider da barra lateral. **Tokens de raciocínio são cobrados como
saída** e aumentam o tempo morto na aula — por isso o padrão é `low`. Suba para `medium`
nas perguntas que cruzam vários documentos.

## Se algo falhar ao vivo

| Risco | Mitigação |
|---|---|
| Índice ausente | A tela mostra o comando exato. Mantenha um índice pequeno já pronto. |
| PNCP fora do ar | `--fonte camara` (é o padrão justamente por isso). |
| Agente entra em loop | `MAX_TURNOS=12` e `MAX_CHAMADAS=25` em `agente/loop.py`. |
| Ferramenta quebra | O erro volta como `tool_result` com `is_error` — o agente se recupera, e isso é ótimo de mostrar. |
| Latência alta | Baixe o esforço de raciocínio para `none` ou `low` na barra lateral. |
| Sem chave / sem rede | **Modo replay**: ligue "Gravar o trace" durante o ensaio e depois use o toggle "Modo replay". É o seguro mais valioso da demo. |

## Estrutura

```
app.py                    UI Streamlit — o trace passo a passo
perguntas.py              testa quais perguntas funcionam no acervo baixado
agente/loop.py            o loop de tool use na Responses API (generator) + replay
agente/ferramentas.py     schemas das tools e execução
agente/indice.py          manifesto, chunks, embeddings, as duas buscas
agente/prompts.py         o system prompt (a "parte fixa" que vai para o cache)
agente/eventos.py         os eventos que o loop emite
ingest/baixar_corpus.py   camara | pncp | bcb
ingest/ingerir.py         PDF -> markdown -> chunks -> embeddings (incremental)
corpus/                   os PDFs (não versionado)
indice/                   os artefatos do índice (não versionado)
traces/                   execuções gravadas, para o modo replay
```

### Por que numpy e não FAISS

Algumas centenas de PDFs dão ~10k–40k chunks. `embeddings @ consulta` em numpy leva
menos de 10 ms. FAISS/Chroma seriam complexidade e uma dependência a mais para falhar
em sala, sem ganho nenhum nesta escala.

E o formato é **inspecionável ao vivo** — `head indice/chunks.jsonl` é um slide:

```
indice/manifesto.jsonl    um documento por linha (id, arquivo, hash, páginas)
indice/chunks.jsonl       um chunk por linha (doc_id, páginas, texto)
indice/embeddings.npy     float32 [N, 768], L2-normalizado
indice/markdown/<id>.md   o documento convertido
```

**A ordem importa:** linha `i` de `embeddings.npy` é a linha `i` de `chunks.jsonl`.
`Indice` valida isso na carga e falha alto se estiver inconsistente.

### Detalhes que decidem o resultado

- **Prefixos do e5.** O modelo exige `"query: "` na pergunta e `"passage: "` no chunk.
  Esquecer não dá erro — só **degrada o recall em silêncio**. Por isso tudo passa por
  `embutir_consulta` / `embutir_passagens`, e nada chama `encode()` direto.
- **Ingestão incremental.** O SHA-256 do arquivo entra no manifesto; documento com o
  mesmo hash é pulado. Reindexar um acervo que cresce não custa o acervo inteiro.
- **Cobertura.** Documento que falha na conversão vai para `indice/falhas.json`, e a
  barra lateral avisa. Um documento que falhou e ninguém viu é uma resposta errada
  esperando para acontecer.
- **`re`, não `subprocess grep`.** Além de portabilidade, passar um padrão escrito pelo
  modelo para o shell seria injeção de comando.
