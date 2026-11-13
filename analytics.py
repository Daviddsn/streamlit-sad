"""Leitura do catálogo de cursos da UFS.

Cada linha do CSV é uma oferta (curso + município + nível + turno), não um
curso único. Alunos ativos e concluídos são estoques do extrato, não coorte
e não taxa de evasão.
"""

from __future__ import annotations

import unicodedata
from pathlib import Path

import pandas as pd
import plotly.express as px
import plotly.graph_objects as go

DATA_PATH = Path(__file__).resolve().parent / "cur-csv-cursos-da-ufs.csv"

NAVY = "#0B3A6A"
TEAL = "#1F7A8C"
GOLD = "#C4A35A"
INK = "#152033"
GRID = "#E6ECF5"
PALETTE = [NAVY, TEAL, GOLD, "#3D6B4F", "#8C4A3A", "#4C5B8A", "#6B4C7A"]

NIVEL_LABEL = {
    "GRADUACAO": "Graduação",
    "MESTRADO": "Mestrado",
    "DOUTORADO": "Doutorado",
    "LATO": "Especialização",
    "RESIDENCIA": "Residência",
    "MEDIO": "Educação básica",
}

LABEL_FIXES = {
    "Centro de Ciencias Sociais Aplicadas": "Centro de Ciências Sociais Aplicadas",
    "Ciencias Biologicas": "Ciências Biológicas",
    "Lingüística, Letras e Artes": "Linguística, Letras e Artes",
}

SMALL_WORDS = {
    "de",
    "da",
    "do",
    "das",
    "dos",
    "e",
    "em",
    "à",
    "a",
    "o",
    "para",
    "com",
    "na",
    "no",
    "nos",
    "nas",
}


def br_int(value: float) -> str:
    return f"{int(round(value)):,}".replace(",", ".")


def br_pct(part: float, whole: float, digits: int = 0) -> str:
    if not whole:
        return "0%"
    number = 100 * part / whole
    text = f"{number:.{digits}f}"
    return text.replace(".", ",") + "%"


def fold_key(text: str) -> str:
    decomposed = unicodedata.normalize("NFKD", text or "")
    stripped = "".join(ch for ch in decomposed if not unicodedata.combining(ch))
    return " ".join(stripped.upper().split())


def title_pt(text: str) -> str:
    words = text.split()
    output = []
    for index, word in enumerate(words):
        lower = word.lower()
        if index and lower in SMALL_WORDS:
            output.append(lower)
        elif word.isalpha() and word.isupper() and len(word) <= 4:
            output.append(word)
        else:
            output.append(lower[:1].upper() + lower[1:])
    return " ".join(output)


def prettify(value: object) -> str:
    text = "" if value is None or (isinstance(value, float) and pd.isna(value)) else str(value).strip()
    if not text or text.lower() in {"nan", "none", "null"}:
        return "Não informado"
    text = LABEL_FIXES.get(text, text)
    letters = [ch for ch in text if ch.isalpha()]
    if letters and sum(ch.isupper() for ch in letters) / len(letters) > 0.8:
        text = title_pt(text)
    return LABEL_FIXES.get(text, text)


def _canonical_map(names: pd.Series, weights: pd.Series) -> dict[str, str]:
    frame = pd.DataFrame({"key": names.map(lambda v: fold_key(str(v or ""))), "pretty": names.map(prettify), "w": weights})
    scores = frame.groupby(["key", "pretty"], as_index=False)["w"].sum()
    scores = scores.sort_values(["key", "w", "pretty"], ascending=[True, False, True])
    chosen = scores.drop_duplicates("key")
    return dict(zip(chosen["key"], chosen["pretty"]))


