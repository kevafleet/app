
import streamlit as st
import pandas as pd
import numpy as np
import yfinance as yf
import plotly.express as px
from io import StringIO

st.set_page_config(page_title="StockScreen Analytics", page_icon="📊", layout="wide")

st.markdown("""
<style>
.block-container {padding-top: 1.5rem; max-width: 1450px;}
[data-testid="stMetric"] {background: #f4f7fb; border: 1px solid #dbe4f0; padding: 14px; border-radius: 12px;}
h1, h2, h3 {letter-spacing: -0.02em;}
</style>
""", unsafe_allow_html=True)

st.title("📊 StockScreen Analytics")
st.caption("Interactive financial screening • transparent scoring • company-level comparisons")
st.info("Educational analysis only. Ratios are screening signals, not guarantees of future performance. Data coverage and reporting dates vary by company.")

FALLBACK_TICKERS = [
    # --- Technology & Communications (Software, Semi, Hardware) ---
    "AAPL", "MSFT", "NVDA", "AMZN", "GOOGL", "META", "AVGO", "ORCL", "CRM", "AMD",
    "CSCO", "IBM", "QCOM", "TXN", "INTU", "ADBE", "NOW", "AMAT", "MU", "LRCX",
    "KLAC", "ADI", "PANW", "SNPS", "CDNS", "ANET", "APH", "MSI", "FTNT", "NXPI",
    "MCHP", "ON", "MPWR", "DELL", "HPQ", "HPE", "STX", "WDC", "NTAP", "LOGI",
    "SMCI", "DDOG", "NET", "PLTR", "OKTA", "ZS", "CRWD", "TEAM", "WDAY", "SNOW",
    "SPLK", "GEN", "NLOK", "FFIV", "FSLR", "ENPH", "SEDG", "SWKS", "QRVO", "TER",
    "ENTG", "COHR", "LITE", "IPG", "AKAM", "JNPR", "CIEN", "ANSS", "PTC", "ALTR",
    "VRSN", "GRMN", "LOGM", "DBX", "BOX", "JNPR", "UI", "U", "UNITY", "PATH",
    
    # --- Financials (Banks, Insurance, Asset Management) ---
    "JPM", "BAC", "WFC", "GS", "MS", "C", "BLK", "SCHW", "AXP", "USB",
    "PNC", "TFC", "COF", "BK", "ICE", "CME", "SPGI", "MCO", "AON", "MMC",
    "AJG", "WTW", "BRO", "CB", "PGR", "TRV", "ALL", "HIG", "MET", "PRU",
    "AFL", "LNC", "PFG", "BEN", "TROW", "AMP", "IVZ", "STT", "NTRS", "FITB",
    "HBAN", "KEY", "RF", "CFG", "MTB", "SBNY", "SIVB", "FRC", "CMA", "ZION",
    "FCNCA", "NYCB", "EWBC", "WAL", "PACW", "BOKF", "ASB", "CFR", "UMBF", "FNB",
    "SYF", "DFS", "SOFI", "HOOD", "COIN", "MKTX", "SEIC", "LPLA", "RJF", "SF",
    
    # --- Healthcare (Pharma, Biotech, Devices, Providers) ---
    "LLY", "JNJ", "ABBV", "MRK", "PFE", "AMGN", "GILD", "ISRG", "ABT", "TMO",
    "DHR", "MDT", "SYK", "VRTX", "REGN", "CI", "ELV", "HUM", "CNC", "UNH",
    "CVS", "COR", "MCK", "CAH", "BSX", "EW", "ZBH", "DXCM", "PODD", "ALGN",
    "STE", "TFX", "BAX", "BDX", "A", "PKI", "MTD", "WAT", "WST", "IQV",
    "CRL", "MEDP", "VEEV", "RMD", "RES", "MOH", "UHS", "HCA", "THC", "DGX",
    "LH", "OPCH", "AMN", "MRNA", "BNTX", "SGEN", "BIIB", "ALNY", "BGNE", "INC_TEST",
    "TECH", "INC_DEMO", "SRPT", "EXAS", "NBIX", "UTHR", "HALO", "PACB", "ILMN", "ONT",
    
    # --- Energy (Oil, Gas, Equipment, Services) ---
    "XOM", "CVX", "COP", "SLB", "EOG", "OXY", "PSX", "MPC", "VLO", "FANG",
    "HAL", "BKR", "DVN", "PXD", "MRO", "APA", "HES", "TRGP", "OKE", "WMB",
    "KMI", "LNG", "CTRA", "EQT", "RRC", "SWN", "CNX", "MTDR", "PDCE", "CHRD",
    "MUR", "OVV", "CIVI", "VNOM", "DTM", "CDEV", "AR", "GPOR", "NFE", "AMPY",
    
    # --- Consumer Discretionary & Retail ---
    "WMT", "COST", "HD", "LOW", "TGT", "TJX", "NKE", "MCD", "SBUX", "CMG",
    "KO", "PEP", "PG", "CL", "MDLZ", "DG", "DLTR", "WBA", "KR", "SYY",
    "YUM", "DPZ", "WEN", "QSR", "DRI", "TXRH", "EAT", "BLMN", "CAKE", "BJ",
    "SFM", "GO", "FIVE", "ULTA", "ORLY", "AZO", "AAP", "GPC", "LKQ", "TSLA",
    "F", "GM", "HMC", "TM", "LCID", "RIVN", "Fisker", "NIO", "LI", "XPEV",
    "PHM", "LEN", "DHI", "TOL", "KBH", "MDC", "MTH", "GRBK", "TMHC", "CCS",
    
    # --- Industrials (Aerospace, Defense, Machinery, Transport) ---
    "CAT", "DE", "GE", "HON", "ETN", "UNP", "UPS", "FDX", "BA", "LMT",
    "RTX", "GD", "NOC", "TDG", "HWM", "HEI", "TXT", "BWXT", "LHX", "LDOS",
    "EMR", "ROK", "AME", "KEYS", "FTV", "IR", "DOV", "PH", "XYL", "FELE",
    "GWW", "FAST", "MSM", "URI", "HEES", "HRI", "OC", "CX", "VMC", "MLI",
    "NSC", "CSX", "UNP", "KSU", "CP", "CNI", "ODFL", "SAIA", "XPO", "ARCB",
    "CHRW", "EXPD", "JBHT", "LSTR", "KNX", "TFII", "UHAL", "MATX", "AL", "AER",
    
    # --- Materials & Chemicals ---
    "LIN", "APD", "SHW", "ECL", "FCX", "NEM", "CTVA", "DOW", "DD", "PPG",
    "ALB", "FMC", "NUE", "STLD", "X", "CLF", "FCX", "AEM", "GOLD", "WPM",
    "CF", "MOS", "IPI", "UAN", "EMN", "CE", "HUN", "OLN", "AVNT", "KWR",
    "VALE", "RIO", "BHP", "AA", "CENX", "KGC", "AU", "HMY", "DRD", "SBGL",
    
    # --- Consumer Staples & Products ---
    "PG", "KO", "PEP", "PM", "MO", "EL", "KMB", "CHD", "CLX", "COTY",
    "STZ", "BF-B", "TAP", "SAM", "BUD", "DEO", "HEINY", "CAG", "K", "GIS",
    "HNZ", "CPB", "HRL", "SJM", "POST", "LW", "MKC", "HSY", "TR", "HAIN",
    
    # --- Utilities & Real Estate ---
    "NEE", "SO", "DUK", "D", "AEP", "EXC", "SRE", "XEL", "WEC", "AWK",
    "PLD", "AMT", "CCI", "EQIX", "WY", "PSA", "O", "VICI", "WELL", "AVB",
    "EQR", "MAA", "UDR", "ESS", "CPT", "SUI", "ELS", "RER", "FRT", "REG",
    "KIM", "SPG", "MAC", "PECO", "EXR", "LSI", "CUBE", "COLD", "DRE", "STAG",
    
    # --- Communications & Media ---
    "DIS", "NFLX", "CMCSA", "T", "VZ", "TMUS", "CHTR", "FOXA", "EA", "TTWO",
    "LYV", "WBD", "PARA", "NWSA", "NYT", "TGNA", "NXST", "SIRI", "SPOT", "WMG",
    "LBRDK", "FWONA", "BATRA", "ZFOX", "ROKU", "IQ", "HUYA", "BILIBILI", "WB", "SINA",
    
    # --- Mid-Cap / Russell Growth & Value Picks ---
    "COPT", "HIW", "KRC", "OFC", "PGRE", "BDN", "CXP", "CLI", "HPP", "JBGS",
    "AMH", "SFR", "INVH", "TCO", "WPG", "PEI", "CBL", "SRG", "UNIT", "SBRA",
    "LTC", "NHI", "CHCT", "CTRE", "GMRE", "MTA", "GLPI", "MGP", "EPRT", "NETST",
    "FIX", "MYRG", "PWR", "TTEK", "ACM", "AECOM", "KBR", "FLR", "J", "EMR",
    "ROK", "FTV", "AME", "KEYS", "DOV", "PH", "XYL", "FELE", "GWW", "FAST",
    "MSM", "URI", "HEES", "HRI", "OC", "CX", "VMC", "MLI", "EXP", "SUM",
    "USCR", "CRH", "JELD", "PGT", "MAS", "FBHS", "AOS", "PNR", "MWA", "WTS",
    "TNC", "BMI", "XLY", "XLK", "XLF", "XLV", "XLI", "XLE", "XLB", "XLU",
    "XLP", "IYZ", "VNQ", "ITA", "XHB", "XRT", "SMH", "IBB", "KRE", "KBE"
]

