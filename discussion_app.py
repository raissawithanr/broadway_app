import streamlit as st
import pandas as pd
import altair as alt

# -----------------------------
# Page state
# -----------------------------
if "current_page" not in st.session_state:
    st.session_state.current_page = "Home"

# -----------------------------
# Title & description
# -----------------------------
st.markdown(
    "<h1 style='color: black; font-size: 45px;'>Broadway Database Explorer</h1>",
    unsafe_allow_html=True
)

st.markdown("""
This dataset compiles historical data on Broadway productions, capturing key information such as shows,
performance periods, venues, and audience or financial-related metrics. Its purpose is to provide a
structured view of Broadway activity over time, enabling users to explore trends in performance,
popularity, and commercial outcomes.
""")

# -----------------------------
# Load data
# -----------------------------
@st.cache_data
def load_data():
    return pd.read_csv("broadway_data.csv")

data = load_data()

# -----------------------------
# Column names
# -----------------------------
date_col = "WEEK DATE"
show_col = "SHOW"
gross_col = "THIS WEEK GROSS"
perf_col = "PERFORMANCES"

# -----------------------------
# Clean / coerce types
# -----------------------------
data[date_col] = pd.to_datetime(data[date_col], errors="coerce")
data = data.dropna(subset=[date_col])

data[gross_col] = (
    data[gross_col]
    .astype(str)
    .str.replace(r"[$,]", "", regex=True)
)
data[gross_col] = pd.to_numeric(data[gross_col], errors="coerce").fillna(0)

data[perf_col] = pd.to_numeric(data[perf_col], errors="coerce").fillna(0)

# -----------------------------
# Timeframe filter
# -----------------------------
min_date = data[date_col].min().date()
max_date = data[date_col].max().date()

start_date, end_date = st.slider(
    "Select timeframe (Week Date)",
    min_value=min_date,
    max_value=max_date,
    value=(min_date, max_date)
)

filtered_time = data[
    (data[date_col].dt.date >= start_date) &
    (data[date_col].dt.date <= end_date)
].copy()

# -----------------------------
# Show filter (table only)
# -----------------------------
show_list = sorted(filtered_time[show_col].dropna().unique().tolist())
show_list = ["All shows"] + show_list

selected_show = st.selectbox(
    "Filter table by show (type to autocomplete)",
    options=show_list,
    index=0
)

filtered_table = filtered_time.copy()
if selected_show != "All shows":
    filtered_table = filtered_table[filtered_table[show_col] == selected_show]

# -----------------------------
# Dataset table
# -----------------------------
st.markdown("## Dataset Table")

display_table = filtered_table.copy()
display_table[date_col] = display_table[date_col].dt.strftime("%m-%d-%Y")

st.write(f"Rows in table: {len(display_table):,}")
st.dataframe(display_table, height=900, use_container_width=True)

# -----------------------------
# Rankings
# -----------------------------
st.markdown("## Rankings within Selected Timeframe")

metric_label = st.selectbox(
    "Rank shows by",
    ["Total Performances", "Total Gross (sum of weekly gross)"]
)

rank_type = st.radio(
    "Ranking type",
    ["Top", "Bottom"],
    horizontal=True
)

top_n = st.slider(
    "Number of shows",
    min_value=5,
    max_value=30,
    value=10,
    step=5
)

# Aggregate
agg = (
    filtered_time
    .groupby(show_col, as_index=False)
    .agg({
        perf_col: "sum",
        gross_col: "sum"
    })
)

if metric_label == "Total Performances":
    metric_col = perf_col
    x_axis_title = "Total Number of Performances"
else:
    metric_col = gross_col
    x_axis_title = "Total Gross Revenue (US$ thousands)"

# Remove zeros for Bottom rankings
rank_source = agg.copy()
if rank_type == "Bottom":
    if metric_col == gross_col:
        rank_source = rank_source[rank_source[gross_col] > 0]
    else:
        rank_source = rank_source[rank_source[perf_col] > 0]

ascending = rank_type == "Bottom"

ranked = (
    rank_source
    .sort_values(by=metric_col, ascending=ascending)
    .head(top_n)
)

# -----------------------------
# Horizontal bar chart
# -----------------------------
if metric_col == gross_col:
    plot_data = ranked.copy()
    plot_data["US$ Gross ($K)"] = plot_data[gross_col] / 1_000
    x_field = "US$ Gross ($K):Q"
else:
    plot_data = ranked.copy()
    x_field = f"{perf_col}:Q"

chart = alt.Chart(plot_data).mark_bar().encode(
    x=alt.X(
        x_field,
        title=x_axis_title
    ),
    y=alt.Y(
        f"{show_col}:N",
        sort="-x",
        title="Show"
    ),
    tooltip=list(plot_data.columns)
).properties(
    height=30 * len(plot_data)
)

st.altair_chart(chart, use_container_width=True)

# -----------------------------
# Ranking table
# -----------------------------
ranked_display = ranked.copy()
ranked_display["US$ Gross"] = ranked_display[gross_col].map(lambda x: f"US${x:,.2f}")
ranked_display["US$ Gross ($K)"] = (ranked[gross_col] / 1_000).map(lambda x: f"US${x:,.2f}K")
ranked_display["US$ Gross ($M)"] = (ranked[gross_col] / 1_000_000).map(lambda x: f"US${x:,.2f}M")

st.dataframe(ranked_display, use_container_width=True)

# -----------------------------
# Methodological note
# -----------------------------
if rank_type == "Bottom":
    if metric_col == gross_col:
        st.caption(
            "Note: Bottom gross rankings exclude shows with total gross equal to zero "
            "within the selected timeframe to avoid including inactive or closed productions."
        )
    else:
        st.caption(
            "Note: Bottom performance rankings exclude shows with total performances equal to zero "
            "within the selected timeframe to avoid including inactive or closed productions."
        )
