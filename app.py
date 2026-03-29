import pandas as pd
import streamlit as st
import plotly.graph_objects as go
import zipfile

st.set_page_config(page_title="ODA Dashboard", layout="wide")

# ====================================
# Load data from ZIP
# ====================================
@st.cache_data
def load_data():

    zip_path = "Table1_Data.zip"

    with zipfile.ZipFile(zip_path) as z:
        csv_files = [f for f in z.namelist() if f.endswith(".csv")]

        if len(csv_files) == 0:
            st.error("No CSV file found inside ZIP")
            return pd.DataFrame()

        with z.open(csv_files[0]) as f:
            df = pd.read_csv(f)

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

countries = sorted(df["Donor"].dropna().unique())

selected_countries = st.sidebar.multiselect(
    "Select countries",
    countries,
    default=["France","Germany","Japan","United Kingdom","United States"]
)

year_min = int(df["Year"].min())
year_max = int(df["Year"].max())

selected_years = st.sidebar.slider(
    "Year range",
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
# Build filtered dataset
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
fig = go.Figure()

for donor in selected_countries:

    donor_data = chart_df[chart_df["Donor"] == donor]

    fig.add_trace(
        go.Scatter(
            x=donor_data["Year"],
            y=donor_data["Value"],
            mode="lines",
            name=donor
        )
    )

fig.update_layout(
    title=chart_title,
    xaxis_title="Year",
    yaxis_title=y_title,
    template="plotly_white",
    height=600
)

st.plotly_chart(fig, use_container_width=True)

# ====================================
# Data preview
# ====================================
with st.expander("Show filtered data"):
    st.dataframe(chart_df)
