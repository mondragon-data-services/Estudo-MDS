"""Página "Mapa das embeddings": ver a proximidade semântica em 3D."""
import textwrap

import numpy as np
import pandas as pd
import plotly.graph_objects as go
import streamlit as st

from recursos import carregar_campos_semanticos, carregar_indice, vetorizar
from src import config, mapa

# ---------- cores (paleta validada para o fundo claro do app) ----------
FUNDO = "#fcfcfb"
TINTA = "#0b0b0b"          # texto principal e a "sua busca"
TINTA_2 = "#52514e"        # rótulos
GRADE = "#e1e0d9"
OUTROS = "#898781"         # campos fora da seleção
CORES_CAMPO = ["#2a78d6", "#eb6834", "#1baf7a"]   # no máximo 3 campos por vez (legibilidade)
ESCALA_PROXIMIDADE = [      # uma cor só, do claro (longe) ao escuro (perto)
    [0.0, "#cde2fb"], [0.2, "#9ec5f4"], [0.4, "#6da7ec"],
    [0.6, "#3987e5"], [0.8, "#256abf"], [1.0, "#104281"],
]
ESCALA_NUMEROS = [[0.0, "#2a78d6"], [0.5, "#f0efec"], [1.0, "#e34948"]]  # negativo / zero / positivo

PCA = "PCA (a sombra)"
TSNE = "t-SNE (os vizinhos)"
POR_PROXIMIDADE = "Proximidade da sua busca"
POR_CAMPO = "Campo semântico"

EXEMPLOS = ["coragem para enfrentar o pânico", "nunca vamos desistir da luta",
            "o povo escolhe pelo voto", "futebol no domingo"]


def curto(texto: str, n: int = 32) -> str:
    return texto if len(texto) <= n else texto[: n - 1].rstrip() + "…"


def quebrar(texto: str) -> str:
    return "<br>".join(textwrap.wrap(texto, 60))


@st.cache_data(show_spinner="Calculando o t-SNE (alguns segundos)...")
def tsne(matriz: np.ndarray) -> np.ndarray:
    return mapa.tsne_3d(matriz)


def cores_estaveis(selecionados: list[str]) -> dict[str, str]:
    """A cor acompanha o campo enquanto ele estiver selecionado (não muda ao mexer nos outros)."""
    atual = st.session_state.setdefault("mapa_cores", {})
    for campo in list(atual):
        if campo not in selecionados:
            del atual[campo]
    for campo in selecionados:
        if campo not in atual:
            livres = [c for c in CORES_CAMPO if c not in atual.values()]
            atual[campo] = livres[0]
    return dict(atual)


# ======================================================================
# Dados: frases (vetores lidos do SQL Server) + palavras dos campos
# ======================================================================
indice, frases = carregar_indice()
campos = carregar_campos_semanticos()
nomes_campos = campos.campo.drop_duplicates().tolist()
vet_palavras = vetorizar(tuple(campos.palavra))

# Cada frase "herda" o campo cujo centro (média das palavras) está mais perto dela
centros = np.vstack([vet_palavras[(campos.campo == c).to_numpy()].mean(axis=0) for c in nomes_campos])
centros /= np.linalg.norm(centros, axis=1, keepdims=True)
campo_da_frase = [nomes_campos[i] for i in np.argmax(indice.matriz @ centros.T, axis=1)]

pontos_frases = pd.DataFrame({
    "texto": [frases.loc[i, "Texto"] for i in indice.ids],
    "tipo": "Frase",
    "origem": [f"{frases.loc[i, 'Politico']}, {frases.loc[i, 'Ano']}" for i in indice.ids],
    "campo": campo_da_frase,
})
pontos_palavras = pd.DataFrame({
    "texto": campos.palavra, "tipo": "Palavra", "origem": campos.campo, "campo": campos.campo,
})

