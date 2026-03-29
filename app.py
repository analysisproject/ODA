import pandas as pd
import streamlit as st
import plotly.express as px

st.set_page_config(page_title="ODA Dashboard", layout="wide")

# ====================================
# Load data (ZIP file)
# ====================================

@st.cache_data
def load_data():
    # pandas automatically reads CSV inside zip
    df = pd.read_csv("Table1_Data.zip")
    return df

df = load_data()

# ====================================
# Clean data
# ====================================

df["Year"] = pd.to_numeric(df["Year"], errors="coerce")
df["Value"] = pd.to_numeric(df["Value"], errors="coerce")
df = df.dropna(subset=["Year", "Value"])

# ====================================
# Sidebar filters
# ====================================

st.sidebar.header("Filters")

countries = sorted(df["Donor"].dropna().unique().tolist())

selected_countries = st.sidebar.multiselect(
    "Select countries",
    countries,
    default=["United States", "Germany", "Japan", "France", "United Kingdom"]
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

# ====================================
# Build filtered data
# ====================================

if indicator == "ODA as percent of GNI":

    chart_df = df[
        (df["Aid type"] == "ODA grant equivalent as percent of GNI") &
        (df["Fund flows"] == "Grant equivalents")
    ].copy()

    y_title = "Percent of GNI"
    chart_title = "ODA, as percent of GNI"

else:

    chart_df = df[
        (df["Aid type"] == "Official Development Assistance, grant equivalent measure") &
        (df["Fund flows"] == "Grant equivalents") &
        (df["Amount type"] == "Constant Prices (2023 USD millions)")
    ].copy()

    chart_df["Value"] = chart_df["Value"] / 1000

    y_title = "USD billion (constant 2023 prices)"
    chart_title = "ODA, USD billion"

# ====================================
# Apply filters
# ====================================

chart_df = chart_df[
    (chart_df["Donor"].isin(selected_countries)) &
    (chart_df["Year"] >= selected_years[0]) &
    (chart_df["Year"] <= selected_years[1])
]

# ====================================
# Page title
# ====================================

st.title("ODA Interactive Dashboard")
st.caption("Filter by donor and year range.")

# ====================================
# Plot
# ====================================

fig = px.line(
    chart_df,
    x="Year",
    y="Value",
    color="Donor",
    title=chart_title
)

fig.update_layout(
    xaxis_title="Year",
    yaxis_title=y_title,
    legend_title="Donor"
)

st.plotly_chart(fig, use_container_width=True)

# ====================================
# Data preview
# ====================================

with st.expander("Show filtered data"):
    st.dataframe(chart_df)
