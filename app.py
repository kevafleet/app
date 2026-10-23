
import time
import numpy as np
import pandas as pd
import streamlit as st
import plotly.express as px
import yfinance as yf

st.set_page_config(
    page_title="StockScreen Analytics",
    page_icon="📊",
    layout="wide"
)

st.title("📊 StockScreen Analytics")
st.caption(
    "US equities | P/E | Book-to-Market | Scaled Net Operating Assets"
)

st.info(
    "Financial data is retrieved from Yahoo Finance and may be delayed, "
    "incomplete, or unavailable. This is an academic screening tool, "
    "not investment advice."
)


# ---------------------------------------------------------
# 1. BUILD THE UNIVERSE - GITHUB DATASET + LOCAL CSV FALLBACK
# ---------------------------------------------------------

from pathlib import Path

UNIVERSE_PATH = Path(__file__).parent / "universe.csv"

UNIVERSE_URL = (
    "https://raw.githubusercontent.com/"
    "zyhe16/top-us-stock-tickers/main/data/v2/tickers.csv"
)

FINANCIAL_SECTORS = {
    "financials",
    "financial services",
    "financial",
    "finance",
}

@st.cache_data(ttl=86400, show_spinner=False)
def load_stock_universe():
    errors = []
    source = None

    # Try the published dataset first.
    try:
        raw = pd.read_csv(
            UNIVERSE_URL,
            keep_default_na=False,
            timeout=30,
        )

        required = {"symbol", "name", "sector", "country"}
        if not required.issubset(
            {str(c).lower() for c in raw.columns}
        ):
            raise ValueError("Remote dataset has unexpected columns.")

        raw.columns = [str(c).strip().lower() for c in raw.columns]

        if "is_us_domiciled" in raw.columns:
            us_mask = (
                raw["is_us_domiciled"]
                .astype(str)
                .str.lower()
                .isin(["true", "1", "yes"])
            )
            raw = raw.loc[us_mask].copy()
        else:
            raw = raw[
                raw["country"].astype(str).str.strip()
                == "United States"
            ].copy()

        universe = pd.DataFrame({
            "Ticker": raw["symbol"].astype(str).str.strip().str.upper(),
            "Company": raw["name"].astype(str).str.strip(),
            "Sector": raw["sector"].astype(str).str.strip(),
            "Index": "US-listed universe",
        })

        source = "published US stock dataset"

    except Exception as e:
        errors.append(f"Remote source: {str(e)[:180]}")

        # Fall back to a local CSV if network access fails.
        if not UNIVERSE_PATH.exists():
            raise RuntimeError(
                "Could not load the remote stock dataset and "
                "universe.csv was not found beside app.py. "
                + " | ".join(errors)
            )

        local = pd.read_csv(
            UNIVERSE_PATH,
            keep_default_na=False,
        )
        local.columns = [str(c).strip() for c in local.columns]

        lower_map = {c.lower(): c for c in local.columns}

        if "ticker" not in lower_map:
            raise ValueError(
                "Local universe.csv must contain a Ticker column."
            )

        ticker_col = lower_map["ticker"]
        company_col = lower_map.get("company")
        sector_col = lower_map.get("sector")

        universe = pd.DataFrame({
            "Ticker": local[ticker_col].astype(str).str.strip().str.upper(),
            "Company": (
                local[company_col].astype(str).str.strip()
                if company_col else local[ticker_col].astype(str).str.strip()
            ),
            "Sector": (
                local[sector_col].astype(str).str.strip()
                if sector_col else "Unknown"
            ),
            "Index": "Local CSV",
        })

        source = "local universe.csv"

    # Normalize symbols for Yahoo Finance.
    universe["Ticker"] = (
        universe["Ticker"]
        .str.replace("/", "-", regex=False)
        .str.replace(".", "-", regex=False)
    )

    universe = universe[
        universe["Ticker"].str.fullmatch(r"[A-Z0-9-]+", na=False)
    ].copy()

    universe = universe[
        ~universe["Sector"].str.lower().isin(FINANCIAL_SECTORS)
    ].copy()

    universe = universe.drop_duplicates(
        subset=["Ticker"]
    ).reset_index(drop=True)

    if universe.empty:
        raise RuntimeError("No eligible companies were found.")

    return universe, errors, source


