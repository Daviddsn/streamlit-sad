from __future__ import annotations

import streamlit as st

import analytics

st.set_page_config(
    page_title="Cursos da UFS",
    page_icon="🎓",
    layout="wide",
    initial_sidebar_state="expanded",
)

st.markdown(
    """
    <style>
    .block-container { padding-top: 1.4rem; padding-bottom: 2.5rem; max-width: 1180px; }
    header[data-testid="stHeader"] { background: transparent; }
    footer { visibility: hidden; }
    .hero {
        background: linear-gradient(135deg, #0B3A6A 0%, #14508F 58%, #1F7A8C 100%);
        color: white;
        border-radius: 18px;
        padding: 28px 32px 22px;
        margin-bottom: 14px;
    }
    .hero .eyebrow {
        letter-spacing: 0.14em;
        text-transform: uppercase;
        font-size: 0.74rem;
        color: #E4C98A;
        font-weight: 700;
        margin-bottom: 8px;
    }
    .hero h1 {
        color: white;
        font-size: 2rem;
        line-height: 1.15;
        letter-spacing: -0.03em;
        margin: 0 0 10px;
    }
    .hero p { color: rgba(255,255,255,0.9); font-size: 1.04rem; line-height: 1.5; margin: 0; }
    .kpi {
        background: white;
        border: 1px solid #E4EAF3;
        border-radius: 14px;
        padding: 14px 16px 12px;
        min-height: 108px;
    }
    .kpi-label {
        color: #5C6B80;
        font-size: 0.78rem;
        font-weight: 700;
        letter-spacing: 0.04em;
        text-transform: uppercase;
    }
    .kpi-value { color: #0B3A6A; font-size: 1.7rem; font-weight: 700; line-height: 1.2; margin: 4px 0 2px; }
    .kpi-hint { color: #5C6B80; font-size: 0.82rem; line-height: 1.35; }
    div[data-testid="stCaptionContainer"] { color: #5C6B80; }
    </style>
    """,
    unsafe_allow_html=True,
)


@st.cache_data(show_spinner=False)
def catalogo():
    return analytics.load_catalog()


def opcoes(df, coluna: str) -> list[str]:
    valores = sorted(v for v in df[coluna].dropna().unique() if v != "Não informado")
    if (df[coluna] == "Não informado").any():
        valores.append("Não informado")
    return valores


def aplicar_filtro(df, escolhas: dict[str, list[str]], busca: str, somente_ativos: bool):
    recorte = df
    for coluna, selecionados in escolhas.items():
        if selecionados:
            recorte = recorte[recorte[coluna].isin(selecionados)]
    termo = busca.strip().casefold()
    if termo:
        colunas_busca = ("curso", "coordenacao", "unidade", "municipio", "centro", "area")
        mascara = recorte[colunas_busca[0]].str.casefold().str.contains(termo, na=False, regex=False)
        for coluna in colunas_busca[1:]:
            mascara = mascara | recorte[coluna].str.casefold().str.contains(termo, na=False, regex=False)
        recorte = recorte[mascara]
    if somente_ativos:
        recorte = recorte[recorte["alunos_ativos"] > 0]
    return recorte


def texto_recorte(escolhas: dict[str, list[str]], busca: str, somente_ativos: bool) -> str:
    partes = []
    rotulos = {
        "nivel": "nível",
        "modalidade": "modalidade",
        "municipio": "município",
        "area": "área",
        "grau": "grau",
        "centro": "centro",
    }
    for coluna, selecionados in escolhas.items():
        if not selecionados:
            continue
        amostra = ", ".join(selecionados[:3])
        if len(selecionados) > 3:
            amostra += f" +{len(selecionados) - 3}"
        partes.append(f"{rotulos[coluna]}: {amostra}")
    if busca.strip():
        partes.append(f"busca: {busca.strip()}")
    if somente_ativos:
        partes.append("somente ofertas com aluno ativo")
    if not partes:
        return "Recorte: catálogo completo."
    return "Recorte: " + " · ".join(partes) + "."


