"""Identidade visual dos gráficos do app.

Um princípio de visualização de dados que vale a aula inteira: **a cor tem
função, não é decoração**. Neste app usamos três papéis diferentes:

* **Categórica** — identidade (cada piloto/equipe tem SEU tom, fixo, que não
  muda quando o filtro muda). Usamos uma ordem fixa de 8 tons, validada para
  daltonismo; nunca "cor por posição no ranking".
* **Sequencial** — magnitude (um único tom do claro ao escuro).
* **Status** — estado (aprovado/reprovado), sempre acompanhado de texto.

Regra prática que evita 90% dos gráficos ruins: escolha a *forma* primeiro
(barra para comparar, linha para evolução, número grande para um só valor) e a
cor por último.
"""

from __future__ import annotations

import plotly.graph_objects as go
import plotly.io as pio

# --- superfícies e tinta ----------------------------------------------------
SUPERFICIE = "#fcfcfb"
PLANO = "#f9f9f7"
TINTA_PRIMARIA = "#0b0b0b"
TINTA_SECUNDARIA = "#52514e"
TINTA_DISCRETA = "#898781"
GRADE = "#e1e0d9"
EIXO = "#c3c2b7"

# --- paleta categórica (ordem fixa, validada para daltonismo) ---------------
CATEGORICA = [
    "#2a78d6",  # 1 azul
    "#eb6834",  # 2 laranja
    "#1baf7a",  # 3 água
    "#eda100",  # 4 amarelo
    "#e87ba4",  # 5 magenta
    "#008300",  # 6 verde
    "#4a3aa7",  # 7 violeta
    "#e34948",  # 8 vermelho
]
MAX_SERIES = len(CATEGORICA)

# --- paleta sequencial (magnitude: um único tom, claro -> escuro) -----------
SEQUENCIAL = [
    "#cde2fb",
    "#9ec5f4",
    "#6da7ec",
    "#3987e5",
    "#2a78d6",
    "#256abf",
    "#1c5cab",
    "#184f95",
]

# --- paleta de status (nunca usada como série) ------------------------------
STATUS = {
    "bom": "#0ca30c",
    "atencao": "#fab219",
    "grave": "#ec835a",
    "critico": "#d03b3b",
}

FONTE = 'system-ui, -apple-system, "Segoe UI", sans-serif'


def registrar_template() -> str:
    """Registra o template Plotly do projeto e o define como padrão."""
    template = go.layout.Template()
    template.layout = go.Layout(
        colorway=CATEGORICA,
        paper_bgcolor=SUPERFICIE,
        plot_bgcolor=SUPERFICIE,
        font=dict(family=FONTE, size=13, color=TINTA_PRIMARIA),
        title=dict(font=dict(size=16, color=TINTA_PRIMARIA), x=0, xanchor="left"),
        margin=dict(l=8, r=8, t=48, b=8),
        hovermode="closest",
        hoverlabel=dict(
            bgcolor=SUPERFICIE,
            bordercolor=EIXO,
            font=dict(family=FONTE, size=12, color=TINTA_PRIMARIA),
        ),
        legend=dict(
            orientation="h",
            yanchor="bottom",
            y=1.02,
            x=0,
            font=dict(size=12, color=TINTA_SECUNDARIA),
            title=None,
        ),
        xaxis=dict(
            gridcolor=GRADE,
            linecolor=EIXO,
            zerolinecolor=EIXO,
            tickfont=dict(color=TINTA_DISCRETA, size=12),
            title=dict(font=dict(color=TINTA_SECUNDARIA, size=12)),
        ),
        yaxis=dict(
            gridcolor=GRADE,
            linecolor=EIXO,
            zerolinecolor=EIXO,
            tickfont=dict(color=TINTA_DISCRETA, size=12),
            title=dict(font=dict(color=TINTA_SECUNDARIA, size=12)),
        ),
        colorscale=dict(sequential=[[i / (len(SEQUENCIAL) - 1), c] for i, c in enumerate(SEQUENCIAL)]),
    )
    pio.templates["f1"] = template
    pio.templates.default = "f1"
    return "f1"


def cores_por_entidade(entidades: list[str]) -> dict[str, str]:
    """Amarra cada entidade (piloto, equipe) a um tom fixo.

    Por que isso importa: se a cor seguisse a *posição* na lista, mudar o filtro
    repintaria todo mundo e o leitor perderia a referência. A cor segue a
    entidade, sempre.
    """
    return {
        entidade: CATEGORICA[i % MAX_SERIES] for i, entidade in enumerate(entidades)
    }


