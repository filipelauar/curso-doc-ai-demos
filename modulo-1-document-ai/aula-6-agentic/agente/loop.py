"""O loop de tool use — codado na mão, sem framework.

Usa a **Responses API** da OpenAI com o modelo `gpt-5.6-luna`.

É um *generator* de `Evento`: é isso que permite a UI mostrar o trace ao
vivo, passo a passo, em vez de só o resultado final.

O loop em si:

    modelo -> quer usar ferramenta? -> executa -> devolve o resultado
           -> modelo de novo ... até ele parar de pedir ferramenta

**Prompt caching (aula 4):** na OpenAI o cache é *implícito* — não existe
`cache_control` para marcar. Basta manter o prefixo estável (as
`instructions` e as `tools` vão primeiro e nunca mudam) que o provider
reaproveita sozinho, sem custo de escrita. Passamos também um
`prompt_cache_key` estável, que ajuda a rotear as chamadas para o mesmo
cache. A UI mostra `usage.input_tokens_details.cached_tokens` a cada
turno — é o slide da imagem `prompt_cache.png` acontecendo ao vivo, no
modo implícito.
"""

from __future__ import annotations

import json
import os
import time
from typing import Iterator

from agente.eventos import Evento
from agente.ferramentas import TOOLS, executar
from agente.indice import Indice
from agente.prompts import SYSTEM

MAX_TURNOS = 12
MAX_CHAMADAS = 25
MAX_TOKENS_SAIDA = 4096

# ATENÇÃO: o alias curto `gpt-5.6` roteia para o `gpt-5.6-sol`, NÃO para o
# Luna. Sempre use o id completo.
MODELO_PADRAO = "gpt-5.6-luna"
ESFORCO_PADRAO = "low"  # none | low | medium | high | xhigh | max

# Chave de cache estável: mantém as chamadas da demo no mesmo prefixo
# cacheado. Só muda se o system prompt ou as tools mudarem.
CHAVE_CACHE = "curso-doc-ai/aula-6/agente-v1"

# US$ por 1M de tokens (set/2026): (entrada, entrada em cache, saída).
# Só para a métrica de custo da UI.
# Nota: acima de 272K tokens de entrada a OpenAI cobra 2x a entrada e 1,5x a
# saída — não modelamos isso aqui porque a demo fica muito abaixo disso.
PRECOS = {
    "gpt-5.6-luna": (0.20, 0.02, 1.20),
}


def custo_estimado(modelo: str, uso: dict) -> float:
    entrada, cacheada, saida = PRECOS.get(modelo, PRECOS[MODELO_PADRAO])
    cache = uso.get("cached_tokens", 0)
    nao_cacheados = max(0, uso.get("input_tokens", 0) - cache)
    return (
        nao_cacheados * entrada
        + cache * cacheada
        + uso.get("output_tokens", 0) * saida
    ) / 1_000_000


def _achatar_uso(usage) -> dict[str, int]:
    """Normaliza o objeto de uso da Responses API para um dict simples."""
    if usage is None:
        return {}
    entrada = getattr(usage, "input_tokens_details", None)
    saida = getattr(usage, "output_tokens_details", None)
    return {
        "input_tokens": getattr(usage, "input_tokens", 0) or 0,
        "output_tokens": getattr(usage, "output_tokens", 0) or 0,
        "total_tokens": getattr(usage, "total_tokens", 0) or 0,
        "cached_tokens": getattr(entrada, "cached_tokens", 0) or 0,
        "reasoning_tokens": getattr(saida, "reasoning_tokens", 0) or 0,
    }