with st.spinner("Loading US stock universe..."):
    try:
        universe, source_errors, universe_source = load_stock_universe()
    except Exception as e:
        st.error(f"Could not build the stock universe: {e}")
        st.stop()

st.success(
    f"Loaded {len(universe):,} unique eligible tickers "
    f"from {universe_source}."
)

if source_errors:
    with st.expander("Stock-universe source warnings"):
        for message in source_errors:
            st.write(f"- {message}")

if len(universe) < 500:
    st.warning(
        "Fewer than 500 eligible tickers were loaded. "
        "Check data-source availability and the universe file."
    )


# ---------------------------------------------------------
# 2. FINANCIAL DATA COLLECTION
# ---------------------------------------------------------

def get_value(series, names):
    """Return the first usable value from a financial statement row."""
    if series is None or series.empty:
        return np.nan

    for name in names:
        if name in series.index:
            value = pd.to_numeric(series[name], errors="coerce")
            if pd.notna(value):
                return float(value)

    return np.nan


def get_statement_value(balance_sheet, names):
    if balance_sheet is None or balance_sheet.empty:
        return np.nan

    # Use the most recent available balance sheet column
    latest = balance_sheet.iloc[:, 0]
    return get_value(latest, names)


def collect_company(ticker, company, sector, index_name):
    result = {
        "Ticker": ticker,
        "Company": company,
        "Sector": sector,
        "Index": index_name,
        "Price": np.nan,
        "Market Cap": np.nan,
        "P/E": np.nan,
        "Book Equity": np.nan,
        "Book-to-market ratio": np.nan,
        "Total Assets": np.nan,
        "Operating Assets": np.nan,
        "Operating Liabilities": np.nan,
        "Net Operating Assets": np.nan,
        "Scaled net operating assets": np.nan,
        "Data Status": "Incomplete"
    }

    try:
        stock = yf.Ticker(ticker)

        # Yahoo Finance quote information
        info = stock.info or {}

        price = info.get("currentPrice")
        if price is None:
            price = info.get("regularMarketPrice")

        market_cap = info.get("marketCap")
        pe = info.get("trailingPE")

        if pe is None:
            eps = info.get("trailingEps")
            if price is not None and eps not in (None, 0):
                pe = price / eps

        if pe is not None and not np.isfinite(float(pe)):
            pe = np.nan

        # Balance sheet
        try:
            balance_sheet = stock.balance_sheet
        except Exception:
            balance_sheet = pd.DataFrame()

        total_assets = get_statement_value(
            balance_sheet,
            ["Total Assets"]
        )

        total_liabilities = get_statement_value(
            balance_sheet,
            ["Total Liabilities Net Minority Interest",
             "Total Liabilities"]
        )

        cash = get_statement_value(
            balance_sheet,
            ["Cash Cash Equivalents And Short Term Investments",
             "Cash And Cash Equivalents",
             "Cash"]
        )

        short_term_investments = get_statement_value(
            balance_sheet,
            ["Other Short Term Investments",
             "Short Term Investments"]
        )

        total_debt = get_statement_value(
            balance_sheet,
            ["Total Debt"]
        )

        book_equity = get_statement_value(
            balance_sheet,
            ["Stockholders Equity",
             "Common Stock Equity",
             "Total Stockholder Equity"]
        )

        # If total debt is unavailable, do not assume it is zero.
        # SNOA remains missing unless the required components exist.
        operating_assets = np.nan
        operating_liabilities = np.nan
        noa = np.nan
        scaled_noa = np.nan

        if (
            pd.notna(total_assets)
            and pd.notna(cash)
            and pd.notna(short_term_investments)
        ):
            operating_assets = (
                total_assets - cash - short_term_investments
            )

        if pd.notna(total_liabilities) and pd.notna(total_debt):
            operating_liabilities = total_liabilities - total_debt

        if (
            pd.notna(operating_assets)
            and pd.notna(operating_liabilities)
        ):
            noa = operating_assets - operating_liabilities

        if pd.notna(noa) and pd.notna(total_assets) and total_assets != 0:
            scaled_noa = noa / total_assets

        # Book-to-market ratio
        if (
            pd.notna(book_equity)
            and market_cap not in (None, 0)
            and pd.notna(market_cap)
        ):
            book_to_market = book_equity / market_cap
        else:
            book_to_market = np.nan

        result.update({
            "Price": price,
            "Market Cap": market_cap,
            "P/E": pe,
            "Book Equity": book_equity,
            "Book-to-market ratio": book_to_market,
            "Total Assets": total_assets,
            "Operating Assets": operating_assets,
            "Operating Liabilities": operating_liabilities,
            "Net Operating Assets": noa,
            "Scaled net operating assets": scaled_noa
        })

        required = [
            result["P/E"],
            result["Book-to-market ratio"],
            result["Scaled net operating assets"]
        ]

        result["Data Status"] = (
            "Complete" if all(pd.notna(v) for v in required)
            else "Partial"
        )

    except Exception as e:
        result["Data Status"] = f"Error: {str(e)[:100]}"

    return result


