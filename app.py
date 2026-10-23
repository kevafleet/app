
import streamlit as st
import pandas as pd
import numpy as np
import plotly.express as px

st.set_page_config(
    page_title="StockScreen Analytics",
    page_icon="📊",
    layout="wide"
)

st.markdown("""
<style>
.block-container {padding-top: 1.5rem; max-width: 1450px;}
[data-testid="stMetric"] {
    background: #f4f7fb;
    border: 1px solid #dbe4f0;
    padding: 14px;
    border-radius: 12px;
}
h1, h2, h3 {letter-spacing: -0.02em;}
</style>
""", unsafe_allow_html=True)

st.title("📊 StockScreen Analytics")
st.caption(
    "Financial screening • P/E, Book-to-Market, "
    "Scaled Net Operating Assets (NOA)"
)

# 1. Load company universe
try:
    df = pd.read_csv("universe.csv")
except Exception as e:
    st.error(f"Could not load universe.csv: {e}")
    st.info(
        "Ensure universe.csv is in the same GitHub repository "
        "directory as app.py and is a valid CSV file."
    )
    st.stop()

# Normalize headers before accessing any columns
df.columns = df.columns.astype(str).str.strip()

# Standardize common column name variations
rename_map = {}
for col in df.columns:
    normalized = col.strip().lower()

    if normalized in ("ticker", "symbol"):
        rename_map[col] = "Ticker"
    elif normalized in ("company", "company name", "name"):
        rename_map[col] = "Company"
    elif normalized in ("sector", "gics sector", "industry sector"):
        rename_map[col] = "Sector"
    elif normalized in ("p/e", "pe", "pe ratio", "p/e ratio"):
        rename_map[col] = "P/E"
    elif normalized in (
        "book-to-market ratio", "book to market ratio",
        "book/market", "b/m"
    ):
        rename_map[col] = "Book-to-market ratio"
    elif normalized in (
        "scaled net operating assets",
        "scaled noa", "noa"
    ):
        rename_map[col] = "Scaled net operating assets"
    elif normalized in ("price", "share price"):
        rename_map[col] = "Price"

df = df.rename(columns=rename_map)

# Required company identifier
if "Ticker" not in df.columns:
    st.error(
        "universe.csv must contain a Ticker column. "
        f"Columns found: {df.columns.tolist()}"
    )
    st.stop()

# Add optional columns if the CSV does not contain them
if "Company" not in df.columns:
    df["Company"] = df["Ticker"]

if "Sector" not in df.columns:
    df["Sector"] = "Unknown"

for col in [
    "Price",
    "P/E",
    "Book-to-market ratio",
    "Scaled net operating assets"
]:
    if col not in df.columns:
        df[col] = np.nan
    else:
        df[col] = pd.to_numeric(df[col], errors="coerce")

df["Ticker"] = df["Ticker"].astype(str).str.strip().str.upper()
df["Company"] = df["Company"].fillna(df["Ticker"]).astype(str)
df["Sector"] = (
    df["Sector"].fillna("Unknown").astype(str).str.strip()
)
df = df[df["Ticker"].ne("") & df["Ticker"].ne("NAN")]
df = df.drop_duplicates(subset=["Ticker"]).reset_index(drop=True)

if df.empty:
    st.error("No valid company tickers were found in universe.csv.")
    st.stop()

if len(df) < 500:
    st.warning(
        f"Your dataset contains {len(df)} unique tickers. "
        "The assignment target is at least 500 companies."
    )

# 2. Sidebar scoring controls
with st.sidebar:
    st.header("Screening Controls")
    st.subheader("Ranking Weights")

    w_pe = st.slider("P/E Ratio Weight", 0, 100, 35)
    w_bm = st.slider("Book-to-Market Weight", 0, 100, 35)
    w_noa = st.slider("Scaled NOA Weight", 0, 100, 30)

    st.caption("Weights are normalized automatically.")

# 3. Screen controls
st.subheader("1. Define your screen")

available_sectors = sorted(df["Sector"].unique().tolist())

c1, c2, c3 = st.columns(3)

with c1:
    sectors = st.multiselect(
        "Sectors to include",
        options=available_sectors,
        default=available_sectors
    )

with c2:
    max_pe = st.number_input(
        "Maximum P/E (0 = ignore)",
        min_value=0.0,
        value=60.0,
        step=5.0
    )

with c3:
    min_bm = st.number_input(
        "Minimum Book-to-Market (0 = ignore)",
        min_value=0.0,
        value=0.1,
        step=0.1
    )

# 4. Apply filters
filtered = df[df["Sector"].isin(sectors)].copy()

if max_pe > 0:
    filtered = filtered[
        filtered["P/E"].isna() | (filtered["P/E"] <= max_pe)
    ]

if min_bm > 0:
    filtered = filtered[
        filtered["Book-to-market ratio"].isna()
        | (filtered["Book-to-market ratio"] >= min_bm)
    ]

