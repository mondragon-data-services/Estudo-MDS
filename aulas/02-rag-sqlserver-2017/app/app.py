"""
Quem disse? Busca semântica de frases de políticos
SQL Server 2017 (VARBINARY) + cálculo de similaridade no Python.

Rodar (na pasta da aula):  streamlit run app/app.py
"""
import sys
from pathlib import Path

sys.path.append(str(Path(__file__).resolve().parents[1]))

import pandas as pd
import streamlit as st
from sentence_transformers import SentenceTransformer

from src import banco, config
from src.vetores import IndiceEmMemoria, vetor_para_bytes

st.set_page_config(page_title="Quem disse?", page_icon="🗣️", layout="wide")


# ---------- recursos em cache (carregam uma vez por sessão do servidor) ----------
@st.cache_resource(show_spinner="Carregando o modelo de embeddings...")
def carregar_modelo():
    return SentenceTransformer(config.MODELO_EMBEDDING)


@st.cache_resource(show_spinner="Lendo os vetores do SQL Server 2017...")
def carregar_indice():
    with banco.conectar(config.SQL_DATABASE) as conn:
        indice = IndiceEmMemoria.do_banco(conn, config.MODELO_EMBEDDING)
        frases = pd.read_sql("SELECT * FROM rag.vw_Frases", conn).set_index("FraseId")
    return indice, frases


def busca_palavra_chave(termo: str) -> pd.DataFrame:
    with banco.conectar(config.SQL_DATABASE) as conn:
        return pd.read_sql("EXEC rag.usp_BuscaPalavraChave @Termo = ?", conn, params=[termo])


def busca_semantica(pergunta: str, k: int, minimo: float) -> pd.DataFrame:
    modelo = carregar_modelo()
    indice, frases = carregar_indice()
    vq = modelo.encode(pergunta, normalize_embeddings=True)
    res = [(fid, s) for fid, s in indice.buscar(vq, k) if s >= minimo]
    if not res:
        return pd.DataFrame()
    out = frases.loc[[fid for fid, _ in res]].copy()
    out["Similaridade"] = [s for _, s in res]
    return out.reset_index()


def montar_prompt(pergunta: str, resultados: pd.DataFrame) -> str:
    contexto = "\n".join(
        f'- "{r.Texto}" ({r.Politico}, {r.Ano})' for r in resultados.itertuples()
    )
    return (
        "Responda usando APENAS as frases abaixo. Se não houver resposta, diga que não sabe.\n\n"
        f"Frases recuperadas do SQL Server:\n{contexto}\n\nPergunta: {pergunta}"
    )


def cartao(r, quiz: bool, mostrar_score: bool = True):
    with st.container(border=True):
        st.markdown(f"#### “{r.Texto}”")
        if mostrar_score:
            st.progress(max(0.0, min(1.0, float(r.Similaridade))),
                        text=f"Similaridade: {r.Similaridade:.3f}")
        detalhes = f"**{r.Politico}**, {r.Ano}"
        if getattr(r, "Contexto", None):
            detalhes += f" · {r.Contexto}"
        if quiz:
            with st.expander("Quem disse?"):
                st.markdown(detalhes)
        else:
            st.markdown(detalhes)


# ---------- barra lateral ----------
with st.sidebar:
    st.header("Configuração")
    modo = st.radio("Tipo de busca", ["Semântica", "Palavra-chave", "Comparar as duas"])
    k = st.slider("Quantos resultados", 1, 10, 3)
    minimo = st.slider("Similaridade mínima", 0.0, 1.0, 0.30, 0.05)
    quiz = st.toggle("Modo quiz (esconder o autor)", value=True)
    st.divider()
    st.caption(f"Modelo: `{config.MODELO_EMBEDDING}`")
    st.caption("Banco: SQL Server 2017, vetores em VARBINARY(MAX)")
    if st.button("Recarregar vetores do banco"):
        carregar_indice.clear()
        st.rerun()

# ---------- tela principal ----------
st.title("Quem disse?")
st.write("Digite uma ideia, não precisa ser a frase exata. O SQL Server 2017 guarda os vetores e o Python calcula a similaridade.")

exemplos = ["coragem para enfrentar o pânico", "não desistir nunca da luta",
            "cansado de ver a corrupção vencer", "we will never give up"]
cols = st.columns(len(exemplos))
for c, ex in zip(cols, exemplos):
    if c.button(ex, use_container_width=True):
        st.session_state["pergunta"] = ex

pergunta = st.text_input("Sua busca", key="pergunta", placeholder="ex.: sacrifício e trabalho duro")

if pergunta:
    if modo in ("Semântica", "Comparar as duas"):
        sem = busca_semantica(pergunta, k, minimo)
    if modo in ("Palavra-chave", "Comparar as duas"):
        kw = busca_palavra_chave(pergunta)

    if modo == "Comparar as duas":
        esq, dir_ = st.columns(2)
        with esq:
            st.subheader(f"Palavra-chave (LIKE): {len(kw)}")
            if kw.empty:
                st.info("Nenhuma frase contém esse texto literalmente.")
            for r in kw.itertuples():
                cartao(r, quiz, mostrar_score=False)
        with dir_:
            st.subheader(f"Semântica: {len(sem)}")
            for r in sem.itertuples():
                cartao(r, quiz)
    elif modo == "Palavra-chave":
        if kw.empty:
            st.info("Nenhuma frase contém esse texto literalmente. Tente a busca semântica.")
        for r in kw.itertuples():
            cartao(r, quiz, mostrar_score=False)
    else:
        if sem.empty:
            st.warning("Nada acima da similaridade mínima. Diminua o limite na barra lateral.")
        for r in sem.itertuples():
            cartao(r, quiz)

    if modo != "Palavra-chave" and not sem.empty:
        with st.expander("Ver o prompt de RAG montado com esses resultados"):
            st.code(montar_prompt(pergunta, sem), language="text")

# ---------- cadastrar nova frase ao vivo ----------
st.divider()
with st.expander("Cadastrar uma nova frase (demonstração ao vivo)"):
    with st.form("nova_frase", clear_on_submit=True):
        c1, c2, c3 = st.columns(3)
        nome = c1.text_input("Político")
        pais = c2.text_input("País", value="Brasil")
        ano = c3.number_input("Ano", 1500, 2100, 2020)
        texto = st.text_area("Frase (em português)")
        enviar = st.form_submit_button("Gravar no SQL Server")
    if enviar and nome and texto:
        modelo = carregar_modelo()
        vetor = modelo.encode(texto, normalize_embeddings=True)
        with banco.conectar(config.SQL_DATABASE) as conn:
            cur = conn.cursor()
            cur.execute("""IF NOT EXISTS (SELECT 1 FROM rag.Politico WHERE Nome = ?)
                           INSERT INTO rag.Politico (Nome, Pais) VALUES (?, ?)""", nome, nome, pais)
            fid = cur.execute("""INSERT INTO rag.Frase (PoliticoId, Texto, Ano)
                                 OUTPUT INSERTED.FraseId
                                 SELECT PoliticoId, ?, ? FROM rag.Politico WHERE Nome = ?""",
                              texto, int(ano), nome).fetchval()
            cur.execute("""INSERT INTO rag.FraseEmbedding (FraseId, Modelo, Dimensoes, Vetor)
                           VALUES (?, ?, ?, ?)""",
                        fid, config.MODELO_EMBEDDING, len(vetor), vetor_para_bytes(vetor))
            conn.commit()
        carregar_indice.clear()
        st.success(f"Frase {fid} gravada com {len(vetor)} dimensões ({len(vetor) * 4} bytes). Já pode buscar!")
