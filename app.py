
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



# 1. BUILD THE UNIVERSE
import io
import requests
import pandas as pd
import streamlit as st

UNIVERSE_URL = (
    "https://raw.githubusercontent.com/"
    "zyhe16/top-us-stock-tickers/main/data/v2/tickers.csv"
)

@st.cache_data(ttl=3600)
def build_universe():
    try:
        response = requests.get(
            UNIVERSE_URL,
            timeout=30,
            headers={"User-Agent": "Mozilla/5.0"}
        )
        response.raise_for_status()

        if not response.content.strip():
            raise ValueError("The downloaded CSV file is empty.")

        raw = pd.read_csv(
            io.BytesIO(response.content),
            keep_default_na=False
        )

        if raw.empty or "symbol" not in raw.columns:
            raise ValueError(
                f"Unexpected CSV format. Columns found: "
                f"{list(raw.columns)}"
            )

        # Convert the downloaded dataset into the app's format.
        universe = pd.DataFrame()
        universe["Ticker"] = raw["symbol"].astype(str).str.strip()
        universe["Company"] = (
            raw["name"].astype(str).str.strip()
            if "name" in raw.columns else universe["Ticker"]
        )
        universe["Sector"] = (
            raw["sector"].astype(str).str.strip()
            if "sector" in raw.columns else "Unknown"
        )

        # Keep US-listed companies; exclude financial services.
        if "country" in raw.columns:
            country = raw["country"].astype(str).str.strip().str.lower()
            universe = universe[
                country.isin(["united states", "usa", "us"])
            ].copy()

        excluded_sectors = {
            "finance",
            "financial",
            "financial services",
            "financials",
        }
        universe = universe[
            ~universe["Sector"].str.lower().isin(excluded_sectors)
        ].copy()

        # Remove blank and duplicate tickers.
        universe["Ticker"] = (
            universe["Ticker"].str.replace(".", "-", regex=False)
            .str.replace("/", "-", regex=False)
        )
        universe = universe[
            universe["Ticker"].ne("")
        ].drop_duplicates(subset="Ticker")

        if universe.empty:
            raise ValueError(
                "No eligible companies remained after filtering."
            )

        universe["Index"] = "US-listed"
        return universe.reset_index(drop=True)

    except Exception as exc:
        # Fall back to a local CSV if one exists.
        try:
            local = pd.read_csv(
                "universe.csv",
                keep_default_na=False
            )

            if "Ticker" not in local.columns:
                raise ValueError(
                    "universe.csv must contain a Ticker column."
                )

            if "Company" not in local.columns:
                local["Company"] = local["Ticker"]

            if "Sector" not in local.columns:
                local["Sector"] = "Unknown"

            local["Ticker"] = (
                local["Ticker"].astype(str).str.strip()
                .str.replace(".", "-", regex=False)
                .str.replace("/", "-", regex=False)
            )

            local = local[local["Ticker"].ne("")].copy()
            local = local[
                ~local["Sector"].astype(str).str.lower().isin(
                    {
                        "finance",
                        "financial",
                        "financial services",
                        "financials",
                    }
                )
            ]

            if local.empty:
                raise ValueError("The local universe.csv has no eligible rows.")

            if "Index" not in local.columns:
                local["Index"] = "Local CSV"

            st.warning(
                f"Online download failed ({exc}). "
                "Using the local universe.csv instead."
            )
            return local.drop_duplicates(
                subset="Ticker"
            ).reset_index(drop=True)

        except Exception as local_exc:
            raise RuntimeError(
                f"Could not download the online universe: {exc}. "
                f"Local CSV fallback also failed: {local_exc}"
            ) from local_exc


try:
    universe = build_universe()
    st.success(f"Loaded {len(universe):,} eligible companies.")
    st.dataframe(universe.head(10), use_container_width=True)

except Exception as exc:
    st.error(f"Could not build the stock universe: {exc}")
    st.stop()


# ---------------------------------------------------------
# 2. FINANCIAL DATA COLLECTION
# ---------------------------------------------------------


# 2. FINANCIAL DATA COLLECTION
# ---------------------------------------------------------

import numpy as np
import pandas as pd
import yfinance as yf
import streamlit as st


def get_value(series, names):
    """Find the first available numeric value in a statement row."""
    if series is None or getattr(series, "empty", True):
        return np.nan

    for name in names:
        if name in series.index:
            value = pd.to_numeric(series.loc[name], errors="coerce")

            if isinstance(value, pd.Series):
                value = value.dropna()
                if not value.empty:
                    return float(value.iloc[0])
            elif pd.notna(value):
                return float(value)

    return np.nan