# 5. Calculate within-sector percentile scores
def percentile_score(series, higher_is_better=True):
    valid = series.notna()
    result = pd.Series(np.nan, index=series.index, dtype=float)

    if valid.any():
        ranks = series[valid].rank(pct=True, method="average")
        result.loc[valid] = (
            ranks if higher_is_better else 1 - ranks
        )

    return result

metric_columns = [
    "P/E",
    "Book-to-market ratio",
    "Scaled net operating assets"
]

if not filtered.empty:
    # Calculate peer ranks within each sector
    grouped = filtered.groupby("Sector", dropna=False)

    filtered["P/E Score"] = grouped["P/E"].transform(
        lambda s: percentile_score(s, higher_is_better=False)
    )
    filtered["B/M Score"] = grouped[
        "Book-to-market ratio"
    ].transform(
        lambda s: percentile_score(s, higher_is_better=True)
    )
    filtered["NOA Score"] = grouped[
        "Scaled net operating assets"
    ].transform(
        lambda s: percentile_score(s, higher_is_better=False)
    )

    # Only use metrics with available data for each company.
    # Renormalize weights when a metric is missing.
    raw_weights = {
        "P/E Score": w_pe,
        "B/M Score": w_bm,
        "NOA Score": w_noa
    }

    score_cols = list(raw_weights)
    score_matrix = filtered[score_cols]
    weight_series = pd.Series(raw_weights, dtype=float)

    weighted_scores = score_matrix.mul(weight_series, axis=1)
    available_weights = (
        score_matrix.notna().mul(weight_series, axis=1).sum(axis=1)
    )

    filtered["Composite Score"] = (
        weighted_scores.sum(axis=1, min_count=1)
        .div(available_weights.replace(0, np.nan))
        * 100
    )

    filtered = filtered.sort_values(
        "Composite Score", ascending=False, na_position="last"
    ).reset_index(drop=True)

    filtered.insert(0, "Rank", range(1, len(filtered) + 1))

# 6. Results
st.subheader("2. Results")

m1, m2, m3 = st.columns(3)
m1.metric("Total Universe Size", f"{len(df):,}")
m2.metric("Passing Screen", f"{len(filtered):,}")

median_score = (
    filtered["Composite Score"].median()
    if not filtered.empty else np.nan
)
m3.metric(
    "Median Composite Score",
    f"{median_score:.1f}" if pd.notna(median_score) else "—"
)

if filtered.empty:
    st.warning("No companies passed the current filters.")
    st.stop()

if filtered["Composite Score"].notna().sum() == 0:
    st.warning(
        "No composite scores could be calculated. "
        "Check whether your CSV contains numeric financial metrics."
    )

display_cols = [
    "Rank", "Ticker", "Company", "Sector", "Price", "P/E",
    "Book-to-market ratio", "Scaled net operating assets",
    "Composite Score"
]

st.dataframe(
    filtered[display_cols],
    use_container_width=True,
    hide_index=True,
    column_config={
        "Composite Score": st.column_config.ProgressColumn(
            "Composite Score",
            min_value=0,
            max_value=100,
            format="%.1f"
        )
    }
)

# 7. Charts
chart_data = filtered.dropna(subset=["Composite Score"])

if not chart_data.empty:
    left, right = st.columns(2)

    with left:
        st.markdown("#### Top 15 Companies by Composite Score")
        top = chart_data.head(15).sort_values("Composite Score")

        fig = px.bar(
            top,
            x="Composite Score",
            y="Ticker",
            orientation="h",
            color="Composite Score",
            hover_data=["Company", "Sector", "P/E"],
            title="Top 15 Ranking"
        )
        st.plotly_chart(fig, use_container_width=True)

    with right:
        st.markdown("#### Book-to-Market vs. Scaled NOA")

        scatter_data = filtered.dropna(
            subset=[
                "Book-to-market ratio",
                "Scaled net operating assets"
            ]
        )

        if not scatter_data.empty:
            fig2 = px.scatter(
                scatter_data,
                x="Book-to-market ratio",
                y="Scaled net operating assets",
                color="Sector",
                hover_name="Ticker",
                hover_data=["Company", "Composite Score"],
                title="B/M vs. Scaled NOA"
            )
            st.plotly_chart(fig2, use_container_width=True)
        else:
            st.info("Not enough data for the scatter plot.")

# 8. Export
csv_data = filtered.to_csv(index=False).encode("utf-8")
st.download_button(
    "Download Screen Results (CSV)",
    data=csv_data,
    file_name="stockscreen_results.csv",
    mime="text/csv"
)

with st.expander("Dataset diagnostics"):
    st.write("Loaded columns:", df.columns.tolist())
    st.write("Unique tickers:", df["Ticker"].nunique())
    st.write("Sector counts:")
    st.dataframe(
        df["Sector"].value_counts().rename_axis("Sector").reset_index(
            name="Companies"
        ),
        use_container_width=True,
        hide_index=True
    )