# Ensure unique elements while preserving order representation
FALLBACK_TICKERS = list(dict.fromkeys(EXPANDED_TICKERS))
print(f"Created updated FALLBACK_TICKERS with {len(FALLBACK_TICKERS)} unique tickers.")


@st.cache_data(ttl=3600, show_spinner=False)
def get_universe():
    try:
        tables = pd.read_html("https://en.wikipedia.org/wiki/List_of_S%26P_500_companies")
        df = tables[0]
        ticker_col = "Symbol" if "Symbol" in df.columns else df.columns[0]
        name_col = "Security" if "Security" in df.columns else df.columns[1]
        sector_col = "GICS Sector" if "GICS Sector" in df.columns else None
        out = pd.DataFrame({"Ticker": df[ticker_col].astype(str).str.replace(".", "-", regex=False),
                            "Company": df[name_col].astype(str),
                            "Sector": df[sector_col].astype(str) if sector_col else "Unknown"})
        return out.drop_duplicates("Ticker")
    except Exception:
        return pd.DataFrame({"Ticker": FALLBACK_TICKERS, "Company": FALLBACK_TICKERS, "Sector": "Unknown"})

@st.cache_data(ttl=3600, show_spinner=False)
def fetch_company(ticker):
    try:
        t = yf.Ticker(ticker)
        info = t.get_info()
        # Use the most recent reported fundamentals exposed by Yahoo Finance.
        return {
            "Ticker": ticker,
            "Company": info.get("longName") or info.get("shortName") or ticker,
            "Sector": info.get("sector") or "Unknown",
            "Price": info.get("currentPrice") or info.get("regularMarketPrice"),
            "Market Cap ($B)": (info.get("marketCap") / 1e9) if info.get("marketCap") else np.nan,
            "P/E": info.get("trailingPE"),
            "Forward P/E": info.get("forwardPE"),
            "ROA (%)": (info.get("returnOnAssets") * 100) if info.get("returnOnAssets") is not None else np.nan,
            "ROE (%)": (info.get("returnOnEquity") * 100) if info.get("returnOnEquity") is not None else np.nan,
            "Operating Margin (%)": (info.get("operatingMargins") * 100) if info.get("operatingMargins") is not None else np.nan,
            "Debt/Equity": info.get("debtToEquity"),
            "Free Cash Flow ($B)": (info.get("freeCashflow") / 1e9) if info.get("freeCashflow") is not None else np.nan,
            "Altman Z": info.get("altmanZScore"),
            "Revenue Growth (%)": (info.get("revenueGrowth") * 100) if info.get("revenueGrowth") is not None else np.nan,
            "Data Source": "Yahoo Finance via yfinance"
        }
    except Exception:
        return {"Ticker": ticker, "Company": ticker, "Sector": "Unknown", "Data Source": "Fetch failed"}

