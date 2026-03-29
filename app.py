import pandas as pd
import streamlit as st
import plotly.graph_objects as go
import zipfile

st.set_page_config(page_title="ODA Dashboard", layout="wide")

# ====================================
# 1. Load data from ZIP
# ====================================
@st.cache_data
def load_data():
    zip_path = "Table1_Data.zip"

    with zipfile.ZipFile(zip_path) as z:
        csv_files = [f for f in z.namelist() if f.endswith(".csv")]

        if not csv_files:
            return pd.DataFrame()

        with z.open(csv_files[0]) as f:
            df = pd.read_csv(f)

    return df


df = load_data()

if df.empty:
    st.error("No CSV file found inside Table1_Data.zip.")
    st.stop()

# ====================================
# 2. Clean data
# ====================================
df["Year"] = pd.to_numeric(df["Year"], errors="coerce")
df["Value"] = pd.to_numeric(df["Value"], errors="coerce")
df = df.dropna(subset=["Year", "Value"]).copy()
df["Year"] = df["Year"].astype(int)

# ====================================
# 3. Sidebar filters
# ====================================
st.sidebar.header("Filters")

all_countries = sorted(df["Donor"].dropna().unique().tolist())

default_countries = [
    c for c in ["France", "Germany", "Japan", "United Kingdom", "United States"]
    if c in all_countries
]

selected_countries = st.sidebar.multiselect(
    "Select countries",
    all_countries,
    default=default_countries
)

year_min = int(df["Year"].min())
year_max = int(df["Year"].max())

selected_years = st.sidebar.slider(
    "Select year range",
    min_value=year_min,
    max_value=year_max,
    value=(1960, 2024)
)

# ====================================
# 4. Build continuous series
#    Pre-2018: flows basis
#    2018+:   grant equivalent basis
# ====================================
def build_gni_series(data, providers):
    gni_pre = data[
        (data["Donor"].isin(providers)) &
        (data["Aid type"] == "ODA flows basis, as percent of GNI") &
        (data["Fund flows"] == "Net Disbursements")
    ][["Donor", "Year", "Value"]].copy()

    gni_post = data[
        (data["Donor"].isin(providers)) &
        (data["Aid type"] == "ODA grant equivalent as percent of GNI") &
        (data["Fund flows"] == "Grant equivalents")
    ][["Donor", "Year", "Value"]].copy()

    gni_all = pd.concat(
        [
            gni_pre[gni_pre["Year"] < 2018],
            gni_post[gni_post["Year"] >= 2018]
        ],
        ignore_index=True
    )

    gni_pivot = gni_all.pivot_table(
        index="Year",
        columns="Donor",
        values="Value",
        aggfunc="first"
    ).sort_index()

    full_years = pd.Index(range(1960, 2025), name="Year")
    gni_pivot = gni_pivot.reindex(full_years)

    return gni_pivot


def build_usd_series(data, providers):
    usd_pre = data[
        (data["Donor"].isin(providers)) &
        (data["Aid type"] == "I. Official Development Assistance (ODA) (I.A + I.B)") &
        (data["Fund flows"] == "Net Disbursements") &
        (data["Amount type"] == "Constant Prices (2023 USD millions)")
    ][["Donor", "Year", "Value"]].copy()

    usd_post = data[
        (data["Donor"].isin(providers)) &
        (data["Aid type"] == "Official Development Assistance, grant equivalent measure") &
        (data["Fund flows"] == "Grant equivalents") &
        (data["Amount type"] == "Constant Prices (2023 USD millions)")
    ][["Donor", "Year", "Value"]].copy()

    usd_pre["Value"] = usd_pre["Value"] / 1000
    usd_post["Value"] = usd_post["Value"] / 1000

    usd_all = pd.concat(
        [
            usd_pre[usd_pre["Year"] < 2018],
            usd_post[usd_post["Year"] >= 2018]
        ],
        ignore_index=True
    )

    usd_pivot = usd_all.pivot_table(
        index="Year",
        columns="Donor",
        values="Value",
        aggfunc="first"
    ).sort_index()

    full_years = pd.Index(range(1960, 2025), name="Year")
    usd_pivot = usd_pivot.reindex(full_years)

    return usd_pivot


gni_df = build_gni_series(df, selected_countries)
usd_df = build_usd_series(df, selected_countries)

# Apply year filter after series construction
gni_df = gni_df.loc[selected_years[0]:selected_years[1]]
usd_df = usd_df.loc[selected_years[0]:selected_years[1]]

# ====================================
# 5. Page title
# ====================================
st.title("ODA in historical perspective: 1960-2024")
st.caption(
    "Please note: from 2018 onwards, ODA is measured based on grant equivalents, "
    "USD, constant 2023 prices."
)

# ====================================
# 6. Helper function to build a chart
# ====================================
def make_figure(series_df, chart_title, y_title, y_range=None):
    fig = go.Figure()

    for donor in series_df.columns:
        donor_series = series_df[donor].dropna()

        if donor_series.empty:
            continue

        fig.add_trace(
            go.Scatter(
                x=donor_series.index,
                y=donor_series.values,
                mode="lines",
                name=donor,
                line=dict(width=2)
            )
        )

    shade_start = max(2018, selected_years[0])
    shade_end = selected_years[1]

    if shade_start <= shade_end:
        fig.add_vrect(
            x0=shade_start,
            x1=shade_end,
            fillcolor="lightgray",
            opacity=0.35,
            line_width=0
        )

        if y_range is not None:
            label_y = y_range[0] + (y_range[1] - y_range[0]) * 0.05
        else:
            y_min = series_df.min().min()
            y_max = series_df.max().max()
            if pd.isna(y_min) or pd.isna(y_max):
                label_y = 0
            else:
                label_y = y_min + (y_max - y_min) * 0.05

        fig.add_annotation(
            x=(shade_start + shade_end) / 2,
            y=label_y,
            text="Grant equivalent basis",
            textangle=-90,
            showarrow=False,
            font=dict(size=10, color="gray"),
            xref="x",
            yref="y"
        )

    fig.update_layout(
        title=chart_title,
        xaxis_title="",
        yaxis_title=y_title,
        template="plotly_white",
        hovermode="x unified",
        height=500,
        margin=dict(l=30, r=20, t=60, b=20),
        legend_title="Donor"
    )

    fig.update_xaxes(
        showgrid=False,
        tickangle=-45
    )

    fig.update_yaxes(
        showgrid=True,
        gridcolor="rgba(0,0,0,0.08)"
    )

    if y_range is not None:
        fig.update_yaxes(range=y_range)

    return fig

# ====================================
# 7. Build both charts
# ====================================
fig_gni = make_figure(
    gni_df,
    "ODA, as percent of GNI",
    "Percent of GNI",
    y_range=[0, 0.9]
)

fig_usd = make_figure(
    usd_df,
    "ODA, USD billion",
    "USD billion (constant 2023 prices)"
)

# ====================================
# 8. Show charts side by side
# ====================================
col1, col2 = st.columns(2)

with col1:
    st.plotly_chart(fig_gni, use_container_width=True)

with col2:
    st.plotly_chart(fig_usd, use_container_width=True)

# ====================================
# 9. Show filtered data
# ====================================
with st.expander("Show filtered data: ODA as percent of GNI"):
    st.dataframe(gni_df.reset_index())

with st.expander("Show filtered data: ODA in USD billion"):
    st.dataframe(usd_df.reset_index())
