"""Visualizador interativo da página com as caixas do OCR.

Por que não `st.image` com as caixas desenhadas: a informação que
interessa na aula — *o que* o OCR leu naquela caixa, com *quanta*
confiança e em *qual* posição — não cabe na imagem. Aqui as caixas são
polígonos SVG por cima da página, e o mouse sobre uma delas abre uma
caixinha com transcrição, tipo, bbox e confiança.

O SVG usa `viewBox` nas unidades da própria página (polegadas no PDF,
pixels na imagem), então os polígonos do OCR entram sem conversão e a
figura continua correta em qualquer largura ou DPI — o mesmo truque que
`render.py` explica.
"""

from __future__ import annotations

import base64
import html as html_mod
import json

import streamlit.components.v1 as components
from PIL import Image

from modelos import Caixa, PaginaOCR
from render import para_png

# Paleta do curso + uma cor por tipo de bloco do Chandra.
CIANO, ROXO, VERDE = "#0891B2", "#7C3AED", "#059669"

CORES = {
    # OCR tradicional (Azure)
    "palavra": CIANO,
    "linha": ROXO,
    # blocos de layout (Chandra) — chave em minúsculas
    "text": CIANO,
    "sectionheader": ROXO,
    "title": ROXO,
    "table": VERDE,
    "tablecell": VERDE,
    "figure": "#D97706",
    "picture": "#D97706",
    "listitem": "#2563EB",
    "listgroup": "#2563EB",
    "equation": "#DB2777",
    "code": "#475569",
    "form": "#0E7490",
    "caption": "#94A3B8",
    "footnote": "#94A3B8",
    "pageheader": "#94A3B8",
    "pagefooter": "#94A3B8",
}

LIMITE_TEXTO = 600  # caracteres mostrados na caixinha


def cor_da(caixa: Caixa) -> str:
    chave = (caixa.rotulo or caixa.tipo or "").lower()
    return CORES.get(chave, CORES.get(caixa.tipo, "#64748B"))


def _cor_confianca(conf: float) -> str:
    if conf < 0.80:
        return "#DC2626"
    if conf < 0.95:
        return "#D97706"
    return VERDE


def _bbox(poligono: list[float]) -> tuple[float, float, float, float]:
    xs = poligono[0::2]
    ys = poligono[1::2]
    return min(xs), min(ys), max(xs), max(ys)


def _fmt(valor: float, unidade: str) -> str:
    return f"{valor:.2f}" if unidade == "inch" else f"{valor:.0f}"


def visualizar(
    imagem: Image.Image,
    pagina: PaginaOCR,
    tipos: tuple[str, ...] = ("palavra",),
    por_confianca: bool = False,
    largura: int = 620,
) -> None:
    """Desenha a página com as caixas e a caixinha de hover."""
    html, altura = montar_html(imagem, pagina, tipos, por_confianca, largura)
    components.html(html, height=altura, scrolling=False)


def montar_html(
    imagem: Image.Image,
    pagina: PaginaOCR,
    tipos: tuple[str, ...] = ("palavra",),
    por_confianca: bool = False,
    largura: int = 620,
) -> tuple[str, int]:
    """Monta o HTML do visualizador. Separado de `visualizar` para poder
    ser gerado e inspecionado fora do Streamlit."""
    png = base64.b64encode(para_png(imagem)).decode("ascii")
    proporcao = imagem.height / imagem.width
    altura_px = int(largura * proporcao) + 8

    if not pagina.largura or not pagina.altura:
        # Sem dimensões de página não há como escalar: mostra só a imagem.
        return (
            f'<img src="data:image/png;base64,{png}" style="width:{largura}px">',
            altura_px,
        )

    formas: list[str] = []
    dados: list[dict] = []
    # A palavra vai por último: no SVG quem hoverga é o elemento de
    # cima, e quando o aluno liga "caixas de linha" junto ele ainda
    # quer ver a palavra ao passar o mouse.
    ordem = {"linha": 0, "bloco": 0, "palavra": 2}
    for caixa in sorted(pagina.caixas, key=lambda c: ordem.get(c.tipo, 1)):
        if tipos and caixa.tipo not in tipos:
            continue
        p = caixa.poligono
        if len(p) < 8:
            continue
        cor = cor_da(caixa)
        if por_confianca and caixa.confianca is not None:
            cor = _cor_confianca(caixa.confianca)

        pontos = " ".join(f"{p[i]},{p[i + 1]}" for i in range(0, len(p) - 1, 2))
        i = len(dados)
        formas.append(
            f'<polygon class="bx" data-i="{i}" points="{pontos}" style="stroke:{cor}"/>'
        )

        x0, y0, x1, y1 = _bbox(p)
        u = pagina.unidade
        texto = caixa.texto or "(sem texto)"
        dados.append(
            {
                "texto": html_mod.escape(texto[:LIMITE_TEXTO])
                + ("…" if len(texto) > LIMITE_TEXTO else ""),
                "tipo": html_mod.escape(caixa.rotulo or caixa.tipo),
                "cor": cor,
                "bbox": f"({_fmt(x0, u)}, {_fmt(y0, u)}) → ({_fmt(x1, u)}, {_fmt(y1, u)}) {u}",
                "tam": f"{_fmt(x1 - x0, u)} × {_fmt(y1 - y0, u)} {u}",
                "conf": None if caixa.confianca is None else round(caixa.confianca, 3),
                "conf_cor": None
                if caixa.confianca is None
                else _cor_confianca(caixa.confianca),
            }
        )

    html = (
        _MOLDE.replace("__PNG__", png)
        .replace("__LARGURA__", str(largura))
        .replace("__VB__", f"0 0 {pagina.largura} {pagina.altura}")
        .replace("__FORMAS__", "".join(formas))
        .replace("__DADOS__", json.dumps(dados, ensure_ascii=False))
    )
    return html, altura_px