def load_catalog(path: Path | None = None) -> pd.DataFrame:
    source = path or DATA_PATH
    raw = pd.read_csv(source, dtype=str, keep_default_na=False)
    frame = pd.DataFrame()
    frame["nome_original"] = raw["nome"].str.strip()
    frame["coordenacao"] = raw["coordenadores"].map(prettify)
    frame["situacao"] = raw["situacao_curso"].map(lambda v: prettify(v) if str(v).strip() else "Não informada")
    frame["nivel"] = raw["nivel_ensino"].map(lambda v: NIVEL_LABEL.get(str(v).strip(), prettify(v)))
    frame["grau"] = raw["grau_academico"].map(prettify)
    frame["modalidade"] = raw["modalidade_educacao"].map(prettify)
    frame["area"] = raw["area_conhecimento"].map(prettify)
    frame["tipo_oferta"] = raw["tipo_oferta"].map(prettify)
    frame["turno"] = raw["turno"].map(prettify)
    frame["municipio"] = raw["municipio"].map(prettify)
    frame["centro"] = raw["centro"].map(prettify)
    frame["unidade"] = raw["unidade_responsavel"].map(prettify)
    frame["codigo_inep"] = raw["codigo_inep"].str.strip()
    frame["portaria"] = raw["portaria_reconhecimento"].str.strip()
    frame["alunos_ativos"] = pd.to_numeric(raw["alunos_ativos"], errors="coerce").fillna(0).astype(int)
    frame["alunos_concluidos"] = pd.to_numeric(raw["alunos_concluidos"], errors="coerce").fillna(0).astype(int)

    inicio = pd.to_datetime(raw["data_inicio_funcionamento"], format="%d/%m/%Y", errors="coerce")
    ano = inicio.dt.year
    invalido = ano.notna() & ((ano < 1950) | (ano > 2030))
    inicio = inicio.mask(invalido)
    frame["inicio"] = inicio
    frame["ano"] = inicio.dt.year.astype("Int64")

    peso = frame["alunos_ativos"] + frame["alunos_concluidos"]
    curso_map = _canonical_map(frame["nome_original"], peso)
    frame["curso_key"] = frame["nome_original"].map(lambda v: fold_key(str(v or "")))
    frame["curso"] = frame["curso_key"].map(curso_map).map(lambda v: LABEL_FIXES.get(v, v))

    centro_map = _canonical_map(raw["centro"], peso)
    frame["centro_key"] = raw["centro"].map(lambda v: fold_key(str(v or "")))
    frame["centro"] = frame["centro_key"].map(centro_map).map(lambda v: LABEL_FIXES.get(v, v))
    return frame


def kpis(df: pd.DataFrame) -> dict[str, int]:
    return {
        "ofertas": int(len(df)),
        "cursos": int(df["curso_key"].nunique()) if len(df) else 0,
        "ativos": int(df["alunos_ativos"].sum()) if len(df) else 0,
        "concluidos": int(df["alunos_concluidos"].sum()) if len(df) else 0,
        "municipios": int(df.loc[df["municipio"] != "Não informado", "municipio"].nunique()) if len(df) else 0,
        "sem_aluno": int((df["alunos_ativos"] == 0).sum()) if len(df) else 0,
    }


def build_insights(df: pd.DataFrame) -> list[dict[str, str]]:
    if df.empty:
        return [
            {
                "kicker": "Filtro",
                "title": "Nenhuma oferta neste recorte",
                "body": "Afrouxe um filtro na barra lateral para voltar a ver o catálogo.",
            }
        ]

    builders = (
        _insight_territorio,
        _insight_modalidade,
        _insight_nivel,
        _insight_grau,
        _insight_ancoras,
        _insight_expansao,
        _insight_lacunas,
    )
    insights = [item for item in (builder(df) for builder in builders) if item]
    return insights[:6]


def _insight_territorio(df: pd.DataFrame) -> dict[str, str] | None:
    ativos = int(df["alunos_ativos"].sum())
    if ativos <= 0:
        return None
    por_municipio = (
        df[df["municipio"] != "Não informado"]
        .groupby("municipio")["alunos_ativos"]
        .sum()
        .sort_values(ascending=False)
    )
    if por_municipio.empty:
        return None
    topo, valor = por_municipio.index[0], int(por_municipio.iloc[0])
    municipios = int(por_municipio.shape[0])
    if municipios == 1:
        return {
            "kicker": "Território",
            "title": f"O recorte está inteiro em {topo}",
            "body": (
                f"As {br_int(len(df))} ofertas deste filtro e os {br_int(ativos)} alunos ativos "
                f"estão em {topo}."
            ),
        }
    if valor / ativos >= 0.5:
        fora = ativos - valor
        return {
            "kicker": "Território",
            "title": "O mapa é largo; a matrícula é concentrada",
            "body": (
                f"{topo} reúne {br_pct(valor, ativos)} dos alunos ativos "
                f"({br_int(valor)} de {br_int(ativos)}). Os outros {br_int(municipios - 1)} municípios "
                f"dividem {br_int(fora)} alunos. A interiorização aparece primeiro como rede de ofertas, "
                f"não como o mesmo volume de turma."
            ),
        }
    segundo = por_municipio.index[1]
    return {
        "kicker": "Território",
        "title": "A matrícula se divide entre municípios",
        "body": (
            f"{topo} lidera este recorte com {br_pct(valor, ativos)} dos alunos ativos, "
            f"seguido por {segundo} ({br_pct(int(por_municipio.iloc[1]), ativos)}). "
            f"Há oferta em {br_int(municipios)} municípios."
        ),
    }


