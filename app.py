import streamlit as st
import pandas as pd
import numpy as np
import plotly.express as px

st.set_page_config(page_title="StockScreen Analytics", page_icon="📊", layout="wide")

st.markdown("""
<style>
.block-container {padding-top: 1.5rem; max-width: 1450px;}
[data-testid="stMetric"] {background: #f4f7fb; border: 1px solid #dbe4f0; padding: 14px; border-radius: 12px;}
h1, h2, h3 {letter-spacing: -0.02em;}
</style>
""", unsafe_allow_html=True)

st.title("📊 StockScreen Analytics")
st.caption("Interactive financial screening • P/E, Book-to-Market, & Scaled Net Operating Assets (NOA)")

# Load universe.csv automatically
try:
    df = pd.read_csv("universe.csv")
except Exception as e:
    st.error(f"Error loading universe.csv: {e}")
    st.stop()

# Setup Sidebar weights for scoring
with st.sidebar:
    st.header("Screening Controls")
    st.subheader("Ranking Weights")
    w_pe = st.slider("P/E Ratio Weight", 0, 100, 35)
    w_bm = st.slider("Book-to-Market Weight", 0, 100, 35)
    w_noa = st.slider("Scaled Net Operating Assets Weight", 0, 100, 30)
    st.caption("Weights are normalized automatically to total 100%.")

# Financial Threshold Controls in Main Panel
st.subheader("1. Define your screen")
available_sectors = sorted(df["Sector"].fillna("Unknown").astype(str).unique().tolist())

c1, c2, c3 = st.columns(3)
with c1:
    sectors = st.multiselect("Sectors to include", available_sectors, default=available_sectors)
with c2:
    max_pe = st.number_input("Maximum P/E (0 = ignore)", min_value=0.0, value=60.0, step=5.0)
with c3:
    min_bm = st.number_input("Minimum Book-to-market ratio (0 = ignore)", min_value=0.0, value=0.1, step=0.1)

filtered = df.copy()
if sectors:
    filtered = filtered[filtered["Sector"].fillna("Unknown").astype(str).isin(sectors)]
if max_pe > 0 and "P/E" in filtered.columns:
    filtered = filtered[filtered["P/E"].isna() | (filtered["P/E"] <= max_pe)]
if min_bm > 0 and "Book-to-market ratio" in filtered.columns:
    filtered = filtered[filtered["Book-to-market ratio"].isna() | (filtered["Book-to-market ratio"] >= min_bm)]

# Calculate percentiles and scoring
def pct_score(s, higher_is_better=True):
    rank = s.rank(pct=True)
    return rank if higher_is_better else 1 - rank

if not filtered.empty:
    filtered["P/E Score"] = pct_score(filtered["P/E"], higher_is_better=False)
    filtered["B/M Score"] = pct_score(filtered["Book-to-market ratio"], higher_is_better=True)
    filtered["NOA Score"] = pct_score(filtered["Scaled net operating assets"], higher_is_better=False)

    w_sum = w_pe + w_bm + w_noa
    if w_sum == 0:
        weights = {"pe": 1/3, "bm": 1/3, "noa": 1/3}
    else:
        weights = {"pe": w_pe / w_sum, "bm": w_bm / w_sum, "noa": w_noa / w_sum}

    filtered["Composite Score"] = 100 * (
        filtered["P/E Score"] * weights["pe"] +
        filtered["B/M Score"] * weights["bm"] +
        filtered["NOA Score"] * weights["noa"]
    )
    filtered = filtered.sort_values("Composite Score", ascending=False).reset_index(drop=True)
    filtered.insert(0, "Rank", range(1, len(filtered) + 1))

st.subheader("2. Results")
m1, m2, m3 = st.columns(3)
m1.metric("Total Universe Size", f"{len(df):,}")
m2.metric("Passing Screen", f"{len(filtered):,}")
m3.metric("Median Composite Score", f"{filtered['Composite Score'].median():.1f}" if not filtered.empty else "—")

if filtered.empty:
    st.warning("No companies passed the current filters.")
    st.stop()

display_cols = ["Rank", "Ticker", "Company", "Sector", "Price", "P/E", "Book-to-market ratio", "Scaled net operating assets", "Composite Score"]
st.dataframe(filtered[display_cols], use_container_width=True, hide_index=True,
             column_config={"Composite Score": st.column_config.ProgressColumn("Composite Score", min_value=0, max_value=100, format="%.1f")})

left, right = st.columns(2)
with left:
    st.markdown("#### Top 15 Companies by Composite Score")
    top = filtered.head(15).sort_values("Composite Score")
    fig = px.bar(top, x="Composite Score", y="Ticker", orientation="h", color="Composite Score",
                 hover_data=["Company", "Sector", "P/E", "Book-to-market ratio"], title="Top 15 Ranking")
    st.plotly_chart(fig, use_container_width=True)

with right:
    st.markdown("#### Value (B/M) vs Operating Efficiency (NOA)")
    fig2 = px.scatter(filtered, x="Book-to-market ratio", y="Scaled net operating assets", color="Sector",
                      hover_name="Ticker", hover_data=["Company", "Composite Score"], title="B/M vs Scaled NOA")
    st.plotly_chart(fig2, use_container_width=True)