def rodar(pergunta: str, indice: Indice, historico: list | None = None,
          modelo: str | None = None, esforco: str | None = None) -> Iterator[Evento]:
    """Roda o agente, emitindo um Evento por passo.

    `historico` é a lista de itens de entrada da Responses API (mensagens,
    chamadas de ferramenta, resultados e itens de raciocínio) dos turnos
    anteriores. É mutada no lugar, para a UI continuar a conversa.
    """
    try:
        from openai import OpenAI
    except ImportError:
        yield Evento(tipo="erro", texto="Pacote openai ausente. Rode: uv sync --group agente")
        return

    if not os.getenv("OPENAI_API_KEY"):
        yield Evento(tipo="erro", texto="OPENAI_API_KEY não configurada no .env da raiz.")
        return

    modelo = modelo or os.getenv("OPENAI_MODEL", MODELO_PADRAO)
    esforco = esforco or os.getenv("OPENAI_REASONING_EFFORT", ESFORCO_PADRAO)
    cliente = OpenAI()

    entrada = historico if historico is not None else []
    entrada.append({"role": "user", "content": pergunta})

    chamadas = 0

    for turno in range(1, MAX_TURNOS + 1):
        try:
            with cliente.responses.stream(
                model=modelo,
                # `instructions` + `tools` formam o prefixo fixo. Manter isso
                # estável é o que faz o cache implícito funcionar.
                instructions=SYSTEM,
                tools=TOOLS,
                input=entrada,
                max_output_tokens=MAX_TOKENS_SAIDA,
                # Raciocínio custa tokens de saída. Numa aula ao vivo, "low"
                # é o melhor equilíbrio entre qualidade e tempo morto.
                reasoning={"effort": esforco},
                prompt_cache_key=CHAVE_CACHE,
            ) as stream:
                for evento in stream:
                    if evento.type == "response.output_text.delta":
                        yield Evento(tipo="texto", texto=evento.delta, turno=turno)
                resposta = stream.get_final_response()
        except Exception as exc:  # noqa: BLE001 — a UI mostra, a aula continua
            yield Evento(tipo="erro", texto=f"{type(exc).__name__}: {exc}", turno=turno)
            return

        yield Evento(tipo="uso", uso=_achatar_uso(resposta.usage), turno=turno)

        # Devolvemos TODOS os itens de saída ao histórico — inclusive os itens
        # de raciocínio. Omiti-los faz o modelo perder o fio entre os turnos.
        entrada += [item.model_dump(exclude_none=True) for item in resposta.output]

        pedidos = [item for item in resposta.output if item.type == "function_call"]
        if not pedidos:
            yield Evento(tipo="fim", turno=turno)
            return

        # ── executa todas as ferramentas pedidas neste turno ──────
        for pedido in pedidos:
            chamadas += 1
            try:
                argumentos = json.loads(pedido.arguments or "{}")
            except json.JSONDecodeError:
                argumentos = {}

            yield Evento(tipo="ferramenta", nome=pedido.name, argumentos=argumentos,
                         id_chamada=pedido.call_id, turno=turno)

            t = time.perf_counter()
            try:
                saida = executar(indice, pedido.name, argumentos)
                erro = False
            except Exception as exc:  # noqa: BLE001
                # Devolvemos o erro COMO resultado da ferramenta em vez de
                # estourar: o agente se recupera sozinho, e ver isso é ótimo
                # na aula.
                saida = f"A ferramenta falhou: {type(exc).__name__}: {exc}"
                erro = True

            segundos = time.perf_counter() - t
            entrada.append({
                "type": "function_call_output",
                "call_id": pedido.call_id,
                "output": saida,
            })
            yield Evento(tipo="resultado", nome=pedido.name, texto=saida,
                         id_chamada=pedido.call_id, erro=erro, segundos=segundos,
                         turno=turno)

            if chamadas >= MAX_CHAMADAS:
                yield Evento(
                    tipo="erro", turno=turno,
                    texto=f"Limite de {MAX_CHAMADAS} chamadas de ferramenta atingido. "
                          f"Reformule a pergunta de forma mais específica.",
                )
                return

    yield Evento(tipo="erro", texto=f"Limite de {MAX_TURNOS} turnos atingido.", turno=MAX_TURNOS)


# ─────────────────────────────────────────────────────────────────
# Modo replay — o seguro da demo
# ─────────────────────────────────────────────────────────────────
def gravar_trace(caminho, pergunta: str, eventos: list[Evento]) -> None:
    from dataclasses import asdict

    caminho.parent.mkdir(parents=True, exist_ok=True)
    caminho.write_text(json.dumps(
        {"pergunta": pergunta, "eventos": [asdict(e) for e in eventos]},
        ensure_ascii=False, indent=2,
    ), encoding="utf-8")


def reproduzir(caminho, velocidade: float = 1.0) -> Iterator[Evento]:
    """Reproduz um trace gravado. Sem chave, sem rede, sem surpresa."""
    dados = json.loads(caminho.read_text(encoding="utf-8"))
    for d in dados["eventos"]:
        if velocidade:
            time.sleep(0.01 / velocidade if d["tipo"] == "texto" else 0.25 / velocidade)
        yield Evento(**d)
