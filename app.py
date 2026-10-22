import pandas as pd
import plotly.express as px
import streamlit as st

from src.data_loader import CLASSES, COLUNA_CLASSE, LABELS, VARS_QUANT, load_data

st.set_page_config(
    page_title="Avaliação de correlação entre variáveis quantitativas dos gols de Lionel Messi",
    page_icon=":material/sports_soccer:",
    layout="wide",
)

st.title("Avaliação de correlação entre variáveis quantitativas dos gols de Lionel Messi")
st.caption(
    "Cada linha é um gol de clube. Os filtros da barra lateral usam as variáveis "
    "quantitativas derivadas do `data.csv` (minuto e placares) e a classe da EDA "
    "(gol com assistência vs. gol individual)."
)

df = load_data()

with st.sidebar:
    st.header("Filtros")

    variaveis = st.multiselect(
        "Variáveis quantitativas",
        options=VARS_QUANT,
        default=VARS_QUANT,
        format_func=lambda col: LABELS[col],
        help="Selecione as variáveis quantitativas que deseja analisar no dashboard.",
    )

    separar_por_classe = st.toggle(
        "Distinguir por classe",
        value=False,
        help="Colore a distribuição pela classe (participacao_gols: com assistência ou individual).",
    )

    intervalos = {}
    for var in variaveis:
        if pd.api.types.is_integer_dtype(df[var]):
            minimo, maximo, passo = int(df[var].min()), int(df[var].max()), 1
        else:
            minimo, maximo, passo = float(df[var].min()), float(df[var].max()), 0.1
        intervalos[var] = st.slider(
            f"Intervalo de {LABELS[var].lower()}",
            min_value=minimo,
            max_value=maximo,
            value=(minimo, maximo),
            step=passo,
            key=f"intervalo_{var}",
        )

df_filtrado = df
for var, (inicio, fim) in intervalos.items():
    df_filtrado = df_filtrado[df_filtrado[var].between(inicio, fim)]

st.caption(f"{len(df_filtrado)} de {len(df)} gols dentro dos intervalos escolhidos.")

col_correlacao, col_distribuicao = st.columns([1, 1.5])

with col_correlacao:
    st.subheader("Correlação")
    if len(variaveis) < 2:
        st.warning("Selecione pelo menos 2 variáveis para calcular a correlação.")
    elif df_filtrado.empty:
        st.warning("Nenhum gol restante com os intervalos atuais.")
    else:
        matriz = df_filtrado[variaveis].corr()
        rotulos = [LABELS[col] for col in variaveis]
        figura_corr = px.imshow(
            matriz,
            x=rotulos,
            y=rotulos,
            text_auto=".2f",
            color_continuous_scale="RdBu_r",
            zmin=-1,
            zmax=1,
            aspect="auto",
        )
        figura_corr.update_layout(
            height=480,
            margin=dict(l=0, r=0, t=24, b=0),
            coloraxis_colorbar=dict(title="r"),
        )
        figura_corr.update_xaxes(tickangle=-35)
        st.plotly_chart(
            figura_corr,
            alt="Matriz de correlação de Pearson entre as variáveis quantitativas selecionadas.",
        )

with col_distribuicao:
    st.subheader("Distribuição")
    if not variaveis:
        st.warning("Selecione pelo menos 1 variável para ver a distribuição.")
    elif df_filtrado.empty:
        st.warning("Nenhum gol restante com os intervalos atuais.")
    else:
        var_histograma = st.selectbox(
            "Variável do histograma",
            options=variaveis,
            format_func=lambda col: LABELS[col],
        )
        figura_hist = px.histogram(
            df_filtrado,
            x=var_histograma,
            color=COLUNA_CLASSE if separar_por_classe else None,
            color_discrete_map=CLASSES if separar_por_classe else None,
            nbins=20,
            labels={var_histograma: LABELS[var_histograma], COLUNA_CLASSE: "Classe"},
        )
        figura_hist.update_layout(
            bargap=0.05,
            margin=dict(l=0, r=0, t=24, b=0),
            yaxis_title="Gols",
        )
        st.plotly_chart(
            figura_hist,
            alt=f"Distribuição de {LABELS[var_histograma].lower()} nos gols filtrados.",
        )

st.subheader("Indicadores")

if df_filtrado.empty:
    st.warning("Ajuste os intervalos para calcular os indicadores.")
else:
    n_gols = len(df_filtrado)
    n_assistencia = (df_filtrado[COLUNA_CLASSE] == "Gol com Assistência").sum()
    n_pe_esquerdo = (df_filtrado["Type"] == "Left-footed shot").sum()
    n_casa = (df_filtrado["Venue"] == "H").sum()

    with st.container(horizontal=True):
        st.metric("Gols no recorte", f"{n_gols}", border=True)
        st.metric(
            "Com assistência",
            f"{n_assistencia / n_gols:.0%}",
            border=True,
        )
        st.metric(
            "Minuto médio",
            f"{df_filtrado['minuto'].mean():.1f}",
            border=True,
        )
        st.metric(
            "Chute com o pé esquerdo",
            f"{n_pe_esquerdo / n_gols:.0%}",
            border=True,
        )
        st.metric(
            "Em casa",
            f"{n_casa / n_gols:.0%}",
            border=True,
        )