# ======================================================================
# Barra lateral
# ======================================================================
with st.sidebar:
    st.header("Mapa")
    metodo = st.radio("Como achatar 384 dimensões em 3", [PCA, TSNE],
                      help="PCA: projeção linear, como uma sombra. O mapa fica parado e a sua busca "
                           "cai nele. t-SNE: reorganiza tudo para deixar vizinhos juntos; o mapa "
                           "muda um pouco a cada busca.")
    colorir = st.radio("Colorir por", [POR_PROXIMIDADE, POR_CAMPO])
    selecionados = nomes_campos[:3]
    if colorir == POR_CAMPO:
        selecionados = st.multiselect("Campos em destaque (até 3)", nomes_campos,
                                      default=["Medo e coragem", "Guerra e resistência", "Fora do tema"],
                                      max_selections=3)
    k = st.slider("Vizinhos ligados à busca", 3, 10, 5)
    descontar = st.checkbox("Comparar descontando o formato", value=True,
                            help="Compara assunto com assunto. Desligue para ver o problema: palavras "
                                 "soltas parecem próximas de qualquer palavra só por serem palavras "
                                 "soltas (ex.: 'traficante' perto de 'conquista').")
    mostrar_frases = st.checkbox("Frases dos políticos", value=True)
    mostrar_palavras = st.checkbox("Palavras dos campos semânticos", value=True)
    todos_rotulos = st.checkbox("Mostrar o nome de todas as palavras", value=False,
                                help="Útil depois de aproximar o zoom. Com tudo rotulado, "
                                     "os nomes se sobrepõem na visão geral.")
    st.caption("As palavras vêm de `data/campos_semanticos.csv`: edite para trocar os campos.")

# ======================================================================
# Cabeçalho e busca
# ======================================================================
st.title("Mapa das embeddings")
st.write(
    "Cada frase virou **uma lista de 384 números** (o embedding gravado em `VARBINARY` no SQL Server). "
    "Ninguém enxerga 384 dimensões, então achatamos tudo em 3 — como a **sombra** de um objeto: "
    "perde detalhe, mas o que tem sentido parecido tende a ficar perto."
)

cols = st.columns(len(EXEMPLOS))
for c, ex in zip(cols, EXEMPLOS):
    if c.button(ex, width="stretch", key=f"ex_mapa_{ex}"):
        st.session_state["mapa_busca"] = ex
st.session_state.setdefault("mapa_busca", EXEMPLOS[0])
busca = st.text_input("Sua busca vira um ponto no mapa", key="mapa_busca",
                      placeholder="digite uma palavra ou uma ideia")

partes, vetores = [], []
if mostrar_frases:
    partes.append(pontos_frases); vetores.append(indice.matriz)
if mostrar_palavras:
    partes.append(pontos_palavras); vetores.append(vet_palavras)
if not partes:
    st.info("Marque frases e/ou palavras na barra lateral.")
    st.stop()
pontos = pd.concat(partes, ignore_index=True)
matriz = np.vstack(vetores).astype("float32")

vq = vetorizar((busca,))[0] if busca.strip() else None
if vq is None and colorir == POR_PROXIMIDADE:
    st.info("Digite algo na busca para colorir por proximidade. Por enquanto, as cores mostram os campos.")
    colorir = POR_CAMPO

# ======================================================================
# Projeção 3D + proximidade de verdade (384 dimensões)
# ======================================================================
preservada = None
if metodo == PCA:
    # O desconto de formato (frase x palavra) fica explicado em src/mapa.py
    coords, componentes, medias, preservada = mapa.pca_3d(matriz, pontos.tipo.to_numpy())
    ponto_busca = None
    if vq is not None:
        media = medias.get(mapa.tipo_do_texto(busca), next(iter(medias.values())))
        ponto_busca = mapa.projetar(vq, componentes, media)[0]
else:
    tudo = matriz if vq is None else np.vstack([matriz, vq])
    xyz = tsne(tudo)
    coords, ponto_busca = (xyz, None) if vq is None else (xyz[:-1], xyz[-1])

pontos[["x", "y", "z"]] = coords
if vq is None:
    pontos["sim"] = np.nan
elif descontar:
    pontos["sim"] = mapa.similaridades_sem_formato(vq, matriz, pontos.tipo.to_numpy(), mapa.tipo_do_texto(busca))
else:
    pontos["sim"] = mapa.similaridades(vq, matriz)
vizinhos = pontos.nlargest(k, "sim") if vq is not None else pontos.iloc[0:0]

# ======================================================================
# Gráfico
# ======================================================================
SIMBOLO = {"Frase": "circle", "Palavra": "diamond"}
TAMANHO = {"Frase": 8, "Palavra": 7}