def get_statement_value(statement, names):
    """Read the latest available annual statement column."""
    if statement is None or statement.empty:
        return np.nan

    latest = statement.iloc[:, 0]
    return get_value(latest, names)


def safe_number(value):
    """Convert values to finite numbers or NaN."""
    try:
        value = float(value)
        return value if np.isfinite(value) else np.nan
    except (TypeError, ValueError):
        return np.nan


def collect_company(ticker, company="", sector="Unknown",
                    index_name="US-listed"):
    result = {
        "Ticker": ticker,
        "Company": company or ticker,
        "Sector": sector or "Unknown",
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
        "Data Status": "Incomplete",
        "Data Error": ""
    }

    try:
        stock = yf.Ticker(ticker)

        # 1. Market quote data
        info = stock.get_info() or {}

        price = safe_number(
            info.get("currentPrice")
            or info.get("regularMarketPrice")
        )
        market_cap = safe_number(info.get("marketCap"))
        pe = safe_number(info.get("trailingPE"))

        if not pd.notna(pe):
            eps = safe_number(info.get("trailingEps"))
            if pd.notna(price) and pd.notna(eps) and eps != 0:
                pe = price / eps

        if not company:
            result["Company"] = (
                info.get("longName")
                or info.get("shortName")
                or ticker
            )

        if sector in ("", None, "Unknown"):
            result["Sector"] = info.get("sector") or sector

        # 2. Balance sheet data
        try:
            balance_sheet = stock.balance_sheet
        except Exception:
            balance_sheet = pd.DataFrame()

        total_assets = get_statement_value(
            balance_sheet, ["Total Assets"]
        )
        total_liabilities = get_statement_value(
            balance_sheet,
            [
                "Total Liabilities Net Minority Interest",
                "Total Liabilities"
            ]
        )
        cash = get_statement_value(
            balance_sheet,
            [
                "Cash Cash Equivalents And Short Term Investments",
                "Cash And Cash Equivalents",
                "Cash"
            ]
        )
        short_term_investments = get_statement_value(
            balance_sheet,
            [
                "Other Short Term Investments",
                "Short Term Investments"
            ]
        )
        total_debt = get_statement_value(
            balance_sheet,
            [
                "Total Debt",
                "Long Term Debt And Capital Lease Obligation"
            ]
        )
        book_equity = get_statement_value(
            balance_sheet,
            [
                "Stockholders Equity",
                "Common Stock Equity",
                "Total Stockholder Equity"
            ]
        )

        # 3. Operating assets and liabilities
        # Do not silently treat missing components as zero.
        operating_assets = np.nan
        operating_liabilities = np.nan
        noa = np.nan
        scaled_noa = np.nan

        if pd.notna(total_assets) and pd.notna(cash):
            # If short-term investments are unavailable, use cash only
            # and flag that the operating-assets estimate is incomplete.
            investments_for_calc = (
                short_term_investments
                if pd.notna(short_term_investments) else 0.0
            )
            operating_assets = (
                total_assets - cash - investments_for_calc
            )

        if pd.notna(total_liabilities) and pd.notna(total_debt):
            operating_liabilities = total_liabilities - total_debt

        if (
            pd.notna(operating_assets)
            and pd.notna(operating_liabilities)
        ):
            noa = operating_assets - operating_liabilities

        if pd.notna(noa) and pd.notna(total_assets) and total_assets > 0:
            scaled_noa = noa / total_assets

        # 4. Book-to-market = book equity / market capitalization
        book_to_market = np.nan
        if (
            pd.notna(book_equity)
            and pd.notna(market_cap)
            and market_cap > 0
        ):
            book_to_market = book_equity / market_cap

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

        # Identify which key metrics are available.
        key_metrics = [
            price, market_cap, pe, book_equity,
            book_to_market, total_assets, scaled_noa
        ]
        available = sum(pd.notna(v) for v in key_metrics)

        if available == len(key_metrics):
            result["Data Status"] = "Complete"
        elif available > 0:
            result["Data Status"] = "Partial"
        else:
            result["Data Status"] = "No financial data"

        if pd.isna(short_term_investments):
            result["Data Error"] = (
                "Short-term investments unavailable; "
                "operating assets may be overstated."
            )

    except Exception as e:
        result["Data Status"] = "Fetch error"
        result["Data Error"] = str(e)[:200]

    return result

result = collect_company(
    ticker,
    company,
    sector,
    index_name
)

st.session_state.collected_data.append(result)

    if "collected_data" not in st.session_state:
    st.session_state.collected_data = []

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
# 3. DISPLAY COLLECTED FINANCIAL DATA
st.header("Collected Financial Data")