def _insight_modalidade(df: pd.DataFrame) -> dict[str, str] | None:
    if df["modalidade"].nunique() < 2:
        return None
    grupo = df.groupby("modalidade").agg(ofertas=("curso", "size"), alunos=("alunos_ativos", "sum"))
    if "A Distância" not in grupo.index or "Presencial" not in grupo.index:
        return None
    ofertas = int(len(df))
    ativos = int(df["alunos_ativos"].sum())
    ead_n = int(grupo.loc["A Distância", "ofertas"])
    ead_a = int(grupo.loc["A Distância", "alunos"])
    pres_n = int(grupo.loc["Presencial", "ofertas"])
    pres_a = int(grupo.loc["Presencial", "alunos"])
    if pres_n == 0 or ead_n == 0:
        return None
    densidade_pres = pres_a / pres_n
    densidade_ead = ead_a / ead_n
    texto = (
        f"A educação a distância é {br_pct(ead_n, ofertas)} das ofertas e "
        f"{br_pct(ead_a, ativos) if ativos else '0%'} dos alunos ativos. "
        f"Uma oferta presencial tem, em média, {br_int(densidade_pres)} alunos ativos; "
        f"uma oferta a distância tem {br_int(densidade_ead)}."
    )
    semi = grupo.loc["Semi-Presencial"] if "Semi-Presencial" in grupo.index else None
    if semi is not None and int(semi["ofertas"]) >= 5:
        texto += (
            f" O semipresencial entra com {br_int(int(semi['ofertas']))} ofertas e "
            f"{br_int(int(semi['alunos']))} alunos ativos."
        )
    return {
        "kicker": "Modalidade",
        "title": "EaD abre polo; o presencial segura a turma",
        "body": texto,
    }


def _insight_nivel(df: pd.DataFrame) -> dict[str, str] | None:
    if "Graduação" not in set(df["nivel"]) or df["nivel"].nunique() < 2:
        return None
    ativos = int(df["alunos_ativos"].sum())
    ofertas = int(len(df))
    grad = df[df["nivel"] == "Graduação"]
    stricto = df[df["nivel"].isin(["Mestrado", "Doutorado"])]
    texto = (
        f"A graduação responde por {br_pct(len(grad), ofertas)} das ofertas e "
        f"{br_pct(int(grad['alunos_ativos'].sum()), ativos) if ativos else '0%'} dos alunos ativos."
    )
    if len(stricto):
        texto += (
            f" Mestrado e doutorado mantêm {br_int(int(stricto['alunos_ativos'].sum()))} alunos ativos "
            f"e registram {br_int(int(stricto['alunos_concluidos'].sum()))} concluídos — "
            f"egressos acumulados, não uma taxa de conclusão de coorte."
        )
    return {
        "kicker": "Nível",
        "title": "A graduação é o centro de gravidade",
        "body": texto,
    }


def _insight_grau(df: pd.DataFrame) -> dict[str, str] | None:
    grad = df[df["nivel"] == "Graduação"]
    if grad.empty:
        return None
    lic = grad[grad["grau"].isin(["Licenciatura", "Licenciatura Plena"])]
    bac = grad[grad["grau"] == "Bacharelado"]
    if lic.empty or bac.empty:
        return None
    ativos_grad = int(grad["alunos_ativos"].sum())
    med = grad[grad["grau"] == "Médico"]
    texto = (
        f"Há {br_int(len(lic))} ofertas de licenciatura e {br_int(len(bac))} de bacharelado. "
        f"Os bacharelados concentram {br_pct(int(bac['alunos_ativos'].sum()), ativos_grad) if ativos_grad else '0%'} "
        f"dos alunos ativos da graduação ({br_int(int(bac['alunos_ativos'].sum()))}); "
        f"as licenciaturas, {br_pct(int(lic['alunos_ativos'].sum()), ativos_grad) if ativos_grad else '0%'} "
        f"({br_int(int(lic['alunos_ativos'].sum()))}), em mais polos."
    )
    if len(med):
        texto += (
            f" Medicina, com grau próprio no arquivo, soma {br_int(int(med['alunos_ativos'].sum()))} "
            f"alunos ativos em {br_int(len(med))} ofertas."
        )
    return {
        "kicker": "Grau",
        "title": "Mais licenciaturas no catálogo, mais bacharéis na sala",
        "body": texto,
    }