def dica(df: pd.DataFrame) -> list:
    return [[quebrar(r.texto), r.tipo, r.origem,
             "" if np.isnan(r.sim) else f"Similaridade com a busca: {r.sim:.3f}"]
            for r in df.itertuples()]


HOVER = "<b>%{customdata[0]}</b><br>%{customdata[1]} · %{customdata[2]}<br>%{customdata[3]}<extra></extra>"

fig = go.Figure()
if colorir == POR_PROXIMIDADE:
    cmax = max(0.5, round(float(pontos.sim.max()) + 0.05, 1))
    for tipo in ("Frase", "Palavra"):
        sub = pontos[pontos.tipo == tipo]
        if sub.empty:
            continue
        fig.add_trace(go.Scatter3d(
            x=sub.x, y=sub.y, z=sub.z, name=tipo, showlegend=False, mode="markers",
            marker=dict(size=TAMANHO[tipo], symbol=SIMBOLO[tipo], color=sub.sim,
                        colorscale=ESCALA_PROXIMIDADE, cmin=0, cmax=cmax, showscale=tipo == "Frase",
                        colorbar=dict(title=dict(text="Similaridade<br>com a busca", font=dict(color=TINTA_2)),
                                      thickness=12, len=0.55, tickfont=dict(color=TINTA_2),
                                      outlinewidth=0)),
            customdata=dica(sub), hovertemplate=HOVER,
        ))
    em_destaque = pd.Series(False, index=pontos.index)
else:
    cores = cores_estaveis(selecionados)
    pontos["grupo"] = [c if c in cores else "Outros campos" for c in pontos.campo]
    for grupo in [*cores, "Outros campos"]:
        primeiro = True
        for tipo in ("Frase", "Palavra"):   # um traço por tipo: tamanho e símbolo fixos
            sub = pontos[(pontos.grupo == grupo) & (pontos.tipo == tipo)]
            if sub.empty:
                continue
            fig.add_trace(go.Scatter3d(
                x=sub.x, y=sub.y, z=sub.z, name=grupo, legendgroup=grupo, showlegend=primeiro,
                mode="markers",
                marker=dict(size=TAMANHO[tipo], symbol=SIMBOLO[tipo], color=cores.get(grupo, OUTROS)),
                customdata=dica(sub), hovertemplate=HOVER,
            ))
            primeiro = False
    em_destaque = pontos.grupo != "Outros campos"

# Rótulos seletivos: texto demais vira borrão. Os vizinhos ganham rótulo escuro;
# as palavras dos campos em destaque, rótulo cinza; o resto aparece ao passar o mouse.
eh_vizinho = pontos.index.isin(vizinhos.index)
contexto = pontos[(pontos.tipo == "Palavra") & ~eh_vizinho & (em_destaque | todos_rotulos)]
fig.add_trace(go.Scatter3d(x=contexto.x, y=contexto.y, z=contexto.z, mode="text", text=contexto.texto,
                           textposition="top center", textfont=dict(color=TINTA_2, size=11),
                           hoverinfo="skip", showlegend=False))

if ponto_busca is not None:
    # linhas até os vizinhos de verdade (calculados nas 384 dimensões)
    lx, ly, lz = [], [], []
    for r in vizinhos.itertuples():
        lx += [ponto_busca[0], r.x, None]; ly += [ponto_busca[1], r.y, None]; lz += [ponto_busca[2], r.z, None]
    fig.add_trace(go.Scatter3d(x=lx, y=ly, z=lz, mode="lines", hoverinfo="skip", showlegend=False,
                               line=dict(color=TINTA, width=3, dash="dash")))
    fig.add_trace(go.Scatter3d(x=vizinhos.x, y=vizinhos.y, z=vizinhos.z, mode="text",
                               text=[curto(t, 30) for t in vizinhos.texto],
                               textposition="bottom center", textfont=dict(color=TINTA, size=12),
                               hoverinfo="skip", showlegend=False))
    fig.add_trace(go.Scatter3d(
        x=[ponto_busca[0]], y=[ponto_busca[1]], z=[ponto_busca[2]], name="Sua busca",
        mode="markers+text", text=["<b>SUA BUSCA</b>"], textposition="top center",
        textfont=dict(color=TINTA, size=13), showlegend=colorir == POR_CAMPO,
        marker=dict(size=10, symbol="square", color=TINTA),
        customdata=[[quebrar(busca), "Sua busca", "vetor calculado agora", ""]], hovertemplate=HOVER,
    ))

