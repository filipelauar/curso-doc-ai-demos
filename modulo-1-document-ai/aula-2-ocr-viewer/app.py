"""Demo da aula 2 — OCR tradicional vs OCR de LLM, lado a lado.

    uv sync --group ocr
    uv run streamlit run modulo-1-document-ai/aula-2-ocr-viewer/app.py

Sem chave no .env, a demo cai automaticamente para as respostas
gravadas em `exemplos/` — dá para dar a aula inteira offline.
"""

from __future__ import annotations

import sys
from pathlib import Path

import streamlit as st
from dotenv import find_dotenv, load_dotenv

AQUI = Path(__file__).parent
sys.path.insert(0, str(AQUI))

load_dotenv(find_dotenv(), override=False)

import cache  # noqa: E402
import render  # noqa: E402
import viewer  # noqa: E402
from modelos import ResultadoOCR  # noqa: E402
from providers import disponiveis  # noqa: E402

st.set_page_config(page_title="OCR: tradicional vs LLM", layout="wide")

CIANO, ROXO = "#0891B2", "#7C3AED"


# ─────────────────────────────────────────────────────────────────
# Sidebar
# ─────────────────────────────────────────────────────────────────
def sidebar() -> dict:
    st.sidebar.title("Comparador de OCR")
    st.sidebar.caption("Curso Document AI · Aula 2")

    chaves = disponiveis()
    for nome, rotulo in [("azure", "Azure Document Intelligence"), ("datalab", "Datalab / Chandra")]:
        icone = "🟢" if chaves[nome] else "⚪"
        st.sidebar.write(f"{icone} {rotulo}")
    com_api = chaves["azure"] or chaves["datalab"]
    if not com_api:
        st.sidebar.info(
            "Nenhuma chave de API no `.env`. A coluna da esquerda mostra a camada "
            "de texto nativa do PDF; a da direita precisa de `DATALAB_API_KEY`."
        )

    st.sidebar.divider()

    ENVIAR = "(enviar um arquivo)"
    exemplos = sorted(AQUI.glob("exemplos/*.pdf")) + sorted(AQUI.glob("exemplos/*.png"))
    # Os exemplos vêm primeiro: a demo abre já com conteúdo na tela.
    opcoes = [e.name for e in exemplos] + [ENVIAR]
    escolha = st.sidebar.selectbox("Documento", opcoes)

    dados, nome = None, None
    if escolha == ENVIAR:
        arquivo = st.sidebar.file_uploader("PDF ou imagem", type=["pdf", "png", "jpg", "jpeg"])
        if arquivo:
            dados, nome = arquivo.getvalue(), arquivo.name
    else:
        caminho = AQUI / "exemplos" / escolha
        dados, nome = caminho.read_bytes(), escolha

    st.sidebar.divider()
    st.sidebar.caption(
        "OCR tradicional: **Azure `prebuilt-read`** — $1,50 por 1.000 páginas. "
        "É o OCR puro: palavra, posição e confiança, sem estrutura."
    )
    modo = st.sidebar.selectbox("Modo Datalab", ["balanced", "fast", "accurate"])
    max_paginas = st.sidebar.number_input(
        "Máx. de páginas (trava de custo)", 1, 50, int(__import__("os").getenv("DATALAB_MAX_PAGES", 5))
    )

    st.sidebar.divider()
    offline = st.sidebar.toggle(
        "Modo offline (respostas gravadas)",
        value=False,
        help="Força os dois lados a usarem os JSONs de exemplos/, sem chamar API.",
    )
    tipos = []
    if st.sidebar.checkbox("Caixas de palavra", value=True):
        tipos.append("palavra")
    if st.sidebar.checkbox("Caixas de linha"):
        tipos.append("linha")
    por_confianca = st.sidebar.checkbox(
        "Colorir por confiança", help="Laranja abaixo de 0,95 · vermelho abaixo de 0,80"
    )
    dpi = st.sidebar.select_slider("DPI do render", [100, 150, 200], value=150)
    largura = st.sidebar.select_slider(
        "Largura do visualizador (px)",
        [420, 520, 620, 720, 860],
        value=620,
        help="Ajuste para o projetor da sala — a caixinha de hover segue o mouse.",
    )

    return dict(
        dados=dados, nome=nome, modo=modo, max_paginas=int(max_paginas),
        offline=offline, tipos=tuple(tipos), por_confianca=por_confianca, dpi=dpi,
        largura=int(largura), chaves=chaves,
    )


