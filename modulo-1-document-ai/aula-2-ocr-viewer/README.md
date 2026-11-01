# Demo da Aula 2 — OCR tradicional vs OCR de LLM

Compara, lado a lado e no mesmo documento. As duas colunas têm a mesma forma — três abas, começando pelo que o motor viu na página:

- **Esquerda — OCR tradicional** (Azure AI Document Intelligence, `prebuilt-read`):
  *Caixas* (uma por **palavra**, sobre a página), *Texto por linha* (a saída crua) e
  *Markdown remontado* (o que precisou ser montado **por nós** a partir das caixas).
- **Direita — OCR de LLM** (Chandra, pela API da Datalab): *Layout* (os **blocos** que o
  modelo enxergou, sobre a página), *Renderizado* e *Markdown bruto* — já com títulos e
  tabelas montados pelo modelo.

**Passe o mouse sobre as caixas dos dois lados.** À esquerda sai a transcrição da
palavra, a **confiança** e a **bbox**; à direita, o **tipo do bloco** (`Table`,
`SectionHeader`...) e o texto inteiro que o modelo leu ali. É a forma mais direta de
mostrar a diferença de granularidade: de um lado a unidade é a *palavra*, do outro é o
*bloco* — e é por isso que um devolve markdown pronto e o outro não.

Embaixo de cada coluna: tempo de resposta, número de páginas e custo estimado.

## Como rodar

```bash
uv sync --group ocr
uv run streamlit run modulo-1-document-ai/aula-2-ocr-viewer/app.py
```

As chaves ficam no `.env` da **raiz do repositório** (copie de `.env.example`):

```
AZURE_DI_ENDPOINT=  AZURE_DI_KEY=
DATALAB_API_KEY=    DATALAB_MODE=balanced  DATALAB_MAX_PAGES=5
```

## Sem chave: a demo continua funcionando

| Situação | O que acontece |
|---|---|
| Existe resposta gravada em `exemplos/` | usa a gravação, sem chamar API |
| Sem `AZURE_DI_KEY` | a coluna da esquerda cai para a **camada de texto nativa** do PDF (pymupdf) — que não é OCR, e a tela diz isso |
| Sem `DATALAB_API_KEY` | a coluna da direita avisa. Não há substituto local honesto para um VLM |
| Toggle "Modo offline" | força as duas colunas a usarem só as gravações |

O fallback da esquerda é, ele próprio, uma aula: **numa página nativa digital a camada
de texto é melhor e mais barata que qualquer OCR**. Abra `recibo-escaneado.pdf` para
ver o caso oposto — sem camada de texto, aí o OCR é obrigatório.

### Gravar respostas para dar a aula offline

Com as chaves configuradas, rode uma vez cada documento e clique em
**"Gravar estas respostas em exemplos/"**. Os JSONs ficam versionados e a demo passa a
funcionar sem internet. **Faça isso na véspera da aula** — é o plano B mais importante.

## Documentos de exemplo

| Arquivo | O que exercita |
|---|---|
| `nota-fiscal.pdf` | nativo digital, com **tabela** — compare como cada motor devolve a tabela |
| `contrato.pdf` | nativo, **duas colunas** — compare a ordem de leitura |
| `recibo-escaneado.pdf` | rasterizado, **torto**, com carimbo — só sai com OCR de verdade |

Para regerá-los: `uv run python exemplos/gerar_exemplos.py`

## O que observar na aula

1. **A tabela.** O OCR tradicional devolve células soltas; o de LLM devolve markdown.
2. **O documento escaneado.** A camada nativa não tem nada. O OCR resolve.
3. **A latência.** O tradicional responde em ~1s; o de LLM é um *job assíncrono* — dá
   para ver o polling acontecendo na tela.
4. **O custo.** `prebuilt-read` custa **$1,50** por 1.000 páginas; o Chandra, ~$4,00.
   O `prebuilt-layout` (fora da demo de propósito) custaria **$10,00** — é o preço de
   pedir *estrutura* ao OCR tradicional, que é justamente o que o de LLM já dá.
5. **As caixas coloridas por confiança.** Onde o OCR tradicional tem menos certeza.
6. **O hover, dos dois lados.** Palavra + confiança de um lado; bloco tipado do outro.

## Estrutura

```
app.py                  UI Streamlit (nenhuma chamada de API direta)
modelos.py              ResultadoOCR / PaginaOCR / Caixa — contrato comum
render.py               página -> imagem (pymupdf)
viewer.py               visualizador interativo: caixas em SVG + caixinha de hover
cache.py                cache das chamadas + fallback para as gravações
providers/azure_di.py   Azure Document Intelligence (só `prebuilt-read`)
providers/datalab.py    Datalab / Chandra (submit + poll, na mão de propósito;
                        `output_format=markdown,json` numa chamada só — o json é
                        que traz os blocos de layout com bbox)
providers/nativo.py     camada de texto nativa — o fallback sem chave
exemplos/               PDFs de exemplo e respostas gravadas (.json)
```

### O detalhe técnico que mais confunde

O Azure DI devolve os polígonos em **polegadas** quando a entrada é PDF e em **pixels**
quando é imagem — e a Datalab, em pixels do render dela (1596×2240 numa A4). Em vez de
tratar cada caso, `viewer.py` usa a **própria página** como sistema de coordenadas: o
SVG sobreposto tem `viewBox="0 0 {largura} {altura}"` nas unidades que o provider
informou, e os polígonos entram sem conversão nenhuma.

```html
<svg viewBox="0 0 8.26 11.69" preserveAspectRatio="none"> <!-- polegadas, no Azure -->
```

Isso é agnóstico de unidade, de DPI e do tamanho em que a página é exibida.

**Limitação conhecida:** páginas rotacionadas (`page.angle`). O OCR corrige a inclinação
internamente, mas o overlay é desenhado sobre a página original — então as caixas saem
tortas em relação ao texto. É um bom gancho para explicar o *deskew*.