# ---------------------------------------------------------
# 3. CONTROLS
# ---------------------------------------------------------

st.sidebar.header("Data Collection")

st.sidebar.caption(
    "The first data pull can take time. Collect smaller batches "
    "if Yahoo Finance limits requests."
)

batch_size = st.sidebar.selectbox(
    "Companies to collect per run",
    options=[25, 50, 100, 250, 500],
    index=2
)

max_companies = min(batch_size, len(universe))

sector_options = sorted(universe["Sector"].unique().tolist())

selected_sectors = st.sidebar.multiselect(
    "Sectors",
    sector_options,
    default=sector_options
)

if "collected_data" not in st.session_state:
    st.session_state.collected_data = {}

filtered_universe = universe[
    universe["Sector"].isin(selected_sectors)
].reset_index(drop=True)

already_collected = set(st.session_state.collected_data.keys())

remaining = filtered_universe[
    ~filtered_universe["Ticker"].isin(already_collected)
].reset_index(drop=True)

st.sidebar.metric("Universe size", f"{len(universe):,}")
st.sidebar.metric(
    "Collected",
    f"{len(already_collected):,}"
)
st.sidebar.metric(
    "Remaining in selected sectors",
    f"{len(remaining):,}"
)

if st.sidebar.button("Collect next batch", type="primary"):
    if remaining.empty:
        st.sidebar.info("No uncollected companies remain in this selection.")
    else:
        batch = remaining.head(max_companies)
        progress = st.progress(0)
        status = st.empty()

        for i, row in batch.iterrows():
            status.write(
                f"Collecting {i + 1} of {len(batch)}: {row['Ticker']}"
            )

            data = collect_company(
                row["Ticker"],
                row["Company"],
                row["Sector"],
                row["Index"]
            )

            st.session_state.collected_data[row["Ticker"]] = data
            progress.progress((i + 1) / len(batch))

            # Small pause to reduce request pressure
            time.sleep(0.15)

        status.success(
            f"Finished collecting {len(batch)} companies."
        )
        st.rerun()

if st.sidebar.button("Clear collected data"):
    st.session_state.collected_data = {}
    st.rerun()

# ---------------------------------------------------------
# 4. DISPLAY AND ANALYZE DATA
# ---------------------------------------------------------

st.subheader("1. Company Universe")
st.dataframe(
    universe,
    use_container_width=True,
    hide_index=True
)

if not st.session_state.collected_data:
    st.info(
        "Select sectors in the sidebar, then click "
        "'Collect next batch' to begin."
    )
    st.stop()

data = pd.DataFrame(
    list(st.session_state.collected_data.values())
)