def clean_num(series):
    return pd.to_numeric(series, errors="coerce").replace([np.inf, -np.inf], np.nan)

with st.sidebar:
    st.header("Screening controls")
    data_mode = st.radio("Data source", ["Fetch live company data", "Upload your own CSV"])
    uploaded = st.file_uploader("CSV file (optional)", type=["csv"]) if data_mode == "Upload your own CSV" else None
    if data_mode == "Fetch live company data":
        universe = get_universe()
        max_n = min(500, len(universe))
        sample_size = st.slider("Companies to retrieve", min_value=25, max_value=max(25, max_n), value=max_n, step=25)
        use_sector = st.selectbox("Peer group for within-industry analysis", ["All sectors"] + sorted(universe["Sector"].dropna().unique().tolist()))
        tickers_text = st.text_area("Optional ticker overrides (comma-separated)", placeholder="AAPL, MSFT, NVDA")
    st.divider()
    st.subheader("Ranking weights")
    w_quality = st.slider("Profitability / quality", 0, 100, 35)
    w_value = st.slider("Valuation", 0, 100, 25)
    w_safety = st.slider("Balance-sheet safety", 0, 100, 25)
    w_growth = st.slider("Growth", 0, 100, 15)
    st.caption("Weights are normalized automatically to total 100%.")

