"""Página "Quem disse?": busca por palavra-chave x busca semântica."""
import time

import pandas as pd
import pyodbc
import streamlit as st

from recursos import carregar_indice, carregar_modelo
from src import banco, config
from src.vetores import vetor_para_bytes

MOTOR_PYTHON = "Python (NumPy)"
MOTOR_TSQL = "SQL Server 2022 (T-SQL)"


def busca_palavra_chave(termo: str) -> pd.DataFrame:
    with banco.conectar(config.SQL_DATABASE) as conn:
        return pd.read_sql("EXEC rag.usp_BuscaPalavraChave @Termo = ?", conn, params=[termo])


def busca_semantica(pergunta: str, k: int, minimo: float, motor: str) -> tuple[pd.DataFrame, float]:
    """Devolve os resultados e o tempo (ms) gasto só no cálculo da similaridade."""
    vq = carregar_modelo().encode(pergunta, normalize_embeddings=True)
    if motor == MOTOR_TSQL:
        return busca_semantica_tsql(vq, k, minimo)

    indice, frases = carregar_indice()
    t = time.perf_counter()
    res = [(fid, s) for fid, s in indice.buscar(vq, k) if s >= minimo]
    ms = (time.perf_counter() - t) * 1000
    if not res:
        return pd.DataFrame(), ms
    out = frases.loc[[fid for fid, _ in res]].copy()
    out["Similaridade"] = [s for _, s in res]
    return out.reset_index(), ms


def busca_semantica_tsql(vq, k: int, minimo: float) -> tuple[pd.DataFrame, float]:
    """Mesma conta, feita no banco: a pergunta vai em VARBINARY, igual aos vetores gravados.

    Não usa o índice em memória, então enxerga na hora frases recém-cadastradas.
    """
    with banco.conectar(config.SQL_DATABASE) as conn:
        t = time.perf_counter()
        res = pd.read_sql("EXEC rag.usp_BuscaSemanticaTSQL @Vetor = ?, @Modelo = ?, @K = ?", conn,
                          params=[vetor_para_bytes(vq), config.MODELO_EMBEDDING, k])
        ms = (time.perf_counter() - t) * 1000
        res = res[res.Similaridade >= minimo]
        if res.empty:
            return pd.DataFrame(), ms
        frases = pd.read_sql("SELECT * FROM rag.vw_Frases", conn)
    out = res[["FraseId", "Similaridade"]].merge(frases, on="FraseId")
    return out.sort_values("Similaridade", ascending=False), ms


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
    motor = st.radio("Onde calcular a similaridade", [MOTOR_PYTHON, MOTOR_TSQL],
                     help="Python: vetores carregados em memória (NumPy). "
                          "T-SQL: o próprio SQL Server 2022 lê o VARBINARY com GENERATE_SERIES.")
    quiz = st.toggle("Modo quiz (esconder o autor)", value=True)
    st.divider()
    st.caption(f"Modelo: `{config.MODELO_EMBEDDING}`")
    st.caption(f"Banco: `{config.SQL_DATABASE}` no SQL Server 2022, vetores em VARBINARY(MAX)")
    if st.button("Recarregar vetores do banco"):
        carregar_indice.clear()
        st.rerun()

# ---------- tela principal ----------
st.title("Quem disse?")
st.write("Digite uma ideia, não precisa ser a frase exata. O SQL Server 2022 guarda os vetores; "
         "a similaridade é calculada no Python ou no próprio banco (escolha na barra lateral).")

exemplos = ["coragem para enfrentar o pânico", "não desistir nunca da luta",
            "cansado de ver a corrupção vencer", "we will never give up"]
cols = st.columns(len(exemplos))
for c, ex in zip(cols, exemplos):
    if c.button(ex, width="stretch"):
        st.session_state["pergunta"] = ex

pergunta = st.text_input("Sua busca", key="pergunta", placeholder="ex.: sacrifício e trabalho duro")

if pergunta:
    if modo in ("Semântica", "Comparar as duas"):
        sem, ms = busca_semantica(pergunta, k, minimo, motor)
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

    if modo != "Palavra-chave":
        st.caption(f"Similaridade calculada em **{motor}**: {ms:.0f} ms")
    if modo != "Palavra-chave" and not sem.empty:
        with st.expander("Ver o prompt de RAG montado com esses resultados"):
            st.code(montar_prompt(pergunta, sem), language="text")