# O HTML/JS é curto de propósito: dá para abrir em aula e explicar.
_MOLDE = """
<meta charset="utf-8">
<style>
  #palco { position: relative; width: __LARGURA__px; font: 13px -apple-system, system-ui, sans-serif; }
  #palco img { width: 100%; display: block; }
  #camada { position: absolute; inset: 0; width: 100%; height: 100%; }
  .bx { fill: rgba(0,0,0,0); stroke-width: 1.5; pointer-events: all;
        vector-effect: non-scaling-stroke; }
  .bx:hover { fill: rgba(8,145,178,.18); stroke-width: 3; }
  #tt { position: absolute; display: none; pointer-events: none; z-index: 9;
        max-width: 320px; background: #fff; color: #1E293B;
        border: 1px solid #CBD5E1; border-left: 4px solid #0891B2;
        border-radius: 6px; padding: 8px 10px;
        box-shadow: 0 6px 20px rgba(15,23,42,.18); }
  #tt .val { font-weight: 600; word-wrap: break-word; white-space: pre-wrap;
             max-height: 140px; overflow: hidden; }
  #tt .meta { margin-top: 6px; color: #64748B; font-size: 11.5px;
              font-family: ui-monospace, SFMono-Regular, Menlo, monospace; }
  #tt .tag { display: inline-block; font-size: 10.5px; text-transform: uppercase;
             letter-spacing: .04em; color: #fff; background: #0891B2;
             border-radius: 4px; padding: 1px 6px; margin-bottom: 5px; }
</style>

<div id="palco">
  <img src="data:image/png;base64,__PNG__">
  <svg id="camada" viewBox="__VB__" preserveAspectRatio="none">__FORMAS__</svg>
  <div id="tt"></div>
</div>

<script>
  const dados = __DADOS__;
  const palco = document.getElementById("palco");
  const tt = document.getElementById("tt");

  function conteudo(d) {
    let h = '<span class="tag" style="background:' + d.cor + '">' + d.tipo + '</span>';
    h += '<div class="val">' + d.texto + '</div><div class="meta">';
    if (d.conf !== null) {
      h += 'confiança: <b style="color:' + d.conf_cor + '">' + d.conf.toFixed(3) + '</b><br>';
    }
    h += 'bbox: ' + d.bbox + '<br>tamanho: ' + d.tam + '</div>';
    return h;
  }

  for (const el of document.querySelectorAll(".bx")) {
    el.addEventListener("mouseenter", () => {
      const d = dados[+el.dataset.i];
      tt.innerHTML = conteudo(d);
      tt.style.borderLeftColor = d.cor;
      tt.style.display = "block";
    });
    el.addEventListener("mouseleave", () => { tt.style.display = "none"; });
  }

  palco.addEventListener("mousemove", (e) => {
    const r = palco.getBoundingClientRect();
    let x = e.clientX - r.left + 14, y = e.clientY - r.top + 14;
    x = Math.min(x, r.width - tt.offsetWidth - 4);
    y = Math.min(y, r.height - tt.offsetHeight - 4);
    tt.style.left = Math.max(0, x) + "px";
    tt.style.top = Math.max(0, y) + "px";
  });
</script>
"""