def kpi_card(coluna, rotulo: str, valor: str, dica: str) -> None:
    coluna.markdown(
        f"""
        <div class="kpi">
          <div class="kpi-label">{rotulo}</div>
          <div class="kpi-value">{valor}</div>
          <div class="kpi-hint">{dica}</div>
        </div>
        """,
        unsafe_allow_html=True,
    )


def desenhar(fig) -> None:
    if fig is None:
        st.info("Não há dados suficientes neste recorte para este gráfico.")
        return
    st.plotly_chart(fig, width="stretch", config={"displayModeBar": False})


def render_insights(itens: list[dict[str, str]]) -> None:
    for inicio in range(0, len(itens), 3):
        faixa = itens[inicio : inicio + 3]
        colunas = st.columns(3)
        for coluna, item in zip(colunas, faixa):
            with coluna.container(border=True):
                st.caption(item["kicker"].upper())
                st.markdown(f"**{item['title']}**")
                st.write(item["body"])


def painel_catalogo(df) -> None:
    tabela = df.sort_values(["alunos_ativos", "alunos_concluidos"], ascending=False)[
        [
            "curso",
            "alunos_ativos",
            "alunos_concluidos",
            "nivel",
            "grau",
            "modalidade",
            "municipio",
            "area",
            "centro",
            "turno",
            "coordenacao",
            "inicio",
            "codigo_inep",
        ]
    ].rename(
        columns={
            "curso": "Curso",
            "nivel": "Nível",
            "grau": "Grau",
            "modalidade": "Modalidade",
            "municipio": "Município",
            "area": "Área",
            "centro": "Centro",
            "turno": "Turno",
            "coordenacao": "Coordenação",
            "alunos_ativos": "Alunos ativos",
            "alunos_concluidos": "Concluídos",
            "inicio": "Início",
            "codigo_inep": "Código INEP",
        }
    )
    st.dataframe(
        tabela,
        width="stretch",
        hide_index=True,
        height=540,
        column_config={
            "Alunos ativos": st.column_config.NumberColumn(format="%d"),
            "Concluídos": st.column_config.NumberColumn(format="%d"),
            "Início": st.column_config.DateColumn(format="DD/MM/YYYY"),
        },
    )
    st.download_button(
        "Baixar recorte em CSV",
        data=tabela.to_csv(index=False).encode("utf-8-sig"),
        file_name="cursos_ufs_recorte.csv",
        mime="text/csv",
    )