def _insight_ancoras(df: pd.DataFrame) -> dict[str, str] | None:
    ativos = int(df["alunos_ativos"].sum())
    cursos = int(df["curso_key"].nunique())
    if ativos <= 0 or cursos < 8:
        return None
    ranking = df.groupby("curso")["alunos_ativos"].sum().sort_values(ascending=False).head(5)
    fatia = int(ranking.sum())
    nomes = ", ".join(ranking.index[:4]) + f" e {ranking.index[4]}"
    return {
        "kicker": "Cursos âncora",
        "title": f"Os cinco maiores cursos reúnem {br_pct(fatia, ativos)} dos alunos ativos",
        "body": (
            f"{nomes} somam {br_pct(fatia, ativos)} dos alunos ativos deste recorte "
            f"({br_int(fatia)} de {br_int(ativos)}). Os outros {br_int(cursos - 5)} cursos "
            f"dividem o restante."
        ),
    }


def _insight_expansao(df: pd.DataFrame) -> dict[str, str] | None:
    anos = df["ano"].dropna().astype(int)
    if len(anos) < 20:
        return None
    onda = int(((anos >= 2006) & (anos <= 2009)).sum())
    decada = (anos // 10) * 10
    contagem = decada.value_counts()
    topo = int(contagem.index[0])
    texto = (
        f"A década de {topo} concentra {br_pct(int(contagem.iloc[0]), len(anos))} das "
        f"{br_int(len(anos))} ofertas com data de início válida."
    )
    if onda / len(anos) >= 0.3:
        texto += (
            f" Só o intervalo 2006–2009 responde por {br_int(onda)} delas, no ciclo de abertura "
            f"dos campi do interior e da rede de polos."
        )
    sem_data = int(df["ano"].isna().sum())
    if sem_data:
        texto += f" Outras {br_int(sem_data)} ofertas do recorte não têm data utilizável."
    return {
        "kicker": "Expansão",
        "title": "A criação de cursos tem um período dominante",
        "body": texto,
    }


def _insight_lacunas(df: pd.DataFrame) -> dict[str, str] | None:
    total = len(df)
    if total < 8:
        return None
    sem_aluno = int((df["alunos_ativos"] == 0).sum())
    sem_coord = int((df["coordenacao"] == "Não informado").sum())
    sem_area = int((df["area"] == "Não informado").sum())
    situacao_preenchida = int((df["situacao"] != "Não informada").sum())
    partes = []
    if sem_aluno:
        partes.append(
            f"{br_int(sem_aluno)} ofertas ({br_pct(sem_aluno, total)}) estão sem aluno ativo"
        )
    if sem_coord:
        partes.append(f"{br_int(sem_coord)} não trazem coordenação")
    if sem_area:
        partes.append(f"{br_int(sem_area)} não informam área de conhecimento")
    if not partes:
        return None
    corpo = ". ".join(partes) + "."
    if situacao_preenchida / total < 0.25:
        corpo += (
            " O campo de situação quase não é preenchido, então ele não serve para separar "
            "curso ativo de curso encerrado. Aluno ativo é o melhor sinal do arquivo — "
            "e ainda assim é um estoque, que pode estar desatualizado."
        )
    return {
        "kicker": "Limite do arquivo",
        "title": "O catálogo também mostra o que não foi preenchido",
        "body": corpo[0].upper() + corpo[1:],
    }


def _layout(fig: go.Figure, title: str, height: int = 420) -> go.Figure:
    fig.update_layout(
        title=dict(text=title, font=dict(size=16, color=INK), x=0, xanchor="left"),
        paper_bgcolor="rgba(0,0,0,0)",
        plot_bgcolor="rgba(0,0,0,0)",
        font=dict(family="Arial, sans-serif", color=INK, size=13),
        margin=dict(l=8, r=28, t=72, b=8),
        legend=dict(orientation="h", yanchor="bottom", y=1.02, x=0, title=""),
        bargap=0.28,
        height=height,
        separators=",.",
    )
    fig.update_xaxes(showgrid=False, zeroline=False)
    fig.update_yaxes(gridcolor=GRID, zeroline=False)
    return fig


def chart_modalidade(df: pd.DataFrame) -> go.Figure | None:
    if df.empty or int(df["alunos_ativos"].sum()) <= 0:
        return None
    grupo = (
        df.groupby("modalidade", as_index=False)
        .agg(ofertas=("curso", "size"), alunos=("alunos_ativos", "sum"))
        .sort_values("alunos", ascending=False)
    )
    ofertas = int(grupo["ofertas"].sum())
    alunos = int(grupo["alunos"].sum())
    longo = pd.DataFrame(
        {
            "modalidade": list(grupo["modalidade"]) + list(grupo["modalidade"]),
            "medida": ["Ofertas"] * len(grupo) + ["Alunos ativos"] * len(grupo),
            "percentual": list(grupo["ofertas"] / ofertas * 100) + list(grupo["alunos"] / alunos * 100),
        }
    )
    fig = px.bar(
        longo,
        x="modalidade",
        y="percentual",
        color="medida",
        barmode="group",
        text=longo["percentual"].map(lambda v: f"{v:.0f}%"),
        color_discrete_sequence=[GOLD, NAVY],
    )
    fig.update_traces(textposition="outside", cliponaxis=False)
    fig.update_yaxes(title="", range=[0, 118], ticksuffix="%")
    fig.update_xaxes(title="")
    return _layout(fig, "Onde está a oferta e onde está o aluno", height=420)


def chart_nivel(df: pd.DataFrame) -> go.Figure | None:
    if df.empty:
        return None
    ordem = ["Graduação", "Mestrado", "Doutorado", "Especialização", "Residência", "Educação básica"]
    grupo = df.groupby("nivel", as_index=False).agg(ofertas=("curso", "size"), alunos=("alunos_ativos", "sum"))
    grupo["ordem"] = grupo["nivel"].map({nome: i for i, nome in enumerate(ordem)}).fillna(99)
    grupo = grupo.sort_values("ordem")
    fig = px.bar(
        grupo,
        x="alunos",
        y="nivel",
        orientation="h",
        text="alunos",
        custom_data=["ofertas"],
        color_discrete_sequence=[NAVY],
    )
    fig.update_traces(
        texttemplate="%{x:,}",
        textposition="outside",
        cliponaxis=False,
        hovertemplate="%{y}<br>Alunos ativos: %{x:,}<br>Ofertas: %{customdata[0]}<extra></extra>",
    )
    fig.update_yaxes(title="", categoryorder="array", categoryarray=list(grupo["nivel"]), autorange="reversed")
    fig.update_xaxes(title="Alunos ativos")
    return _layout(fig, "Alunos ativos por nível", height=420)


def chart_cursos(df: pd.DataFrame, limite: int = 12) -> go.Figure | None:
    if df.empty or int(df["alunos_ativos"].sum()) <= 0:
        return None
    grupo = (
        df.groupby("curso", as_index=False)
        .agg(alunos=("alunos_ativos", "sum"), ofertas=("curso", "size"), concluidos=("alunos_concluidos", "sum"))
        .sort_values("alunos", ascending=False)
        .head(limite)
    )
    fig = px.bar(
        grupo,
        x="alunos",
        y="curso",
        orientation="h",
        custom_data=["ofertas", "concluidos"],
        color_discrete_sequence=[TEAL],
    )
    fig.update_traces(
        hovertemplate=(
            "%{y}<br>Alunos ativos: %{x:,}<br>Ofertas: %{customdata[0]}"
            "<br>Concluídos: %{customdata[1]:,}<extra></extra>"
        )
    )
    fig.update_yaxes(title="", categoryorder="total ascending")
    fig.update_xaxes(title="Alunos ativos")
    return _layout(fig, f"{min(limite, grupo.shape[0])} cursos com mais alunos ativos", height=520)


def chart_areas(df: pd.DataFrame) -> go.Figure | None:
    if df.empty:
        return None
    grupo = (
        df.groupby("area", as_index=False)
        .agg(alunos=("alunos_ativos", "sum"), ofertas=("curso", "size"))
    )
    fig = px.bar(
        grupo,
        x="alunos",
        y="area",
        orientation="h",
        custom_data=["ofertas"],
        color_discrete_sequence=[NAVY],
    )
    fig.update_traces(
        hovertemplate="%{y}<br>Alunos ativos: %{x:,}<br>Ofertas: %{customdata[0]}<extra></extra>"
    )
    fig.update_yaxes(title="", categoryorder="total ascending")
    fig.update_xaxes(title="Alunos ativos")
    return _layout(fig, "Alunos ativos por área", height=460)


def chart_anos(df: pd.DataFrame) -> go.Figure | None:
    datados = df.dropna(subset=["ano"])
    if datados.empty:
        return None
    contagem = datados.groupby("ano").size().reset_index(name="ofertas")
    contagem["ano"] = contagem["ano"].astype(int)
    contagem["faixa"] = contagem["ano"].map(lambda ano: "2006–2009" if 2006 <= ano <= 2009 else "Demais anos")
    fig = px.bar(
        contagem,
        x="ano",
        y="ofertas",
        color="faixa",
        color_discrete_map={"2006–2009": GOLD, "Demais anos": NAVY},
    )
    fig.update_layout(xaxis=dict(dtick=5, title=""), yaxis=dict(title="Ofertas com data válida"))
    fig.update_traces(hovertemplate="%{x}: %{y} ofertas<extra></extra>")
    return _layout(fig, "Ano de início das ofertas")


def chart_municipios(df: pd.DataFrame) -> go.Figure | None:
    if df.empty:
        return None
    grupo = (
        df[df["municipio"] != "Não informado"]
        .groupby("municipio", as_index=False)
        .agg(alunos=("alunos_ativos", "sum"), ofertas=("curso", "size"))
    )
    if grupo.empty:
        return None
    grupo["por_oferta"] = (grupo["alunos"] / grupo["ofertas"]).round(1)
    fig = px.bar(
        grupo,
        x="alunos",
        y="municipio",
        orientation="h",
        custom_data=["ofertas", "por_oferta"],
        color_discrete_sequence=[NAVY],
    )
    fig.update_traces(
        hovertemplate=(
            "%{y}<br>Alunos ativos: %{x:,}<br>Ofertas: %{customdata[0]}"
            "<br>Alunos por oferta: %{customdata[1]}<extra></extra>"
        )
    )
    fig.update_yaxes(title="", categoryorder="total ascending")
    fig.update_xaxes(title="Alunos ativos")
    return _layout(fig, "Alunos ativos por município", height=520)


def chart_densidade(df: pd.DataFrame) -> go.Figure | None:
    grupo = (
        df[df["municipio"] != "Não informado"]
        .groupby("municipio", as_index=False)
        .agg(alunos=("alunos_ativos", "sum"), ofertas=("curso", "size"))
    )
    if grupo.empty:
        return None
    grupo["por_oferta"] = grupo["alunos"] / grupo["ofertas"]
    fig = px.bar(
        grupo,
        x="por_oferta",
        y="municipio",
        orientation="h",
        custom_data=["ofertas", "alunos"],
        color_discrete_sequence=[TEAL],
    )
    fig.update_traces(
        hovertemplate=(
            "%{y}<br>Alunos por oferta: %{x:.1f}<br>Ofertas: %{customdata[0]}"
            "<br>Alunos ativos: %{customdata[1]:,}<extra></extra>"
        )
    )
    fig.update_yaxes(title="", categoryorder="total ascending")
    fig.update_xaxes(title="Alunos ativos por oferta")
    return _layout(fig, "Densidade: aluno ativo por oferta", height=520)


def tabela_municipios(df: pd.DataFrame) -> pd.DataFrame:
    grupo = (
        df[df["municipio"] != "Não informado"]
        .groupby("municipio", as_index=False)
        .agg(
            ofertas=("curso", "size"),
            cursos=("curso_key", "nunique"),
            alunos_ativos=("alunos_ativos", "sum"),
            alunos_concluidos=("alunos_concluidos", "sum"),
        )
    )
    if grupo.empty:
        return grupo
    grupo["alunos_por_oferta"] = (grupo["alunos_ativos"] / grupo["ofertas"]).round(1)
    return grupo.sort_values(["alunos_ativos", "ofertas"], ascending=False)
