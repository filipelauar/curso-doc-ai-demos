"""Baixa o acervo da demo da aula 6.

Três fontes públicas brasileiras, todas sem chave e sem CAPTCHA:

    camara  Projetos de lei da Câmara dos Deputados        (PADRÃO)
            Centenas de documentos, temas muito variados — é a diversidade
            que faz busca semântica e grep serem úteis de formas diferentes.
            Vem com ementa e autor como ground truth.

    pncp    Editais e contratos do Portal Nacional de Contratações Públicas
            Documentos maiores e mais ricos em layout (tabelas, anexos).
            A API é instável: já respondeu 504 por horas. Se falhar, use camara.

    bcb     Atas do Copom do Banco Central
            ~260 PDFs, o download mais confiável dos três. Porém homogêneos,
            o que enfraquece a demonstração de busca semântica.

    uv run python -m ingest.baixar_corpus --fonte camara --quantidade 300

Os metadados da listagem são salvos em `corpus/_metadados.json` — eles dão
ground truth de graça para conferir as respostas do agente.
"""

from __future__ import annotations

import argparse
import json
import re
import sys
import time
from datetime import date, timedelta
from pathlib import Path

import requests

AQUI = Path(__file__).resolve().parent.parent
CORPUS = AQUI / "corpus"

PAUSA = 0.35  # rate limit não é documentado em nenhuma das três fontes
MAX_MB = 12
UA = "curso-doc-ai/1.0 (material didatico)"


# ─────────────────────────────────────────────────────────────────
# utilidades
# ─────────────────────────────────────────────────────────────────
def _sessao() -> requests.Session:
    s = requests.Session()
    s.headers.update({"User-Agent": UA, "Accept": "application/json"})
    return s


def _get(sessao, url, **kw):
    """GET com backoff em 429/5xx. Devolve None quando desiste."""
    for tentativa in range(4):
        try:
            r = sessao.get(url, timeout=90, **kw)
        except requests.RequestException:
            time.sleep(2 * (tentativa + 1))
            continue
        if r.status_code in (429, 500, 502, 503, 504):
            time.sleep(3 * (tentativa + 1))
            continue
        return r
    return None


def _nome_seguro(texto: str, limite: int = 60) -> str:
    texto = re.sub(r"[^\w\s-]", "", texto or "", flags=re.UNICODE).strip()
    return re.sub(r"[\s_]+", "-", texto).lower()[:limite] or "documento"


def _salvar_pdf(dados: bytes, caminho: Path) -> bool:
    """Só grava se for PDF de verdade e couber no limite.

    Filtramos por magic bytes porque várias fontes servem ZIP (às vezes
    ZIP dentro de ZIP) na mesma URL de anexo.
    """
    if not dados.startswith(b"%PDF") or len(dados) > MAX_MB * 1024 * 1024:
        return False
    caminho.write_bytes(dados)
    return True


# ─────────────────────────────────────────────────────────────────
# fonte: Câmara dos Deputados
# ─────────────────────────────────────────────────────────────────
API_CAMARA = "https://dadosabertos.camara.leg.br/api/v2/proposicoes"


def fonte_camara(sessao, quantidade, destino, anos=(2026, 2025), tipos=("PL", "PLP")):
    """Projetos de lei. Duas requisições por PDF (listagem não traz o inteiro teor)."""
    baixados, metadados = 0, []
    for ano in anos:
        for tipo in tipos:
            for pagina in range(1, 40):
                if baixados >= quantidade:
                    return baixados, metadados
                r = _get(sessao, API_CAMARA, params={
                    "siglaTipo": tipo, "ano": ano, "itens": 100,
                    "pagina": pagina, "ordem": "DESC", "ordenarPor": "id",
                })
                if r is None or r.status_code != 200:
                    break
                registros = r.json().get("dados") or []
                if not registros:
                    break
                print(f"— {tipo}/{ano} página {pagina}: {len(registros)} proposições")

                for p in registros:
                    if baixados >= quantidade:
                        return baixados, metadados
                    time.sleep(PAUSA)
                    rd = _get(sessao, p["uri"])
                    if rd is None or rd.status_code != 200:
                        continue
                    det = (rd.json() or {}).get("dados") or {}
                    url = det.get("urlInteiroTeor")
                    if not url:
                        continue

                    time.sleep(PAUSA)
                    rb = _get(sessao, url)
                    if rb is None or rb.status_code != 200:
                        continue

                    doc_id = f"camara-{tipo.lower()}-{p['numero']}-{ano}-{p['id']}"
                    caminho = destino / f"{doc_id}__{_nome_seguro(det.get('ementa'))}.pdf"
                    if not _salvar_pdf(rb.content, caminho):
                        continue
                    baixados += 1
                    metadados.append({
                        "doc_id": doc_id,
                        "arquivo": caminho.name,
                        "fonte": "camara",
                        "titulo": f"{tipo} {p['numero']}/{ano}",
                        "ementa": det.get("ementa"),
                        "tema": det.get("keywords"),
                        "data_apresentacao": det.get("dataApresentacao"),
                        "situacao": (det.get("statusProposicao") or {}).get("descricaoSituacao"),
                        "url": url,
                    })
                    print(f"  [{baixados:4}/{quantidade}] {len(rb.content)/1024:6.0f} KB  {caminho.name[:70]}")
    return baixados, metadados