if data_mode == "Upload your own CSV":
    if uploaded is None:
        st.markdown("### Start with your own company dataset")
        st.write("Upload a CSV with one row per company. Suggested columns: `Ticker`, `Company`, `Sector`, `P/E`, `ROA (%)`, `ROE (%)`, `Operating Margin (%)`, `Debt/Equity`, `Free Cash Flow ($B)`, `Altman Z`, and `Revenue Growth (%)`.")
        st.stop()
    try:
        df = pd.read_csv(uploaded)
    except Exception as e:
        st.error(f"Could not read CSV: {e}")
        st.stop()
    if "Ticker" not in df.columns:
        st.error("Your CSV needs a 'Ticker' column.")
        st.stop()
    if "Company" not in df.columns:
        df["Company"] = df["Ticker"]
    if "Sector" not in df.columns:
        df["Sector"] = "Unknown"
else:
    universe = get_universe()
    if tickers_text.strip():
        requested = [x.strip().upper().replace(".", "-") for x in tickers_text.split(",") if x.strip()]
        ticker_list = list(dict.fromkeys(requested))[:500]
    else:
        # Retrieve a broad universe first; use the sector control below for peer analysis.
        ticker_list = universe["Ticker"].head(sample_size).tolist()
    if not ticker_list:
        st.warning("No companies selected.")
        st.stop()
    with st.spinner(f"Retrieving financial metrics for {len(ticker_list)} companies. Some providers may throttle large requests..."):
        rows = [fetch_company(t) for t in ticker_list]
    df = pd.DataFrame(rows)
    # Prefer sector/company labels from the universe if Yahoo does not provide them.
    if "Sector" in df.columns and "universe" in locals():
        lookup = universe.set_index("Ticker")
        for i, row in df.iterrows():
            if row.get("Sector") in (None, "Unknown") and row["Ticker"] in lookup.index:
                df.at[i, "Sector"] = lookup.at[row["Ticker"], "Sector"]
            if row.get("Company") == row["Ticker"] and row["Ticker"] in lookup.index:
                df.at[i, "Company"] = lookup.at[row["Ticker"], "Company"]

numeric_cols = ["Price", "Market Cap ($B)", "P/E", "Forward P/E", "ROA (%)", "ROE (%)",
                "Operating Margin (%)", "Debt/Equity", "Free Cash Flow ($B)", "Altman Z", "Revenue Growth (%)"]
for c in numeric_cols:
    if c in df.columns:
        df[c] = clean_num(df[c])

# Controls dynamically filter data.
st.subheader("1. Define your screen")
available_sectors = sorted(df["Sector"].fillna("Unknown").astype(str).unique().tolist()) if "Sector" in df else ["Unknown"]
c1, c2, c3 = st.columns(3)
with c1:
    default_sectors = [use_sector] if data_mode == "Fetch live company data" and use_sector != "All sectors" and use_sector in available_sectors else available_sectors
    sectors = st.multiselect("Peer group / sectors to include", available_sectors, default=default_sectors)
with c2:
    min_cap = st.number_input("Minimum market cap ($B)", min_value=0.0, value=0.0, step=10.0)
with c3:
    max_pe = st.number_input("Maximum trailing P/E (0 = ignore)", min_value=0.0, value=60.0, step=5.0)

st.subheader("2. Financial thresholds")
a, b, c, d = st.columns(4)
with a:
    min_roa = st.slider("Minimum ROA (%)", -50.0, 50.0, -10.0, 1.0)
