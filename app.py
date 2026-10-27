import altair as alt
import pandas as pd
import plotly.express as px
import streamlit as st

from src.data_loader import CLASSES, COLUNA_CLASSE, LABELS, VARS_QUANT, load_data
from src.metricas import Kpis, calcular_kpis, gols_por_finalizacao, gols_por_temporada

st.set_page_config(
    page_title="Gols de clube de Lionel Messi",
    page_icon=":material/sports_soccer:",
    layout="wide",
)

# Escala divergente da identidade visual: roxo (r = -1) → neutro (0) → magenta (+1)
ESCALA_CORRELACAO = [[0.0, "#2d223a"], [0.5, "#f5eeec"], [1.0, "#b73779"]]
COR_BARRA = "#8c2981"
CHAVE_GRAFICO_TEMPORADAS = "grafico_temporadas"
PARAM_TEMPORADA = "temporada_sel"


def delta_pontos_percentuais(valor: float, referencia: float) -> str | int:
    diferenca = (valor - referencia) * 100
    return 0 if abs(diferenca) < 0.05 else f"{diferenca:+.1f} p.p."


def delta_minutos(valor: float, referencia: float) -> str | int:
    diferenca = valor - referencia
    return 0 if abs(diferenca) < 0.05 else f"{diferenca:+.1f} min"


def mostrar_kpis(kpis: Kpis, carreira: Kpis) -> None:
    with st.container(horizontal=True):
        st.metric(
            "Gols no recorte",
            f"{kpis.total_gols}",
            delta=f"{kpis.total_gols / carreira.total_gols:.0%} da carreira",
            delta_color="off",
            delta_arrow="off",
            help="Contagem de gols de clube que atendem aos filtros e à temporada selecionada.",
            border=True,
        )
        st.metric(
            "Com assistência",
            f"{kpis.pct_assistencia:.0%}",
            delta=delta_pontos_percentuais(kpis.pct_assistencia, carreira.pct_assistencia),
            delta_color="off",
            delta_description="vs. carreira",
            help="Proporção dos gols que tiveram passe de um companheiro.",
            border=True,
        )
        st.metric(
            "Minuto médio do gol",
            f"{kpis.minuto_medio:.1f}'",
            delta=delta_minutos(kpis.minuto_medio, carreira.minuto_medio),
            delta_color="off",
            delta_description="vs. carreira",
            help="Média do minuto regulamentar do gol (acréscimos contam como 45 ou 90).",
            border=True,
        )
        st.metric(
            "Chute de pé esquerdo",
            f"{kpis.pct_pe_esquerdo:.0%}",
            delta=delta_pontos_percentuais(kpis.pct_pe_esquerdo, carreira.pct_pe_esquerdo),
            delta_color="off",
            delta_description="vs. carreira",
            help="Proporção dos gols marcados com chute de pé esquerdo.",
            border=True,
        )
        st.metric(
            "Gols em casa",
            f"{kpis.pct_casa:.0%}",
            delta=delta_pontos_percentuais(kpis.pct_casa, carreira.pct_casa),
            delta_color="off",
            delta_description="vs. carreira",
            help="Proporção dos gols marcados com o clube como mandante.",
            border=True,
        )


st.title("Gols de clube de Lionel Messi")
st.caption(
    "Cada linha é um gol de clube (FC Barcelona e Paris Saint-Germain, de 2004/05 a "
    "2022/23). A classe da EDA separa gol com assistência de gol individual."
)

df = load_data()

with st.sidebar:
    st.header("Filtros do Dashboard 1")
    st.caption("Os filtros do Dashboard 2 ficam no topo da própria aba.")

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

aba_dashboard1, aba_dashboard2 = st.tabs(
    [":material/scatter_plot: Dashboard 1 · Correlação e distribuição", ":material/leaderboard: Dashboard 2 · KPIs"]
)