# ─────────────────────────────────────────────────────────────────
# fonte: PNCP
# ─────────────────────────────────────────────────────────────────
PNCP_CONSULTA = "https://pncp.gov.br/api/consulta/v1/contratacoes/publicacao"
PNCP_ANEXOS = "https://pncp.gov.br/api/pncp/v1/orgaos/{cnpj}/compras/{ano}/{seq}/arquivos"
PNCP_MODALIDADE = 6  # Pregão Eletrônico


def fonte_pncp(sessao, quantidade, destino, dias=20):
    baixados, metadados = 0, []
    fim = date.today() - timedelta(days=7)  # dá tempo de os anexos subirem
    inicio = fim - timedelta(days=dias)
    base = {
        "dataInicial": inicio.strftime("%Y%m%d"),
        "dataFinal": fim.strftime("%Y%m%d"),
        "codigoModalidadeContratacao": PNCP_MODALIDADE,
        "tamanhoPagina": 50,  # a API exige >= 10
    }
    print(f"Janela PNCP: {inicio:%d/%m/%Y} a {fim:%d/%m/%Y}")

    for pagina in range(1, 200):
        if baixados >= quantidade:
            break
        r = _get(sessao, PNCP_CONSULTA, params={**base, "pagina": pagina})
        if r is None or r.status_code != 200:
            print(f"  listagem: HTTP {getattr(r, 'status_code', 'sem resposta')} — "
                  f"o PNCP costuma ficar instável. Tente --fonte camara.")
            break
        registros = r.json().get("data") or []
        if not registros:
            break
        print(f"— página {pagina}: {len(registros)} contratações")

        for c in registros:
            if baixados >= quantidade:
                break
            try:
                cnpj, ano, seq = c["orgaoEntidade"]["cnpj"], c["anoCompra"], c["sequencialCompra"]
            except (KeyError, TypeError):
                continue
            time.sleep(PAUSA)
            ra = _get(sessao, PNCP_ANEXOS.format(cnpj=cnpj, ano=ano, seq=seq))
            if ra is None or ra.status_code != 200:
                continue
            try:
                anexos = ra.json()
            except ValueError:
                continue
            if not isinstance(anexos, list):
                continue

            for anexo in anexos:
                if baixados >= quantidade:
                    break
                url = anexo.get("url")
                if not url:
                    continue
                time.sleep(PAUSA)
                rb = _get(sessao, url)
                if rb is None or rb.status_code != 200:
                    continue

                doc_id = f"pncp-{cnpj}-{ano}-{seq}-{anexo.get('sequencialDocumento', 0)}"
                titulo = anexo.get("titulo") or c.get("objetoCompra")
                caminho = destino / f"{doc_id}__{_nome_seguro(titulo)}.pdf"
                if not _salvar_pdf(rb.content, caminho):
                    continue
                baixados += 1
                metadados.append({
                    "doc_id": doc_id,
                    "arquivo": caminho.name,
                    "fonte": "pncp",
                    "titulo": anexo.get("titulo"),
                    "objeto": c.get("objetoCompra"),
                    "orgao": (c.get("orgaoEntidade") or {}).get("razaoSocial"),
                    "uf": (c.get("unidadeOrgao") or {}).get("ufSigla"),
                    "valor_estimado": c.get("valorTotalEstimado"),
                    "data_publicacao": c.get("dataPublicacaoPncp"),
                    "url": url,
                })
                print(f"  [{baixados:4}/{quantidade}] {len(rb.content)/1024:6.0f} KB  {caminho.name[:70]}")
    return baixados, metadados