# Ensure numeric metric columns are numeric
metric_cols = [
    "P/E",
    "Book-to-market ratio",
    "Scaled net operating assets",
    "Price",
    "Market Cap"
]

for col in metric_cols:
    data[col] = pd.to_numeric(data[col], errors="coerce")

st.subheader("2. Financial Metrics")

m1, m2, m3, m4 = st.columns(4)
m1.metric("Companies collected", f"{len(data):,}")
m2.metric("Complete metric sets", f"{(data['Data Status'] == 'Complete').sum():,}")
m3.metric("Median P/E", f"{data['P/E'].median():.2f}" if data["P/E"].notna().any() else "—")
m4.metric(
    "Median Book-to-Market",
    f"{data['Book-to-market ratio'].median():.3f}"
    if data["Book-to-market ratio"].notna().any()
    else "—"
)

st.caption(
    "SNOA calculation used here: "
    "[(Total assets − cash − short-term investments) − "
    "(total liabilities − total debt)] / total assets. "
    "Confirm this operational definition against your course materials."
)

st.dataframe(
    data.sort_values("Ticker"),
    use_container_width=True,
    hide_index=True
)

# ---------------------------------------------------------
# 5. WITHIN-SECTOR PERCENTILE RANKS
# ---------------------------------------------------------

st.subheader("3. Within-Sector Analysis")

ranked = data.copy()

# Higher book-to-market is ranked higher.
# Lower positive P/E is ranked higher; negative P/E is not scored.
ranked["P/E for ranking"] = ranked["P/E"].where(ranked["P/E"] > 0)

ranked["P/E Peer Percentile"] = ranked.groupby("Sector")[
    "P/E for ranking"
].rank(pct=True, ascending=False) * 100

ranked["B/M Peer Percentile"] = ranked.groupby("Sector")[
    "Book-to-market ratio"
].rank(pct=True, ascending=True) * 100

# Lower SNOA receives a higher percentile in this exploratory screen.
ranked["SNOA Peer Percentile"] = ranked.groupby("Sector")[
    "Scaled net operating assets"
].rank(pct=True, ascending=False) * 100

st.dataframe(
    ranked[
        [
            "Ticker", "Company", "Sector", "P/E",
            "Book-to-market ratio",
            "Scaled net operating assets",
            "P/E Peer Percentile",
            "B/M Peer Percentile",
            "SNOA Peer Percentile",
            "Data Status"
        ]
    ],
    use_container_width=True,
    hide_index=True
)

valid_scatter = ranked.dropna(
    subset=["Book-to-market ratio", "Scaled net operating assets"]
)

if not valid_scatter.empty:
    st.subheader("4. Visualization")

    fig = px.scatter(
        valid_scatter,
        x="Book-to-market ratio",
        y="Scaled net operating assets",
        color="Sector",
        hover_name="Ticker",
        hover_data=["Company", "P/E"],
        title="Book-to-Market vs. Scaled NOA"
    )

    st.plotly_chart(fig, use_container_width=True)

# ---------------------------------------------------------
# 6. EXPORT
# ---------------------------------------------------------

st.subheader("5. Export")

st.download_button(
    "Download collected financial data (CSV)",
    data=data.to_csv(index=False).encode("utf-8"),
    file_name="financial_metrics.csv",
    mime="text/csv"
)

st.download_button(
    "Download peer rankings (CSV)",
    data=ranked.to_csv(index=False).encode("utf-8"),
    file_name="sector_peer_rankings.csv",
    mime="text/csv"
)

with st.expander("Data quality notes"):
    st.write(
        "- Missing financial data is left blank, not replaced with zero.\n"
        "- Book-to-market uses book equity divided by market capitalization.\n"
        "- P/E may be unavailable for companies with negative or missing earnings.\n"
        "- SNOA is sensitive to how operating assets and liabilities are defined.\n"
        "- Sector labels are sourced from index constituent tables; "
        "Unknown sectors should be reviewed before analysis.\n"
        "- Yahoo Finance data fields and availability can change."
    )