# ---------------------------------------------------------------------------
# Dashboard 1: correlação + distribuição das variáveis quantitativas
# ---------------------------------------------------------------------------
with aba_dashboard1:
    df_filtrado = df
    for var, (inicio, fim) in intervalos.items():
        df_filtrado = df_filtrado[df_filtrado[var].between(inicio, fim)]

    st.caption(f"{len(df_filtrado)} de {len(df)} gols dentro dos intervalos escolhidos.")

    col_correlacao, col_distribuicao = st.columns([1, 1.5])

    with col_correlacao:
        with st.container(border=True, height="stretch"):
            st.subheader("Correlação")
            # Variáveis sem variação no recorte (ex.: slider fechado num único valor)
            # geram correlação indefinida, então ficam fora da matriz.
            variaveis_com_variacao = [v for v in variaveis if df_filtrado[v].nunique() > 1]
            variaveis_constantes = [v for v in variaveis if v not in variaveis_com_variacao]

            if len(variaveis) < 2:
                st.info(
                    "Selecione pelo menos 2 variáveis na barra lateral para calcular a correlação.",
                    icon=":material/info:",
                )
            elif len(df_filtrado) < 3:
                st.warning(
                    "Poucos gols no recorte para calcular correlação. Amplie os intervalos.",
                    icon=":material/warning:",
                )
            elif len(variaveis_com_variacao) < 2:
                st.warning(
                    "Menos de 2 variáveis variam dentro dos intervalos atuais. Amplie os intervalos.",
                    icon=":material/warning:",
                )
            else:
                if variaveis_constantes:
                    nomes = ", ".join(LABELS[v].lower() for v in variaveis_constantes)
                    st.caption(f"Fora da matriz por não variar no recorte: {nomes}.")
                matriz = df_filtrado[variaveis_com_variacao].corr()
                rotulos = [LABELS[col] for col in variaveis_com_variacao]
                figura_corr = px.imshow(
                    matriz,
                    x=rotulos,
                    y=rotulos,
                    text_auto=".2f",
                    color_continuous_scale=ESCALA_CORRELACAO,
                    zmin=-1,
                    zmax=1,
                    aspect="auto",
                )
                figura_corr.update_layout(
                    height=440,
                    margin=dict(l=0, r=0, t=24, b=0),
                    coloraxis_colorbar=dict(title="r"),
                )
                figura_corr.update_xaxes(tickangle=-35)
                st.plotly_chart(
                    figura_corr,
                    alt="Matriz de correlação de Pearson entre as variáveis quantitativas selecionadas.",
                )

    with col_distribuicao:
        with st.container(border=True, height="stretch"):
            st.subheader("Distribuição")
            if not variaveis:
                st.info(
                    "Selecione pelo menos 1 variável na barra lateral para ver a distribuição.",
                    icon=":material/info:",
                )
            elif df_filtrado.empty:
                st.warning("Nenhum gol restante com os intervalos atuais.", icon=":material/warning:")
            else:
                var_histograma = st.selectbox(
                    "Variável do histograma",
                    options=variaveis,
                    format_func=lambda col: LABELS[col],
                    key="var_histograma",
                )
                figura_hist = px.histogram(
                    df_filtrado,
                    x=var_histograma,
                    color=COLUNA_CLASSE if separar_por_classe else None,
                    color_discrete_map=CLASSES if separar_por_classe else None,
                    color_discrete_sequence=None if separar_por_classe else [COR_BARRA],
                    nbins=20,
                    labels={var_histograma: LABELS[var_histograma], COLUNA_CLASSE: "Classe"},
                )
                figura_hist.update_layout(
                    bargap=0.05,
                    height=380,
                    margin=dict(l=0, r=0, t=24, b=0),
                    yaxis_title="Gols",
                    legend=dict(orientation="h", yanchor="bottom", y=1.02, x=0),
                )
                st.plotly_chart(
                    figura_hist,
                    alt=f"Distribuição de {LABELS[var_histograma].lower()} nos gols filtrados.",
                )

