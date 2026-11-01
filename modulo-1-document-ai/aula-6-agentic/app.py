"""Demo da aula 6 — um agente respondendo sobre um acervo de documentos.

    uv sync --group agente
    uv run python -m ingest.baixar_corpus --fonte camara --quantidade 300
    uv run python -m ingest.ingerir
    uv run streamlit run modulo-1-document-ai/aula-6-agentic/app.py

A tela mostra **cada passo** do agente: qual ferramenta escolheu, com quais
argumentos, o que voltou — e os tokens lidos do cache a cada turno.
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

import streamlit as st
from dotenv import find_dotenv, load_dotenv

AQUI = Path(__file__).parent
sys.path.insert(0, str(AQUI))
load_dotenv(find_dotenv(), override=False)

from agente import loop as agente_loop  # noqa: E402
from agente.indice import Indice  # noqa: E402

st.set_page_config(page_title="Agente sobre o acervo", layout="wide")

TRACES = AQUI / "traces"
PERGUNTAS = [
    "Quais documentos do acervo tratam de proteção de dados pessoais, e o que cada um exige?",
    "Qual é o maior valor em reais citado no acervo, e em que contexto ele aparece?",
    "Há divergência entre os documentos sobre prazos de entrada em vigor?",
    "Resuma em 5 tópicos o que o documento mais longo do acervo propõe, citando a página de cada tópico.",
    "O acervo fala sobre 'trabalho remoto'? Se não usa esse termo, qual termo usa?",
]

ICONES = {
    "buscar_semantica": "🧭",
    "buscar_texto": "🔎",
    "ler_documento": "📖",
    "listar_documentos": "🗂️",
}


@st.cache_resource(show_spinner="Carregando o índice e o modelo de embeddings...")
def carregar_indice() -> Indice:
    ix = Indice()
    if ix.pronto:
        # Pré-aquece o encoder: a primeira chamada carrega ~280 MB de pesos e
        # levaria ~8s no meio do trace, parecendo que o agente travou.
        ix.buscar_semantica("aquecimento", k=1)
    return ix


# ─────────────────────────────────────────────────────────────────
def sem_indice() -> None:
    st.title("Agente sobre o acervo")
    st.error("O índice ainda não existe.")
    st.markdown(
        "A indexação é **offline** e é onde mora a qualidade — o agente é só a parte "
        "visível. Rode, nesta ordem:"
    )
    st.code(
        "uv sync --group agente\n"
        "cd modulo-1-document-ai/aula-6-agentic\n\n"
        "# 1. baixar o acervo (~300 PDFs públicos)\n"
        "uv run python -m ingest.baixar_corpus --fonte camara --quantidade 300\n\n"
        "# 2. converter e indexar (demora — é o passo pesado)\n"
        "uv run python -m ingest.ingerir",
        language="bash",
    )
    if (traces := sorted(TRACES.glob("*.json"))):
        st.info(f"Há {len(traces)} trace(s) gravado(s). Dá para rodar a demo em modo replay.")


def barra_lateral(ix: Indice) -> dict:
    st.sidebar.title("Agente sobre o acervo")
    st.sidebar.caption("Curso Document AI · Aula 6")

    paginas = sum(d.get("paginas", 0) for d in ix.documentos.values())
    c1, c2 = st.sidebar.columns(2)
    c1.metric("Documentos", len(ix.documentos))
    c2.metric("Páginas", paginas)
    c1.metric("Chunks", len(ix.chunks))
    c2.metric("Dim.", ix.embeddings.shape[1] if ix.embeddings is not None else 0)

    if (falhas := AQUI / "indice" / "falhas.json").exists():
        n = len(json.loads(falhas.read_text(encoding="utf-8")))
        st.sidebar.warning(f"{n} documento(s) falharam na ingestão — **não estão no índice**.")

    st.sidebar.divider()
    modelo = st.sidebar.selectbox(
        "Modelo",
        ["gpt-5.6-luna"],
        help="Luna é o modelo econômico da OpenAI, feito para alto volume.",
    )
    esforco = st.sidebar.select_slider(
        "Esforço de raciocínio",
        ["none", "low", "medium", "high"],
        value="low",
        help="Mais esforço = melhor raciocínio, mais tokens de saída e mais tempo morto na aula.",
    )
    traces = sorted(TRACES.glob("*.json"))
    replay = st.sidebar.toggle(
        "Modo replay (trace gravado)", value=False,
        disabled=not traces,
        help="Reproduz uma execução gravada. Sem chave, sem rede — o plano B da aula.",
    ) if traces else False
    gravar = st.sidebar.toggle("Gravar o trace desta pergunta", value=False) if not replay else False

    st.sidebar.divider()
    st.sidebar.caption("Uso acumulado na sessão")
    total = st.session_state.get("uso_total", {})
    st.sidebar.metric("Tokens de entrada", f"{total.get('input_tokens', 0):,}".replace(",", "."))
    st.sidebar.metric(
        "Lidos do cache 💰",
        f"{total.get('cached_tokens', 0):,}".replace(",", "."),
        help="Custam 0,1x. Na OpenAI o cache é implícito — nada a configurar.",
    )
    st.sidebar.metric("Tokens de saída", f"{total.get('output_tokens', 0):,}".replace(",", "."))
    st.sidebar.metric("Custo estimado", f"US$ {st.session_state.get('custo', 0):.4f}")

    if st.sidebar.button("Limpar conversa"):
        for chave in ("mensagens", "historico", "uso_total", "custo"):
            st.session_state.pop(chave, None)
        st.rerun()

    return {"modelo": modelo, "esforco": esforco, "replay": replay,
            "gravar": gravar, "traces": traces}


def renderizar_passos(eventos: list, ix: Indice) -> None:
    """Redesenha o trace de uma resposta já concluída."""
    for ev in eventos:
        if ev["tipo"] != "resultado":
            continue
        icone = ICONES.get(ev["nome"], "🔧")
        rotulo = f"{icone} {ev['nome']} · {ev['segundos']:.2f}s"
        with st.expander(rotulo, expanded=False):
            st.code(json.dumps(ev.get("argumentos", {}), ensure_ascii=False, indent=2), language="json")
            st.text(ev["texto"][:4000])


def executar(pergunta: str, ix: Indice, cfg: dict) -> None:
    st.session_state.setdefault("historico", [])
    st.session_state.setdefault("uso_total", {})
    st.session_state.setdefault("custo", 0.0)

    if cfg["replay"]:
        fonte = agente_loop.reproduzir(cfg["traces"][0])
    else:
        fonte = agente_loop.rodar(
            pergunta, ix, historico=st.session_state["historico"],
            modelo=cfg["modelo"], esforco=cfg["esforco"],
        )

    coletados, partes_texto = [], []
    caixa_texto = st.empty()
    status_atual = None
    docs_citados: set[str] = set()

    for ev in fonte:
        coletados.append(ev)

        if ev.tipo == "texto":
            partes_texto.append(ev.texto)
            caixa_texto.markdown("".join(partes_texto))

        elif ev.tipo == "ferramenta":
            icone = ICONES.get(ev.nome, "🔧")
            resumo = ev.argumentos.get("consulta") or ev.argumentos.get("padrao") \
                or ev.argumentos.get("doc_id") or ev.argumentos.get("filtro_titulo") or ""
            status_atual = st.status(f"{icone} {ev.nome}  ·  {str(resumo)[:70]}", expanded=True)
            with status_atual:
                st.code(json.dumps(ev.argumentos, ensure_ascii=False, indent=2), language="json")

        elif ev.tipo == "resultado":
            if status_atual is not None:
                with status_atual:
                    st.text(ev.texto[:4000])
                n = ev.texto.count("[")
                vazio = "Nenhum" in ev.texto[:40] or "Nenhuma" in ev.texto[:40]
                etiqueta = (
                    f"{ICONES.get(ev.nome, '🔧')} {ev.nome} — "
                    + ("nada encontrado" if vazio else f"{n} trecho(s)")
                    + f" · {ev.segundos:.2f}s"
                )
                status_atual.update(
                    label=etiqueta,
                    state="error" if ev.erro else ("complete" if not vazio else "complete"),
                    expanded=False,
                )
                status_atual = None
            for doc in ix.documentos:
                if doc in ev.texto:
                    docs_citados.add(doc)
            # A resposta continua depois do resultado: nova caixa de texto.
            partes_texto = []
            caixa_texto = st.empty()

        elif ev.tipo == "uso":
            for chave, valor in ev.uso.items():
                if isinstance(valor, int):
                    st.session_state["uso_total"][chave] = \
                        st.session_state["uso_total"].get(chave, 0) + valor
            st.session_state["custo"] += agente_loop.custo_estimado(cfg["modelo"], ev.uso)
            lidos = ev.uso.get("cached_tokens", 0)
            if lidos:
                st.caption(f"turno {ev.turno} · {lidos:,} tokens lidos do cache (0,1x)".replace(",", "."))

        elif ev.tipo == "erro":
            st.error(ev.texto)

    if docs_citados:
        with st.expander(f"📎 Documentos consultados ({len(docs_citados)})"):
            for doc in sorted(docs_citados):
                d = ix.documentos[doc]
                st.markdown(f"**{doc}** · {d['paginas']} pág · {d['titulo']}")
                st.caption(d.get("resumo", ""))
                if d.get("url"):
                    st.caption(d["url"])

    if cfg["gravar"] and coletados:
        caminho = TRACES / (pergunta[:50].strip().replace(" ", "-").replace("/", "-") + ".json")
        agente_loop.gravar_trace(caminho, pergunta, coletados)
        st.success(f"Trace gravado em {caminho.name}")

    from dataclasses import asdict
    st.session_state["mensagens"][-1]["eventos"] = [asdict(e) for e in coletados]
    st.session_state["mensagens"][-1]["resposta"] = "".join(
        e.texto for e in coletados if e.tipo == "texto"
    )


# ─────────────────────────────────────────────────────────────────
def main() -> None:
    ix = carregar_indice()
    if not ix.pronto:
        sem_indice()
        return

    cfg = barra_lateral(ix)
    st.title("Agente sobre o acervo")
    st.caption(
        f"{len(ix.documentos)} documentos · {len(ix.chunks)} chunks indexados. "
        "O agente decide sozinho quando usar busca semântica e quando usar grep."
    )

    st.session_state.setdefault("mensagens", [])

    if not st.session_state["mensagens"]:
        st.markdown("**Perguntas de exemplo** — cada uma exercita um caminho diferente:")
        for i, p in enumerate(PERGUNTAS):
            if st.button(p, key=f"ex{i}", use_container_width=True):
                st.session_state["pendente"] = p
                st.rerun()

    for msg in st.session_state["mensagens"]:
        with st.chat_message(msg["papel"]):
            if msg["papel"] == "user":
                st.markdown(msg["texto"])
            else:
                renderizar_passos(msg.get("eventos", []), ix)
                st.markdown(msg.get("resposta", ""))

    pergunta = st.chat_input("Pergunte algo sobre o acervo...") or st.session_state.pop("pendente", None)
    if not pergunta:
        return

    st.session_state["mensagens"].append({"papel": "user", "texto": pergunta})
    with st.chat_message("user"):
        st.markdown(pergunta)

    st.session_state["mensagens"].append({"papel": "assistant", "eventos": [], "resposta": ""})
    with st.chat_message("assistant"):
        executar(pergunta, ix, cfg)


if __name__ == "__main__":
    main()