eixo = dict(showticklabels=False, showgrid=True, gridcolor=GRADE, zeroline=False,
            showbackground=True, backgroundcolor=FUNDO, showspikes=False,
            title=dict(font=dict(color=TINTA_2, size=12)))
fig.update_layout(
    height=680, margin=dict(l=0, r=0, t=10, b=0),
    paper_bgcolor=FUNDO, font=dict(family="system-ui, -apple-system, Segoe UI, sans-serif", color=TINTA_2),
    legend=dict(orientation="h", x=0, y=1.0, title=None, font=dict(color=TINTA)),
    hoverlabel=dict(bgcolor="#ffffff", bordercolor=GRADE, font=dict(color=TINTA)),
    scene=dict(xaxis={**eixo, "title": {**eixo["title"], "text": "eixo 1"}},
               yaxis={**eixo, "title": {**eixo["title"], "text": "eixo 2"}},
               zaxis={**eixo, "title": {**eixo["title"], "text": "eixo 3"}},
               aspectmode="cube", camera=dict(eye=dict(x=1.5, y=1.5, z=1.1))),
    uirevision="mapa",   # mantém a rotação da câmera quando você muda a busca
)
st.plotly_chart(fig, width="stretch", theme=None)
st.caption("● frase de político · ◆ palavra de um campo semântico · ■ sua busca · - - - ligação com os "
           f"{k} vizinhos mais próximos ({'descontando o formato' if descontar else 'cosseno puro'}). "
           "Arraste para girar, role para aproximar, passe o mouse para ler.")

# ======================================================================
# O mapa conta a verdade?
# ======================================================================
if vq is not None:
    esq, dir_ = st.columns([3, 2])
    with esq:
        st.subheader("Vizinhos de verdade (nas 384 dimensões)")
        distancia = np.linalg.norm(coords - ponto_busca, axis=1)
        posicao_mapa = pd.Series(distancia).rank(method="first").astype(int)
        tabela = vizinhos.assign(no_mapa=posicao_mapa[vizinhos.index].to_numpy())
        st.dataframe(
            tabela[["texto", "tipo", "origem", "sim", "no_mapa"]],
            hide_index=True, width="stretch",
            column_config={
                "texto": st.column_config.TextColumn("Texto", width="large"),
                "tipo": "Tipo", "origem": "Autor / campo",
                "sim": st.column_config.ProgressColumn("Similaridade", min_value=0.0, max_value=1.0,
                                                       format="%.3f"),
                "no_mapa": st.column_config.NumberColumn(
                    "Posição no mapa 3D", help="1 = o ponto mais perto da busca no desenho"),
            },
        )
    with dir_:
        st.subheader("O mapa conta a verdade?")
        mantidos = mapa.vizinhos_preservados(pontos.sim.to_numpy(), coords, ponto_busca, k)
        st.metric("Vizinhos que continuam vizinhos no 3D", f"{mantidos} de {k}")
        if preservada is not None:
            st.metric("Informação que os 3 eixos guardam", f"{preservada:.0%}")
            st.write("O PCA guarda só uma parte da variação: a sombra **deforma**. "
                     "Por isso a busca de verdade é feita nas 384 dimensões, nunca no desenho.")
        else:
            st.write("O t-SNE não tenta preservar distâncias longas — ele se dedica a manter "
                     "**vizinhos juntos**. Por isso costuma acertar mais vizinhos, mas grupos distantes "
                     "podem aparecer em posições arbitrárias.")