# ---------------------------------------------------------------------------
# Dashboard 2: KPIs + gráficos de barra agrupados
# ---------------------------------------------------------------------------
with aba_dashboard2:
    with st.container(horizontal=True, vertical_alignment="bottom", gap="medium"):
        clubes = st.pills(
            "Clube",
            options=sorted(df["Club"].unique()),
            selection_mode="multi",
            default=sorted(df["Club"].unique()),
            key="d2_clubes",
        )
        competicoes = st.multiselect(
            "Competição",
            options=df["Competition"].value_counts().index.tolist(),
            default=[],
            placeholder="Todas as competições",
            key="d2_competicoes",
            width=420,
        )

    df_d2 = df[df["Club"].isin(clubes)]
    if competicoes:
        df_d2 = df_d2[df_d2["Competition"].isin(competicoes)]

    # Seleção cruzada: clicar numa barra de temporada filtra os KPIs e o gráfico
    # de finalizações. O estado do clique fica no Session State pela key do gráfico.
    estado_grafico = st.session_state.get(CHAVE_GRAFICO_TEMPORADAS) or {}
    pontos = estado_grafico.get("selection", {}).get(PARAM_TEMPORADA, [])
    temporadas_selecionadas = [
        p["temporada"] for p in pontos if p.get("temporada") in set(df_d2["temporada"])
    ]
    df_recorte = (
        df_d2[df_d2["temporada"].isin(temporadas_selecionadas)] if temporadas_selecionadas else df_d2
    )

    kpis = calcular_kpis(df_recorte)
    kpis_carreira = calcular_kpis(df)

    if kpis is None:
        st.warning("Nenhum gol com os filtros atuais.", icon=":material/warning:")
    else:
        descricao_recorte = " · ".join(
            [
                " e ".join(clubes),
                ", ".join(competicoes) if competicoes else "todas as competições",
                f"temporada {', '.join(temporadas_selecionadas)}"
                if temporadas_selecionadas
                else "todas as temporadas",
            ]
        )
        st.caption(f"Recorte: {descricao_recorte}. Deltas comparam com a carreira inteira.")
        mostrar_kpis(kpis, kpis_carreira)

        col_temporadas, col_finalizacoes = st.columns([1.6, 1])

        with col_temporadas:
            with st.container(border=True, height="stretch"):
                st.subheader("Gols por temporada")
                st.caption("Clique numa barra para filtrar os KPIs e as finalizações. Clique no fundo para limpar.")
                selecao = alt.selection_point(name=PARAM_TEMPORADA, fields=["temporada"])
                grafico_temporadas = (
                    alt.Chart(gols_por_temporada(df_d2))
                    .mark_bar(stroke="#c9b3ae", strokeWidth=0.5)
                    .encode(
                        x=alt.X("temporada:O", title="Temporada", axis=alt.Axis(labelAngle=-45)),
                        y=alt.Y("sum(gols):Q", title="Gols"),
                        color=alt.Color(
                            f"{COLUNA_CLASSE}:N",
                            title=None,
                            scale=alt.Scale(domain=list(CLASSES), range=list(CLASSES.values())),
                            legend=alt.Legend(orient="top"),
                        ),
                        opacity=alt.condition(selecao, alt.value(1.0), alt.value(0.3)),
                        tooltip=[
                            alt.Tooltip("temporada:O", title="Temporada"),
                            alt.Tooltip(f"{COLUNA_CLASSE}:N", title="Classe"),
                            alt.Tooltip("gols:Q", title="Gols"),
                        ],
                    )
                    .add_params(selecao)
                    .properties(height=360)
                )
                st.altair_chart(
                    grafico_temporadas,
                    on_select="rerun",
                    key=CHAVE_GRAFICO_TEMPORADAS,
                    alt="Gráfico de barras empilhadas com os gols por temporada, separados por classe.",
                )

        with col_finalizacoes:
            with st.container(border=True, height="stretch"):
                st.subheader("Como os gols saíram")
                st.caption("Tipo de finalização no recorte, com a participação de cada um.")
                finalizacoes = gols_por_finalizacao(df_recorte)
                barras = (
                    alt.Chart(finalizacoes)
                    .mark_bar(color=COR_BARRA, cornerRadiusEnd=3)
                    .encode(
                        y=alt.Y("finalizacao:N", sort="-x", title=None),
                        x=alt.X("gols:Q", title="Gols"),
                        tooltip=[
                            alt.Tooltip("finalizacao:N", title="Finalização"),
                            alt.Tooltip("gols:Q", title="Gols"),
                            alt.Tooltip("participacao:Q", title="Participação", format=".1%"),
                        ],
                    )
                )
                rotulos = barras.mark_text(align="left", dx=4, color="#2d223a").encode(
                    text=alt.Text("participacao:Q", format=".0%")
                )
                st.altair_chart(
                    (barras + rotulos).properties(height=360),
                    alt="Gráfico de barras horizontais com a quantidade de gols por tipo de finalização.",
                )
