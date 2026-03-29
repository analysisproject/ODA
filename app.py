import pandas as pd
import streamlit as st
import plotly.graph_objects as go

st.set_page_config(page_title="ODA Dashboard", layout="wide")

# ====================================
# 1. Load data
# ====================================
@st.cache_data
def load_data():
    # If you use zip, replace with: pd.read_csv("Table1_Data.zip")
    df = pd.read_csv("Table1_Data.csv")
    return df

df = load_data()

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

indicator = st.sidebar.selectbox(
    "Select indicator",
    [
        "ODA as percent of GNI",
        "ODA in USD billion"
    ]
)

show_labels = st.sidebar.checkbox("Show end labels", value=True)

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

    # Convert million USD to billion USD
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

# ====================================
# 5. Create selected series
# ====================================
if indicator == "ODA as percent of GNI":
    series_df = build_gni_series(df, selected_countries)
    chart_title = "ODA, as percent of GNI"
    y_title = "Percent of GNI"
else:
    series_df = build_usd_series(df, selected_countries)
    chart_title = "ODA, USD billion"
    y_title = "USD billion (constant 2023 prices)"

# Apply year filter after building the continuous series
series_df = series_df.loc[selected_years[0]:selected_years[1]]

# ====================================
# 6. Page title
# ====================================
st.title("ODA Interactive Dashboard")
st.caption("Pre-2018 uses flows basis, while 2018 onward uses grant equivalent basis.")

# ====================================
# 7. Build Plotly figure
# ====================================
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

    # Add label at the last point if requested
    if show_labels:
        fig.add_trace(
            go.Scatter(
                x=[donor_series.index[-1]],
                y=[donor_series.values[-1]],
                mode="text",
                text=[donor],
                textposition="middle right",
                showlegend=False
            )
        )

# Add shaded region for 2018 onward if visible in selected range
shade_start = max(2018, selected_years[0])
shade_end = selected_years[1]

if shade_start <= shade_end:
    fig.add_vrect(
        x0=shade_start,
        x1=shade_end,
        fillcolor="lightgray",
        opacity=0.25,
        line_width=0
    )

fig.update_layout(
    title=chart_title,
    xaxis_title="Year",
    yaxis_title=y_title,
    template="plotly_white",
    hovermode="x unified",
    legend_title="Donor",
    height=600,
    margin=dict(l=40, r=40, t=80, b=40)
)

# Optional y-axis adjustment for GNI
if indicator == "ODA as percent of GNI":
    fig.update_yaxes(range=[0, 0.9])

st.plotly_chart(fig, use_container_width=True)

# ====================================
# 8. Show filtered data
# ====================================
with st.expander("Show filtered data"):
    st.dataframe(series_df.reset_index())