with st.expander("Como ler este gráfico"):
    st.markdown(f"""
- **Perto = sentido parecido.** O modelo não compara letras: `medo` e `pânico` ficam juntos mesmo sem
  nenhuma letra em comum.
- **Campos semânticos formam nuvens.** Palavras do mesmo tema se agrupam; o campo *Fora do tema*
  (futebol, chocolate…) é o controle: não tem nada a ver com política e fica espalhado, longe das frases.
- **Frase inteira × palavra solta.** Só por causa do formato, frases e palavras ocupam regiões
  diferentes do espaço. Sem cuidado, o eixo principal do PCA mostraria apenas "é frase ou é palavra?".
  Por isso o PCA desconta essa diferença (cada tipo é centralizado na sua própria média) e os eixos
  ficam para o **assunto**.
- **Por que "traficante" ficava perto de "conquista"?** Com o cosseno puro, uma palavra solta
  parece próxima de *qualquer* outra palavra solta (≈ 0,6), só pelo formato — e uma frase inteira
  sobre traficantes fica atrás (≈ 0,4). Com **"Comparar descontando o formato"** ligado, cada vetor
  perde a média do seu tipo e a comparação passa a ser de assunto com assunto. Desligue a opção
  e busque `traficante` para mostrar o problema à turma.
- **Os eixos não têm nome nem unidade.** São combinações das 384 dimensões escolhidas para mostrar
  o máximo possível em 3D.
- **A cor por campo das frases é um palpite:** cada frase herda o campo cujo centro está mais perto dela.
- **Multilíngue:** tente `courage`, `freedom` ou `we will never surrender` — caem perto dos equivalentes em português.
- O modelo é o `{config.MODELO_EMBEDDING.split('/')[-1]}`: ele é quem decide o que é "parecido".
""")

# ======================================================================
# Os 384 números por dentro
# ======================================================================
with st.expander("Os 384 números por dentro: a impressão digital de cada texto"):
    rotulos = [f"{r.tipo}: {curto(r.texto, 40)}" for r in pontos.itertuples()]
    escolhas_padrao = []
    if vq is not None:
        ordem = pontos.sim.to_numpy().argsort()
        escolhas_padrao = [rotulos[ordem[-1]], rotulos[ordem[-2]], rotulos[ordem[0]]]
    escolhas = st.multiselect("Compare até 4 textos", rotulos, default=escolhas_padrao, max_selections=4)
    linhas, nomes = [], []
    if vq is not None:
        linhas.append(vq); nomes.append(f"Sua busca: {curto(busca, 40)}")
    for e in escolhas:
        i = rotulos.index(e)
        linhas.append(matriz[i]); nomes.append(e)
    if linhas:
        m = np.vstack(linhas)
        # escala pelo percentil 98: uma ou duas dimensões extremas não apagam o padrão do resto
        limite = float(np.percentile(np.abs(m), 98))
        heat = go.Figure(go.Heatmap(
            z=m, y=nomes, x=list(range(m.shape[1])), colorscale=ESCALA_NUMEROS,
            zmid=0, zmin=-limite, zmax=limite, xgap=0, ygap=2,
            colorbar=dict(title=dict(text="valor", font=dict(color=TINTA_2)), thickness=10,
                          tickfont=dict(color=TINTA_2), outlinewidth=0),
            hovertemplate="%{y}<br>dimensão %{x}: %{z:.3f}<extra></extra>",
        ))
        heat.update_layout(
            height=110 + 52 * len(nomes), margin=dict(l=10, r=0, t=10, b=50),
            paper_bgcolor=FUNDO, plot_bgcolor=FUNDO,
            font=dict(family="system-ui, -apple-system, Segoe UI, sans-serif", color=TINTA_2),
            xaxis=dict(title=dict(text="dimensão (0 a 383)", standoff=12), showgrid=False,
                       zeroline=False, automargin=True),
            yaxis=dict(autorange="reversed", showgrid=False, automargin=True,
                       tickfont=dict(color=TINTA, size=12)),
        )
        st.plotly_chart(heat, width="stretch", theme=None)
        st.caption("Azul = número negativo, vermelho = positivo. Textos com sentido parecido têm "
                   "**padrões** parecidos — é isso que o cosseno mede, dimensão por dimensão.")
        if len(linhas) > 1:
            sims = m @ m[0]
            st.write(" · ".join(f"**{curto(n, 40)}**: {s:.3f}" for n, s in zip(nomes[1:], sims[1:])),
                     "(cosseno puro com a primeira linha)")

with st.expander("Tabela com todos os pontos"):
    st.dataframe(
        pontos[["texto", "tipo", "origem", "campo", "sim", "x", "y", "z"]].sort_values("sim", ascending=False),
        hide_index=True, width="stretch",
        column_config={"sim": st.column_config.NumberColumn("Similaridade", format="%.3f"),
                       "campo": "Campo (palpite para frases)"},
    )