def main() -> None:
    base = catalogo()

    st.sidebar.markdown("### Cursos da UFS")
    st.sidebar.caption("Cada linha do arquivo é uma oferta: curso, nível, município e turno.")
    busca = st.sidebar.text_input("Buscar curso, município ou centro", placeholder="Ex.: Medicina, Lagarto")
    somente_ativos = st.sidebar.toggle("Somente ofertas com aluno ativo", value=False)

    campos = [
        ("nivel", "Nível de ensino"),
        ("modalidade", "Modalidade"),
        ("municipio", "Município"),
        ("area", "Área de conhecimento"),
        ("grau", "Grau acadêmico"),
        ("centro", "Centro"),
    ]
    escolhas = {}
    for coluna, rotulo in campos:
        escolhas[coluna] = st.sidebar.multiselect(rotulo, opcoes(base, coluna), placeholder="Todos")

    recorte = aplicar_filtro(base, escolhas, busca, somente_ativos)
    numeros = analytics.kpis(recorte)
    numeros_base = analytics.kpis(base)

    st.markdown(
        """
        <div class="hero">
          <div class="eyebrow">Universidade Federal de Sergipe</div>
          <h1>Catálogo de cursos em um painel</h1>
          <p>A ferramenta lê o extrato de cursos da UFS e mostra onde estão as ofertas,
          onde estão os alunos e o que o próprio arquivo não consegue afirmar.</p>
        </div>
        """,
        unsafe_allow_html=True,
    )
    st.caption(texto_recorte(escolhas, busca, somente_ativos))

    cartoes = st.columns(6)
    kpi_card(cartoes[0], "Ofertas", analytics.br_int(numeros["ofertas"]), f"de {analytics.br_int(numeros_base['ofertas'])} no arquivo")
    kpi_card(cartoes[1], "Cursos", analytics.br_int(numeros["cursos"]), "nomes distintos no recorte")
    kpi_card(cartoes[2], "Alunos ativos", analytics.br_int(numeros["ativos"]), "estoque, não ingresso do ano")
    kpi_card(cartoes[3], "Concluídos", analytics.br_int(numeros["concluidos"]), "acumulado histórico do extrato")
    kpi_card(cartoes[4], "Municípios", analytics.br_int(numeros["municipios"]), "com pelo menos uma oferta")
    kpi_card(
        cartoes[5],
        "Sem aluno ativo",
        analytics.br_int(numeros["sem_aluno"]),
        analytics.br_pct(numeros["sem_aluno"], numeros["ofertas"]) + " das ofertas do recorte" if numeros["ofertas"] else "—",
    )

    st.markdown("### O que os dados mostram")
    render_insights(analytics.build_insights(recorte))
    st.caption(
        "Concluídos não medem evasão nem sucesso de uma turma. Curso antigo acumula egressos; curso novo ainda não."
    )

    panorama, territorio, catalogo_tab, sobre = st.tabs(["Panorama", "Território", "Catálogo", "Como ler"])

    with panorama:
        esquerda, direita = st.columns(2)
        with esquerda:
            desenhar(analytics.chart_modalidade(recorte))
        with direita:
            desenhar(analytics.chart_nivel(recorte))
        desenhar(analytics.chart_cursos(recorte))
        esquerda, direita = st.columns(2)
        with esquerda:
            desenhar(analytics.chart_areas(recorte))
        with direita:
            desenhar(analytics.chart_anos(recorte))

    with territorio:
        st.markdown(
            "A primeira barra é volume. A segunda é densidade: aluno ativo dividido pelo número de ofertas. "
            "Município com muitas ofertas e barra curta na densidade é polo espalhado, não campus cheio."
        )
        desenhar(analytics.chart_municipios(recorte))
        desenhar(analytics.chart_densidade(recorte))
        ranking = analytics.tabela_municipios(recorte)
        if ranking.empty:
            st.info("Nenhum município neste recorte.")
        else:
            st.dataframe(
                ranking.rename(
                    columns={
                        "municipio": "Município",
                        "ofertas": "Ofertas",
                        "cursos": "Cursos",
                        "alunos_ativos": "Alunos ativos",
                        "alunos_concluidos": "Concluídos",
                        "alunos_por_oferta": "Alunos por oferta",
                    }
                ),
                width="stretch",
                hide_index=True,
            )

    with catalogo_tab:
        st.markdown(f"**{analytics.br_int(len(recorte))} ofertas** no recorte atual. A busca e os filtros da lateral valem aqui.")
        if recorte.empty:
            st.info("Nenhuma oferta encontrada.")
        else:
            painel_catalogo(recorte)

    with sobre:
        st.markdown(
            """
**O que a ferramenta faz.** Lê o CSV de cursos da UFS, junta grafias diferentes do mesmo nome
e deixa filtrar por nível, modalidade, município, área, grau e centro. Os cartões de leitura
e os gráficos acompanham o filtro.

**O que é uma linha.** Uma oferta. Medicina em Aracaju e Medicina em Lagarto são duas linhas.
Letras em vários turnos também. O número de cursos distintos junta essas linhas pelo nome.

**O que dá para afirmar.** Onde o catálogo coloca a oferta, quantos alunos ativos e concluídos
o extrato registra, e quais campos vieram vazios.

**O que não dá para afirmar.** Taxa de evasão, qualidade do curso, demanda do vestibular ou
se a oferta está oficialmente ativa. O campo de situação quase só aparece em residências.
Datas inválidas (ano impossível) ficam de fora da linha do tempo e continuam no catálogo.

**Como apresentar.** Comece pelo catálogo completo, leia os seis cartões e só então filtre
um município ou a graduação. O contraste entre a barra de ofertas e a barra de alunos
é o ponto da modalidade.
            """
        )


if __name__ == "__main__":
    main()