# ─────────────────────────────────────────────────────────────────
# Execução dos providers
# ─────────────────────────────────────────────────────────────────
def rodar_azure(pdf: bytes, h: str, cfg: dict) -> ResultadoOCR:
    """Coluna da esquerda: Azure DI, ou o melhor substituto disponível.

    Ordem: resposta gravada -> API da Azure -> camada nativa do pymupdf.
    O último caso não é OCR, e a UI diz isso claramente.
    """
    if cfg["offline"] or not cfg["chaves"]["azure"]:
        gravado = cache.carregar_gravado(h, "azure")
        if gravado:
            return gravado
        return cache.nativo_cached(pdf, h)
    with st.spinner("Azure Document Intelligence (prebuilt-read)..."):
        return cache.azure_cached(pdf, h)


def rodar_datalab(pdf: bytes, h: str, cfg: dict) -> ResultadoOCR:
    if cfg["offline"] or not cfg["chaves"]["datalab"]:
        gravado = cache.carregar_gravado(h, "datalab")
        if gravado:
            return gravado
        motivo = "Modo offline" if cfg["offline"] else "DATALAB_API_KEY ausente"
        return ResultadoOCR(
            provider="datalab", rotulo="Chandra · Datalab",
            erro=f"{motivo} e não há resposta gravada para este documento.",
        )
    with st.status("Chandra (Datalab) — job assíncrono", expanded=True) as status:
        from providers import datalab as prov

        res = prov.analisar(
            pdf, modo=cfg["modo"], max_paginas=cfg["max_paginas"], progresso=st.write
        )
        status.update(
            label=f"Chandra · {res.segundos:.1f}s", state="error" if res.erro else "complete",
            expanded=False,
        )
    return res


# ─────────────────────────────────────────────────────────────────
# Render das colunas
# ─────────────────────────────────────────────────────────────────
def metricas(res: ResultadoOCR, n_paginas: int) -> None:
    c1, c2, c3 = st.columns(3)
    c1.metric("Tempo", "—" if res.gravado else f"{res.segundos:.1f}s")
    c2.metric("Páginas", len(res.paginas) or n_paginas)
    if res.custo_usd is None:
        c3.metric("Custo", "—")
    else:
        c3.metric(
            "Custo" + (" (est.)" if res.custo_estimado else ""),
            f"US$ {res.custo_usd:.4f}",
        )


def coluna_azure(res: ResultadoOCR, pdf: bytes, pagina: int, cfg: dict) -> None:
    st.subheader("OCR tradicional")
    st.caption(res.rotulo + (" · resposta gravada" if res.gravado else ""))

    if res.provider == "nativo":
        st.info(
            "Sem `AZURE_DI_KEY` no `.env`. Mostrando a **camada de texto nativa** "
            "do PDF — que, numa página nativa digital, é melhor e mais barata que "
            "qualquer OCR. Numa página escaneada, ela não existe."
        )

    if res.erro:
        st.warning(res.erro)
        return

    p = res.pagina(pagina)

    # As três abas espelham as do Chandra: primeiro o que o motor viu na
    # página, depois as duas formas de texto que ele produz.
    aba_caixas, aba_texto, aba_md = st.tabs(
        ["Caixas", "Texto por linha", "Markdown remontado"]
    )
    with aba_caixas:
        imagem = render.pagina_para_imagem(pdf, pagina, dpi=cfg["dpi"])
        if p:
            st.caption(
                "🖱️ Passe o mouse sobre uma caixa: o texto lido, a **confiança** e a "
                "**bbox**. Aqui a unidade é a **palavra** — nenhuma estrutura vem junto."
            )
            viewer.visualizar(
                imagem, p, cfg["tipos"], cfg["por_confianca"], largura=cfg["largura"]
            )
            n_palavras = sum(1 for c in p.caixas if c.tipo == "palavra")
            confs = [c.confianca for c in p.caixas if c.confianca is not None]
            st.caption(
                f"{n_palavras} palavras nesta página"
                + (f" · confiança média {sum(confs)/len(confs):.3f}" if confs else "")
            )
        else:
            st.image(imagem, use_container_width=True)
    with aba_texto:
        st.caption("A saída crua do OCR tradicional: linha por linha, sem estrutura.")
        st.text((p.texto if p else "") or "(vazio)")
    with aba_md:
        st.caption(
            "Remontado **por nós** a partir das caixas — compare com o markdown que "
            "o VLM já devolve pronto ao lado."
        )
        st.code(res.markdown or "(vazio)", language="markdown")

    metricas(res, render.n_paginas(pdf))