with b:
    min_margin = st.slider("Minimum operating margin (%)", -100.0, 100.0, -20.0, 1.0)
with c:
    max_de = st.slider("Maximum debt/equity (0 = ignore)", 0.0, 500.0, 250.0, 10.0)
with d:
    min_z = st.slider("Minimum Altman Z (0 = ignore)", 0.0, 10.0, 0.0, 0.5)

filtered = df.copy()
if "Sector" in filtered:
    filtered = filtered[filtered["Sector"].fillna("Unknown").astype(str).isin(sectors)]
if "Market Cap ($B)" in filtered:
    filtered = filtered[filtered["Market Cap ($B)"].isna() | (filtered["Market Cap ($B)"] >= min_cap)]
if max_pe > 0 and "P/E" in filtered:
    filtered = filtered[filtered["P/E"].isna() | ((filtered["P/E"] > 0) & (filtered["P/E"] <= max_pe))]
if "ROA (%)" in filtered:
    filtered = filtered[filtered["ROA (%)"].isna() | (filtered["ROA (%)"] >= min_roa)]
if "Operating Margin (%)" in filtered:
    filtered = filtered[filtered["Operating Margin (%)"].isna() | (filtered["Operating Margin (%)"] >= min_margin)]
if max_de > 0 and "Debt/Equity" in filtered:
    filtered = filtered[filtered["Debt/Equity"].isna() | (filtered["Debt/Equity"] <= max_de)]
if min_z > 0 and "Altman Z" in filtered:
    filtered = filtered[filtered["Altman Z"].isna() | (filtered["Altman Z"] >= min_z)]

# Build a percentile-based composite score so different units can be compared.
weights = {"Quality": w_quality, "Value": w_value, "Safety": w_safety, "Growth": w_growth}
weight_total = sum(weights.values())
if weight_total == 0:
    weights = {"Quality": 1, "Value": 1, "Safety": 1, "Growth": 1}
    weight_total = 4
weights = {k: v / weight_total for k, v in weights.items()}

def pct_score(s, higher_is_better=True):
    s = clean_num(s)
    rank = s.rank(pct=True)
    return rank if higher_is_better else 1 - rank

def safe_score(columns, directions):
    present = [(col, direction) for col, direction in zip(columns, directions) if col in filtered.columns]
    if not present:
        return pd.Series(0.5, index=filtered.index)
    scores = pd.concat([pct_score(filtered[col], direction).rename(col) for col, direction in present], axis=1)
    return scores.mean(axis=1, skipna=True).fillna(0.5)

filtered["Quality Score"] = safe_score(["ROA (%)", "ROE (%)", "Operating Margin (%)"], [True, True, True])
filtered["Value Score"] = safe_score(["P/E"], [False])
filtered["Safety Score"] = safe_score(["Debt/Equity", "Altman Z"], [False, True])
filtered["Growth Score"] = safe_score(["Revenue Growth (%)", "Free Cash Flow ($B)"], [True, True])
filtered["Composite Score"] = 100 * (
    filtered["Quality Score"] * weights["Quality"] +
    filtered["Value Score"] * weights["Value"] +
    filtered["Safety Score"] * weights["Safety"] +
    filtered["Growth Score"] * weights["Growth"]
)
filtered = filtered.sort_values("Composite Score", ascending=False, na_position="last").reset_index(drop=True)
filtered.insert(0, "Rank", np.arange(1, len(filtered) + 1))

st.subheader("3. Results")
m1, m2, m3, m4 = st.columns(4)
m1.metric("Companies retrieved", f"{len(df):,}")
m2.metric("Companies passing screen", f"{len(filtered):,}")
m3.metric("Median composite score", f"{filtered['Composite Score'].median():.1f}" if len(filtered) else "—")
m4.metric("Sectors represented", f"{filtered['Sector'].nunique() if len(filtered) and 'Sector' in filtered else 0}")

if filtered.empty:
    st.warning("No companies passed the screen. Loosen one or more thresholds.")
    st.stop()

display_cols = ["Rank", "Ticker", "Company", "Sector", "Composite Score", "P/E", "ROA (%)",
                "ROE (%)", "Operating Margin (%)", "Debt/Equity", "Free Cash Flow ($B)", "Altman Z", "Revenue Growth (%)"]