if st.session_state.collected_data:
    financial_df = pd.DataFrame(
        st.session_state.collected_data
    )

    st.metric("Companies collected", len(financial_df))

    st.dataframe(
        financial_df,
        use_container_width=True,
        hide_index=True
    )

    csv_data = financial_df.to_csv(index=False).encode("utf-8")

    st.download_button(
        "Download Financial Data CSV",
        data=csv_data,
        file_name="financial_data.csv",
        mime="text/csv"
    )

    if "Data Status" in financial_df.columns:
        st.subheader("Data Collection Status")
        st.dataframe(
            financial_df["Data Status"].value_counts().rename_axis(
                "Status"
            ).reset_index(name="Companies"),
            use_container_width=True,
            hide_index=True
        )
else:
    st.info("Collect a batch of companies to display financial data.")
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


# SIDEBAR: ADJUSTABLE SCREENING RULES

st.sidebar.header("BUY Candidate Rules")

buy_max_pe = st.sidebar.slider(
    "Maximum BUY P/E",
    min_value=5.0,
    max_value=80.0,
    value=25.0,
    step=1.0
)

buy_min_bm = st.sidebar.slider(
    "Minimum BUY Book-to-Market",
    min_value=0.0,
    max_value=2.0,
    value=0.30,
    step=0.05
)

buy_max_snoa = st.sidebar.slider(
    "Maximum BUY SNOA",
    min_value=-0.5,
    max_value=1.5,
    value=0.50,
    step=0.05
)

st.sidebar.header("SELL Candidate Rules")

sell_min_snoa = st.sidebar.slider(
    "High-SNOA SELL Threshold",
    min_value=0.0,
    max_value=2.0,
    value=0.75,
    step=0.05
)

sell_min_pe = st.sidebar.slider(
    "High-P/E SELL Threshold",
    min_value=5.0,
    max_value=100.0,
    value=40.0,
    step=1.0
)

sell_max_bm = st.sidebar.slider(
    "Low Book-to-Market SELL Threshold",
    min_value=0.0,
    max_value=1.0,
    value=0.15,
    step=0.05
)

# SCREEN THE DATA
if "collected_data" in st.session_state and st.session_state.collected_data:
    df = pd.DataFrame(st.session_state.collected_data)

    # Ensure calculated metrics are numeric.
    for col in ["P/E", "Book-to-Market", "SNOA", "Net Income"]:
        if col in df.columns:
            df[col] = pd.to_numeric(df[col], errors="coerce")
        else:
            df[col] = np.nan

    valid = (
        df["P/E"].notna()
        & df["Book-to-Market"].notna()
        & df["SNOA"].notna()
    )

    # SELL rules focus on accounting quality and expensive valuation.
    df["SELL Candidate"] = (
        (df["SNOA"] >= sell_min_snoa)
        | (df["P/E"] >= sell_min_pe)
        | (df["Book-to-Market"] <= sell_max_bm)
    ) & valid

    # BUY rules focus on valuation and lower SNOA.
    df["BUY Candidate"] = (
        (df["P/E"] > 0)
        & (df["P/E"] <= buy_max_pe)
        & (df["Book-to-Market"] >= buy_min_bm)
        & (df["SNOA"] <= buy_max_snoa)
        & (df["Net Income"] > 0)
        & valid
        & ~df["SELL Candidate"]
    )

    df["Signal"] = "HOLD / REVIEW"
    df.loc[df["BUY Candidate"], "Signal"] = "BUY CANDIDATE"
    df.loc[df["SELL Candidate"], "Signal"] = "SELL CANDIDATE"

    st.header("Financial Screening Results")

    c1, c2, c3 = st.columns(3)
    c1.metric("Companies with data", int(valid.sum()))
    c2.metric("BUY candidates", int(df["BUY Candidate"].sum()))
    c3.metric("SELL candidates", int(df["SELL Candidate"].sum()))

    st.subheader("BUY Candidates")
    st.dataframe(
        df.loc[df["BUY Candidate"]].sort_values("P/E"),
        use_container_width=True
    )

    st.subheader("SELL Candidates")
    st.dataframe(
        df.loc[df["SELL Candidate"]].sort_values("SNOA", ascending=False),
        use_container_width=True
    )

    st.subheader("All Companies")
    st.dataframe(df, use_container_width=True)

    # Show why financial data might be missing.
    if "Data Status" in df.columns:
        with st.expander("Inspect missing financial data"):
            st.dataframe(
                df.loc[~valid, [
                    c for c in [
                        "Ticker", "Company", "Data Status",
                        "P/E", "Book-to-Market", "SNOA"
                    ] if c in df.columns],
                use_container_width==True]
            )

else:
    st.warning(
        "No financial records have been collected yet. "
        "Run the data collection step before screening."
    )