# ---------- cadastrar nova frase ao vivo ----------
AVISO_SQL = ("O SQL Server não respondeu. Confira se a instância está no ar e se a máquina tem memória "
             "livre: com pouca RAM, o Windows joga a memória do SQL Server para o disco e o logon demora "
             "minutos. Feche kernels de notebook que não estiver usando e tente de novo.")


@st.cache_data(ttl=60, show_spinner=False)
def politicos_cadastrados() -> pd.DataFrame:
    with banco.conectar(config.SQL_DATABASE) as conn:
        return pd.read_sql("SELECT Nome, Pais FROM rag.Politico ORDER BY Nome", conn)


def gravar_frase(nome: str, pais: str, ano: int, texto: str, contexto: str | None) -> tuple[int, int]:
    """Grava político (se novo), frase e embedding numa transação só. Devolve (FraseId, dimensões)."""
    vetor = carregar_modelo().encode(texto, normalize_embeddings=True)
    with banco.conectar(config.SQL_DATABASE) as conn:      # sai do with = commit; erro = rollback
        cur = conn.cursor()
        cur.execute("""IF NOT EXISTS (SELECT 1 FROM rag.Politico WHERE Nome = ?)
                           INSERT INTO rag.Politico (Nome, Pais) VALUES (?, ?)""", nome, nome, pais)
        fid = cur.execute("""INSERT INTO rag.Frase (PoliticoId, Texto, Ano, Contexto)
                             OUTPUT INSERTED.FraseId
                             SELECT PoliticoId, ?, ?, ? FROM rag.Politico WHERE Nome = ?""",
                          texto, ano, contexto, nome).fetchval()
        cur.execute("""INSERT INTO rag.FraseEmbedding (FraseId, Modelo, Dimensoes, Vetor)
                       VALUES (?, ?, ?, ?)""",
                    fid, config.MODELO_EMBEDDING, len(vetor), vetor_para_bytes(vetor))
    return fid, len(vetor)


def frase_ja_existe(texto: str) -> bool:
    with banco.conectar(config.SQL_DATABASE) as conn:
        return conn.execute("SELECT COUNT(*) FROM rag.Frase WHERE Texto = ?", texto).fetchval() > 0


st.divider()
with st.expander("Cadastrar uma nova frase (demonstração ao vivo)"):
    try:
        cadastrados = politicos_cadastrados()
    except pyodbc.Error as erro:
        st.error(AVISO_SQL)
        with st.expander("Detalhe técnico"):
            st.code(str(erro), language="text")
        st.stop()

    with st.form("nova_frase", clear_on_submit=True):
        c1, c2, c3 = st.columns([2, 1, 1])
        nome = c1.selectbox("Político", cadastrados.Nome.tolist(), index=None, accept_new_options=True,
                            placeholder="escolha da lista ou digite um nome novo",
                            help="Escolha da lista para a frase ir para o mesmo político "
                                 "(ex.: \"Luiz Inácio Lula da Silva\", e não um novo \"Lula\").")
        pais = c2.text_input("País (se o político for novo)", value="Brasil")
        ano = c3.number_input("Ano", 1500, 2100, 2020)
        texto = st.text_area("Frase (em português)", max_chars=1000)
        contexto = st.text_input("Contexto (opcional)", placeholder="ex.: entrevista, discurso, debate")
        enviar = st.form_submit_button("Gravar no SQL Server")

    if enviar:
        nome, texto = (nome or "").strip(), (texto or "").strip()
        if not nome or not texto:
            st.warning("Preencha o político e a frase.")
        else:
            try:
                if frase_ja_existe(texto):
                    st.info("Essa frase já está no banco.")
                else:
                    with st.spinner("Gerando o embedding e gravando no SQL Server..."):
                        fid, dim = gravar_frase(nome, pais.strip() or "Brasil", int(ano), texto,
                                                contexto.strip() or None)
                    carregar_indice.clear()          # as duas páginas passam a enxergar a frase nova
                    politicos_cadastrados.clear()
                    st.success(f"Frase {fid} gravada para **{nome}** com {dim} dimensões "
                               f"({dim * 4} bytes). Já pode buscar — e ela aparece no Mapa das embeddings!")
            except pyodbc.Error as erro:
                st.error(AVISO_SQL)
                with st.expander("Detalhe técnico"):
                    st.code(str(erro), language="text")
