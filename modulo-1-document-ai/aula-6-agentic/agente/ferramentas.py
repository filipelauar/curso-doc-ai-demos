"""As ferramentas do agente e os seus schemas.

Quatro tools. As descrições **são o conteúdo do slide** "as duas famílias
de busca" — é lendo-as que o modelo decide quando usar semântica e quando
usar grep. Escrever isso mal é a forma mais fácil de estragar a demo.

Duas regras valem para todas:

1. O resultado volta como **texto já formatado**, com `[doc_id p.N]` antes
   de cada trecho. A citação sai correta no fim sem ninguém pedir.
2. Tudo é **truncado**. Resultado de busca sem limite estoura o contexto e
   derruba a qualidade do turno seguinte.
"""

from __future__ import annotations

from agente.indice import Indice

MAX_CHARS_TRECHO = 1500
MAX_CHARS_RESULTADO = 8000


# Formato da Responses API da OpenAI: PLANO — `type`, `name`, `description` e
# `parameters` no mesmo nível (não aninhado dentro de um objeto `function`,
# como era na antiga Chat Completions).
TOOLS = [
    {
        "type": "function",
        "name": "buscar_semantica",
        "description": (
            "Busca trechos por SIGNIFICADO em todo o acervo. Use quando a pergunta é "
            "conceitual, ou quando você não sabe as palavras exatas que os documentos "
            "usam — ela acha sinônimo e paráfrase (procurar por 'prazo de vigência' "
            "encontra 'período de duração'). É a sua primeira parada para perguntas "
            "abertas. Ruim para termo exato: para número, valor, CNPJ, código ou "
            "nome próprio, prefira buscar_texto."
        ),
        "parameters": {
            "type": "object",
            "properties": {
                "consulta": {
                    "type": "string",
                    "description": "O que procurar, em português, como uma frase.",
                },
                "k": {
                    "type": "integer",
                    "description": "Quantos trechos retornar (1 a 15). Padrão 6.",
                },
                "doc_id": {
                    "type": "string",
                    "description": "Opcional: restringe a busca a um documento.",
                },
            },
            "required": ["consulta"],
        },
    },
    {
        "type": "function",
        "name": "buscar_texto",
        "description": (
            "Busca literal por expressão regular em todos os documentos, como um grep. "
            "Use para termo EXATO: valores (R$), datas, CNPJ, números de lei, artigos, "
            "códigos, nomes próprios. É cirúrgica onde a busca semântica é vaga. "
            "Se não achar nada, isso é uma informação honesta e útil — os documentos "
            "podem usar outro termo; nesse caso tente buscar_semantica para descobrir "
            "qual, e depois volte aqui com o termo certo."
        ),
        "parameters": {
            "type": "object",
            "properties": {
                "padrao": {
                    "type": "string",
                    "description": "Expressão regular no dialeto do Python. Ex.: 'R\\$\\s?[\\d.,]+'",
                },
                "ignorar_caixa": {"type": "boolean", "description": "Padrão: true."},
                "max_resultados": {"type": "integer", "description": "Padrão 20."},
                "doc_id": {
                    "type": "string",
                    "description": "Opcional: restringe a busca a um documento.",
                },
            },
            "required": ["padrao"],
        },
    },
    {
        "type": "function",
        "name": "ler_documento",
        "description": (
            "Abre um documento e lê uma faixa de páginas. Use DEPOIS de uma busca, "
            "para ver o contexto em volta de um trecho que você encontrou — a busca "
            "devolve fragmentos, e confirmar uma informação quase sempre exige ler o "
            "que vem antes e depois. Máximo de 10 páginas por chamada."
        ),
        "parameters": {
            "type": "object",
            "properties": {
                "doc_id": {"type": "string"},
                "pagina_ini": {"type": "integer", "description": "Padrão 1."},
                "pagina_fim": {"type": "integer", "description": "No máximo pagina_ini + 9."},
            },
            "required": ["doc_id"],
        },
    },
    {
        "type": "function",
        "name": "listar_documentos",
        "description": (
            "Lista os documentos do acervo com doc_id, título, resumo e número de "
            "páginas. Use para se orientar no começo, ou quando a pergunta for do tipo "
            "'quantos documentos' / 'quais documentos falam sobre'."
        ),
        "parameters": {
            "type": "object",
            "properties": {
                "filtro_titulo": {
                    "type": "string",
                    "description": "Opcional: só documentos cujo título ou resumo contenha isto.",
                }
            },
            "required": [],
        },
    },
]