def coluna_datalab(res: ResultadoOCR, pdf: bytes, pagina: int, cfg: dict) -> None:
    st.subheader("OCR com LLM")
    st.caption(res.rotulo + (" · resposta gravada" if res.gravado else ""))

    if res.erro:
        st.warning(res.erro)
        return

    p = res.pagina(pagina)
    md = (p.markdown if p else "") or res.markdown
    if p is None and res.markdown:
        st.caption("Sem separação por página — mostrando o documento inteiro.")

    aba_layout, aba_render, aba_bruto = st.tabs(["Layout", "Renderizado", "Markdown bruto"])
    with aba_layout:
        if p and p.caixas:
            st.caption(
                "🖱️ Passe o mouse sobre um bloco: o tipo que o modelo atribuiu e o "
                "texto que ele leu ali. Aqui a unidade é o **bloco**, não a palavra — "
                "é por isso que o markdown já sai montado."
            )
            imagem = render.pagina_para_imagem(pdf, pagina, dpi=cfg["dpi"])
            viewer.visualizar(imagem, p, tipos=("bloco",), largura=cfg["largura"])
            st.caption(_resumo_blocos(p))
        else:
            st.info(
                "Sem blocos de layout para esta página. O layout vem do "
                "`output_format=json` da Datalab — respostas gravadas antes dessa "
                "mudança só têm o markdown."
            )
    with aba_render:
        st.markdown(md or "_(vazio)_")
    with aba_bruto:
        st.code(md or "", language="markdown")

    if res.extra.get("parse_quality_score") is not None:
        st.caption(f"parse_quality_score: {res.extra['parse_quality_score']}")

    metricas(res, render.n_paginas(pdf))


def _resumo_blocos(p) -> str:
    """Contagem por tipo de bloco — a legenda do que está na tela."""
    from collections import Counter

    contagem = Counter(c.rotulo or c.tipo for c in p.caixas)
    return f"{len(p.caixas)} blocos: " + " · ".join(
        f"{rotulo} ({n})" for rotulo, n in contagem.most_common()
    )


# ─────────────────────────────────────────────────────────────────
def main() -> None:
    cfg = sidebar()

    st.title("OCR tradicional vs OCR de LLM")
    st.caption(
        "À esquerda, caixas de palavra e transcrição. À direita, markdown com o layout "
        "já montado — e a aba **Layout** com os blocos que o modelo enxergou. "
        "Passe o mouse sobre as caixas dos dois lados."
    )

    if not cfg["dados"]:
        st.info("Escolha um documento de exemplo na barra lateral, ou envie o seu.")
        return

    pdf = cfg["dados"]
    if not pdf.startswith(b"%PDF"):
        pdf = render.imagem_para_pdf(pdf)

    total = render.n_paginas(pdf)
    pagina = st.number_input("Página", 1, total, 1) if total > 1 else 1

    res_azure = rodar_azure(pdf, cache.sha(pdf), cfg)
    res_datalab = rodar_datalab(pdf, cache.sha(pdf), cfg)

    esq, dir_ = st.columns(2, gap="large")
    with esq:
        coluna_azure(res_azure, pdf, int(pagina), cfg)
    with dir_:
        coluna_datalab(res_datalab, pdf, int(pagina), cfg)

    # Gravar as respostas para poder dar a aula offline depois.
    if not cfg["offline"] and st.button("Gravar estas respostas em exemplos/"):
        h = cache.sha(pdf)
        salvos = [str(cache.gravar(h, r)) for r in (res_azure, res_datalab) if r.ok]
        st.success("Gravado: " + ", ".join(salvos) if salvos else "Nada para gravar.")


if __name__ == "__main__":
    main()