# ─────────────────────────────────────────────────────────────────
# fonte: Banco Central (atas do Copom)
# ─────────────────────────────────────────────────────────────────
BCB_LISTA = "https://www.bcb.gov.br/api/servico/sitebcb/copom/atas"
BCB_DETALHE = "https://www.bcb.gov.br/api/servico/sitebcb/copom/atas_detalhes"


def fonte_bcb(sessao, quantidade, destino):
    """Atas do Copom. Nunca monte o nome do arquivo à mão — leia `urlPdfAta`."""
    baixados, metadados = 0, []
    r = _get(sessao, BCB_LISTA, params={"quantidade": 500})
    if r is None or r.status_code != 200:
        print("  não consegui listar as atas do Copom")
        return 0, []
    atas = (r.json() or {}).get("conteudo") or []
    print(f"— {len(atas)} atas disponíveis")

    for ata in atas:
        if baixados >= quantidade:
            break
        nro = ata.get("nroReuniao")
        time.sleep(PAUSA)
        rd = _get(sessao, BCB_DETALHE, params={"nro_reuniao": nro})
        if rd is None or rd.status_code != 200:
            continue
        conteudo = (rd.json() or {}).get("conteudo") or []
        if not conteudo:
            continue
        url = conteudo[0].get("urlPdfAta")
        if not url:
            continue
        if url.startswith("/"):
            url = "https://www.bcb.gov.br" + url

        time.sleep(PAUSA)
        rb = _get(sessao, url)
        if rb is None or rb.status_code != 200:
            continue

        doc_id = f"copom-{nro}"
        caminho = destino / f"{doc_id}__{_nome_seguro(ata.get('titulo'))}.pdf"
        if not _salvar_pdf(rb.content, caminho):
            continue
        baixados += 1
        metadados.append({
            "doc_id": doc_id,
            "arquivo": caminho.name,
            "fonte": "bcb",
            "titulo": ata.get("titulo"),
            "reuniao": nro,
            "data_referencia": ata.get("dataReferencia"),
            "data_publicacao": ata.get("dataPublicacao"),
            "url": url,
        })
        print(f"  [{baixados:4}/{quantidade}] {len(rb.content)/1024:6.0f} KB  {caminho.name[:70]}")
    return baixados, metadados


FONTES = {"camara": fonte_camara, "pncp": fonte_pncp, "bcb": fonte_bcb}


def main() -> int:
    ap = argparse.ArgumentParser(description="Baixa o acervo público da demo da aula 6")
    ap.add_argument("--fonte", choices=list(FONTES), default="camara")
    ap.add_argument("--quantidade", type=int, default=300)
    ap.add_argument("--destino", type=Path, default=CORPUS)
    args = ap.parse_args()

    args.destino.mkdir(parents=True, exist_ok=True)
    print(f"Fonte: {args.fonte}  ·  meta: {args.quantidade} PDFs  ·  destino: {args.destino}\n")

    baixados, metadados = FONTES[args.fonte](_sessao(), args.quantidade, args.destino)

    caminho_meta = args.destino / "_metadados.json"
    anteriores = []
    if caminho_meta.exists():
        try:
            anteriores = json.loads(caminho_meta.read_text(encoding="utf-8"))
        except ValueError:
            anteriores = []
    conhecidos = {m["doc_id"] for m in metadados}
    juntos = metadados + [m for m in anteriores if m.get("doc_id") not in conhecidos]
    caminho_meta.write_text(json.dumps(juntos, ensure_ascii=False, indent=2), encoding="utf-8")

    print(f"\n{baixados} PDFs novos · {len(juntos)} no acervo")
    print(f"metadados (ground truth) em {caminho_meta}")
    if not baixados:
        print("\nNada baixado. Se a fonte era 'pncp', tente: --fonte camara")
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