display_cols = [x for x in display_cols if x in filtered.columns]
st.dataframe(filtered[display_cols], use_container_width=True, hide_index=True,
             column_config={"Composite Score": st.column_config.ProgressColumn("Composite Score", min_value=0, max_value=100, format="%.1f")})
st.download_button("⬇️ Download screened results (CSV)", filtered.to_csv(index=False).encode("utf-8"),
                   file_name="stockscreen_results.csv", mime="text/csv")

left, right = st.columns(2)
with left:
    st.markdown("#### Highest-ranked companies")
    top = filtered.head(15).sort_values("Composite Score")
    fig = px.bar(top, x="Composite Score", y="Ticker", orientation="h", color="Composite Score",
                 hover_data=[x for x in ["Company", "Sector", "P/E", "ROA (%)", "Altman Z"] if x in top.columns],
                 title="Top 15 by composite score")
    fig.update_layout(yaxis_title="", xaxis_title="Composite score (0–100)", coloraxis_showscale=False)
    st.plotly_chart(fig, use_container_width=True)
with right:
    st.markdown("#### Valuation vs profitability")
    if "P/E" in filtered and "ROA (%)" in filtered:
        plotdf = filtered.dropna(subset=["P/E", "ROA (%)"]).copy()
        plotdf = plotdf[(plotdf["P/E"] > 0) & (plotdf["P/E"] < 150)]
        if not plotdf.empty:
            fig2 = px.scatter(plotdf, x="P/E", y="ROA (%)", color="Sector", hover_name="Ticker",
                              hover_data=["Company", "Composite Score"], title="P/E vs ROA")
            st.plotly_chart(fig2, use_container_width=True)
        else:
            st.caption("Not enough complete P/E and ROA data to draw this chart.")
    else:
        st.caption("P/E and ROA columns are required for this chart.")

st.subheader("4. Company deep dive")
ticker_options = filtered["Ticker"].astype(str).tolist()
selected = st.selectbox("Choose a company", ticker_options)
company = filtered[filtered["Ticker"].astype(str) == selected].iloc[0]
st.markdown(f"### {company.get('Company', selected)} ({selected})")
x1, x2, x3, x4 = st.columns(4)
x1.metric("Composite score", f"{company['Composite Score']:.1f}/100")
x2.metric("P/E", f"{company['P/E']:.2f}" if pd.notna(company.get("P/E", np.nan)) else "N/A")
x3.metric("ROA", f"{company['ROA (%)']:.2f}%" if pd.notna(company.get("ROA (%)", np.nan)) else "N/A")
x4.metric("Free cash flow", f"${company['Free Cash Flow ($B)']:.2f}B" if pd.notna(company.get("Free Cash Flow ($B)", np.nan)) else "N/A")

st.markdown("#### How the ranking works")
st.write("The app retrieves a broad company universe (up to 500 S&P 500 constituents), then lets you select a sector as a peer group for within-industry comparison. Each available metric is converted to a percentile rank within the selected comparison sample. The app averages percentiles within each category, then applies your chosen category weights. Lower positive P/E and lower debt/equity are treated as better; higher profitability, growth, free cash flow, and Altman Z are treated as better. Missing metrics are excluded from that metric's category average rather than being treated as zero. Because scores are relative to the comparison sample, changing the peer group can change ranks.")
st.warning("Methodology limitation: a low P/E can reflect weak expected growth or elevated risk; debt/equity and Altman Z are not equally comparable across all industries. Consider peer-group comparisons and verify source data before drawing conclusions.")

with st.expander("Metric definitions and interpretation"):
    st.markdown("""
    - **P/E:** Share price divided by earnings per share. Lower values may indicate cheaper valuation, but can also reflect weaker expected growth or risk.
    - **ROA:** Net income relative to assets; a measure of how effectively assets generate profit.
    - **ROE:** Net income relative to shareholders' equity; can be distorted by high leverage or very low equity.
    - **Operating margin:** Operating income divided by revenue; indicates profitability from core operations.
    - **Debt/equity:** Total debt relative to shareholders' equity; interpretation varies significantly by sector.
    - **Free cash flow:** Cash generated after capital expenditures; this app displays the provider's reported value.
    - **Altman Z-score:** A financial-distress indicator whose formula and interpretation vary by company type. It may be unavailable or inappropriate for some firms.
    - **Revenue growth:** Year-over-year growth reported by the data provider.
    """)