def _cortar(texto: str, limite: int = MAX_CHARS_TRECHO) -> str:
    texto = (texto or "").strip()
    return texto if len(texto) <= limite else texto[:limite] + " […]"


def _juntar(partes: list[str], vazio: str) -> str:
    if not partes:
        return vazio
    saida = "\n\n".join(partes)
    if len(saida) > MAX_CHARS_RESULTADO:
        saida = saida[:MAX_CHARS_RESULTADO] + "\n\n[…resultado truncado…]"
    return saida


# ─────────────────────────────────────────────────────────────────
def buscar_semantica(ix: Indice, consulta: str, k: int = 6, doc_id: str | None = None) -> str:
    trechos = ix.buscar_semantica(consulta, k=k, doc_id=doc_id)
    partes = [
        f"{t.citacao} (relevância {t.score:.2f}) — {t.titulo}\n{_cortar(t.texto)}"
        for t in trechos
    ]
    return _juntar(
        partes,
        f"Nenhum trecho relevante para {consulta!r}. "
        f"Tente outras palavras, ou use buscar_texto se souber o termo exato.",
    )


def buscar_texto(ix: Indice, padrao: str, ignorar_caixa: bool = True,
                 max_resultados: int = 20, doc_id: str | None = None) -> str:
    achados = ix.buscar_texto(padrao, ignorar_caixa, max_resultados, doc_id)
    if achados and "erro" in achados[0]:
        return f"Erro na expressão regular: {achados[0]['erro']}"
    partes = [
        f"[{a['doc_id']} p.{a['pagina']}] encontrou {a['match']!r}\n…{_cortar(a['contexto'], 400)}…"
        for a in achados
    ]
    return _juntar(
        partes,
        f"Nenhuma ocorrência de {padrao!r} em nenhum documento. "
        f"Os documentos podem usar outro termo — tente buscar_semantica para descobrir qual.",
    )


def ler_documento(ix: Indice, doc_id: str, pagina_ini: int = 1,
                  pagina_fim: int | None = None) -> str:
    doc = ix.documentos.get(doc_id)
    if not doc:
        proximos = [d for d in ix.documentos if doc_id.lower() in d.lower()][:5]
        dica = f" Talvez: {', '.join(proximos)}" if proximos else ""
        return f"Documento {doc_id!r} não existe no acervo.{dica} Use listar_documentos."

    texto = ix.ler_documento(doc_id, pagina_ini, pagina_fim)
    if not texto.strip():
        return f"[{doc_id}] sem texto nessa faixa de páginas (documento tem {doc['paginas']})."
    fim = min(pagina_fim or pagina_ini + 4, doc["paginas"], pagina_ini + 9)
    cabecalho = (f"[{doc_id} p.{pagina_ini}-{fim} de {doc['paginas']}] {doc['titulo']}\n"
                 f"{doc.get('resumo', '')}\n")
    return cabecalho + "\n" + _cortar(texto, MAX_CHARS_RESULTADO)


def listar_documentos(ix: Indice, filtro_titulo: str | None = None) -> str:
    docs = ix.listar(filtro_titulo)
    if not docs:
        return f"Nenhum documento" + (f" com {filtro_titulo!r} no título." if filtro_titulo else ".")
    linhas = [f"{len(docs)} documento(s) no acervo:"]
    for d in docs:
        linhas.append(
            f"- {d['doc_id']} · {d['paginas']} pág · {d['titulo']}\n  {_cortar(d.get('resumo', ''), 200)}"
        )
    return _juntar(["\n".join(linhas)], "acervo vazio")


EXECUTORES = {
    "buscar_semantica": buscar_semantica,
    "buscar_texto": buscar_texto,
    "ler_documento": ler_documento,
    "listar_documentos": listar_documentos,
}


def executar(ix: Indice, nome: str, argumentos: dict) -> str:
    fn = EXECUTORES.get(nome)
    if fn is None:
        return f"Ferramenta desconhecida: {nome}"
    return fn(ix, **argumentos)