def barra_horizontal(
    df,
    *,
    x: str,
    y: str,
    titulo: str,
    rotulo_x: str = "",
    cor: str | None = None,
    formato_valor: str = ",.0f",
) -> go.Figure:
    """Barra horizontal — a forma certa para *comparar magnitudes* entre nomes.

    Categoria no eixo Y (nome longo cabe), valor no X, ordenado do maior para o
    menor, rótulo direto na ponta da barra (o leitor não precisa mirar no eixo).
    """
    figura = go.Figure(
        go.Bar(
            x=df[x],
            y=df[y],
            orientation="h",
            marker=dict(color=cor or CATEGORICA[0], cornerradius=4),
            text=df[x].map(lambda v: format(v, formato_valor)),
            textposition="outside",
            textfont=dict(color=TINTA_SECUNDARIA, size=12),
            hovertemplate=f"<b>%{{y}}</b><br>{rotulo_x or x}: %{{x:{formato_valor}}}<extra></extra>",
        )
    )
    figura.update_layout(
        title=titulo,
        xaxis_title=rotulo_x,
        yaxis_title="",
        bargap=0.35,
        yaxis=dict(autorange="reversed", showgrid=False),
        height=max(280, 34 * len(df) + 110),
    )
    return figura


def linha_temporal(
    df,
    *,
    x: str,
    y: str,
    serie: str,
    titulo: str,
    rotulo_y: str = "",
    cores: dict[str, str] | None = None,
) -> go.Figure:
    """Linha — a forma certa para *evolução ao longo do tempo*.

    Linha de 2px, marcador de 8px, crosshair unificado no hover: passando o
    mouse em uma rodada o leitor vê todos os pilotos daquela rodada de uma vez.
    """
    cores = cores or cores_por_entidade(sorted(df[serie].unique()))
    figura = go.Figure()
    for nome, grupo in df.groupby(serie, sort=False):
        figura.add_trace(
            go.Scatter(
                x=grupo[x],
                y=grupo[y],
                name=str(nome),
                mode="lines+markers",
                line=dict(width=2, color=cores.get(nome, CATEGORICA[0])),
                marker=dict(size=8, line=dict(width=2, color=SUPERFICIE)),
                hovertemplate=f"<b>{nome}</b><br>{rotulo_y or y}: %{{y:,.0f}}<extra></extra>",
            )
        )
    figura.update_layout(
        title=titulo,
        xaxis_title="Rodada",
        yaxis_title=rotulo_y,
        hovermode="x unified",
        height=460,
    )
    return figura


def barras_agrupadas(
    df,
    *,
    x: str,
    series: dict[str, str],
    titulo: str,
    rotulo_y: str = "",
) -> go.Figure:
    """Barras agrupadas para comparar 2 ou 3 medidas na mesma escala.

    Nunca use dois eixos Y para juntar medidas de escalas diferentes — é o erro
    de gráfico mais comum que existe. Se as escalas divergem, faça dois
    gráficos.
    """
    figura = go.Figure()
    for i, (coluna, rotulo) in enumerate(series.items()):
        figura.add_trace(
            go.Bar(
                x=df[x],
                y=df[coluna],
                name=rotulo,
                marker=dict(color=CATEGORICA[i % MAX_SERIES], cornerradius=4),
                hovertemplate=f"<b>%{{x}}</b><br>{rotulo}: %{{y:,.0f}}<extra></extra>",
            )
        )
    figura.update_layout(
        title=titulo,
        barmode="group",
        bargap=0.3,
        bargroupgap=0.08,
        yaxis_title=rotulo_y,
        xaxis_title="",
        height=420,
    )
    return figura


CSS_APP = f"""
<style>
    .stApp {{ background-color: {PLANO}; }}
    .bloco-kpi {{
        background: {SUPERFICIE};
        border: 1px solid rgba(11,11,11,0.10);
        border-radius: 10px;
        padding: 14px 16px;
        height: 100%;
    }}
    .bloco-kpi .rotulo {{
        color: {TINTA_SECUNDARIA};
        font-size: 12px;
        text-transform: uppercase;
        letter-spacing: .04em;
    }}
    .bloco-kpi .valor {{
        color: {TINTA_PRIMARIA};
        font-size: 30px;
        font-weight: 650;
        line-height: 1.15;
        margin-top: 2px;
    }}
    .bloco-kpi .apoio {{ color: {TINTA_DISCRETA}; font-size: 12px; }}
    .rodape {{ color: {TINTA_DISCRETA}; font-size: 12px; }}
</style>
"""


def cartao_kpi(rotulo: str, valor: str, apoio: str = "") -> str:
    """Um número grande com contexto — quando um único valor é a resposta,
    um gráfico só atrapalha."""
    return (
        f'<div class="bloco-kpi"><div class="rotulo">{rotulo}</div>'
        f'<div class="valor">{valor}</div>'
        f'<div class="apoio">{apoio}</div></div>'
    )
