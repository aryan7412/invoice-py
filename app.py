import re
import time
import pandas as pd
import streamlit as st

from engine import (
    prepare_dataset,
    train_tabpfn,
    score_current_invoices,
    evaluate_models,
    make_priority_table,
)

st.set_page_config(
    page_title="Collection Radar",
    page_icon="◈",
    layout="wide",
    initial_sidebar_state="expanded",
)

HIGH_RISK_THRESHOLD = 60
MEDIUM_RISK_THRESHOLD = 40
NONE = "— none —"


def classify_risk(x):
    if x >= HIGH_RISK_THRESHOLD:
        return "High"
    if x >= MEDIUM_RISK_THRESHOLD:
        return "Medium"
    return "Low"


def normalize(name):
    return re.sub(r"\s+", " ", re.sub(r"[_\-]+", " ", str(name).strip().lower()))


def guess_column(columns, names):
    norm = {normalize(c): c for c in columns}
    for name in names:
        if normalize(name) in norm:
            return norm[normalize(name)]
    for name in names:
        n = normalize(name)
        for k, original in norm.items():
            if n in k or k in n:
                return original
    return None


def option_index(options, value):
    return options.index(value) if value in options else 0


st.markdown("""
<style>
.block-container{max-width:1280px;padding-top:1.5rem;padding-bottom:3rem}
.eyebrow{font-size:.75rem;font-weight:800;letter-spacing:.14em;text-transform:uppercase;color:#9ca3af}
.hero-subtitle{color:#9ca3af;font-size:1.05rem;max-width:780px}
.radar-card,.metric-card{border:1px solid #30343d;border-radius:16px;padding:1rem 1.1rem;background:#181b23;color:#f9fafb}
.radar-card{min-height:105px}.radar-card-title{font-weight:700}.radar-card-text,.muted{color:#9ca3af;font-size:.88rem}
.metric-card{min-height:95px}.metric-label{color:#9ca3af;font-size:.78rem;font-weight:600}.metric-value{color:#f9fafb;font-size:1.5rem;font-weight:750;margin-top:.25rem}
div[data-testid="stMetric"]{background:#181b23;border:1px solid #30343d;border-radius:16px;padding:1rem}
div[data-testid="stMetricLabel"]{color:#9ca3af} div[data-testid="stMetricValue"]{color:#f9fafb}
section[data-testid="stSidebar"]{border-right:1px solid #30343d}
</style>
""", unsafe_allow_html=True)

for key, default in {
    "df": None,
    "results": None,
    "benchmark": None,
    "tour_seen": False,
}.items():
    if key not in st.session_state:
        st.session_state[key] = default

st.markdown('<div class="eyebrow">LOCAL • PRIVATE • TABULAR AI</div>', unsafe_allow_html=True)
st.title("Collection Radar")
st.markdown(
    '<div class="hero-subtitle">Turn your existing wholesale Excel sheet into one simple answer: '
    '<b>who should I follow up with first?</b></div>',
    unsafe_allow_html=True,
)
st.caption("Runs locally on your laptop. Your invoice data does not need to be sent to a cloud AI service.")

with st.expander("💡 New here? Take the 30-second Collection Radar tour", expanded=not st.session_state.tour_seen):
    a, b, c = st.columns(3)
    with a:
        st.markdown("### 1 · Spreadsheet")
        st.write("Upload the Excel/CSV your business already uses.")
    with b:
        st.markdown("### 2 · History")
        st.write("The model learns from invoices where payment outcomes are known.")
    with c:
        st.markdown("### 3 · Priority")
        st.write("Current invoices are scored and ranked by risk and potential exposure.")
    st.info("The goal is simple: instead of asking “Which invoice should I check?”, get “Who should I call first?”")
    if st.button("Got it", key="tour_done"):
        st.session_state.tour_seen = True
        st.rerun()

with st.sidebar:
    st.markdown("## Collection Radar")
    st.markdown("### 1 · Load your data")
    uploaded = st.file_uploader("Excel or CSV", type=["xlsx", "xls", "csv"])
    demo_button = st.button("Use demo wholesale data", width="stretch")

    if uploaded:
        try:
            st.session_state.df = pd.read_csv(uploaded) if uploaded.name.lower().endswith(".csv") else pd.read_excel(uploaded)
            st.session_state.results = None
            st.session_state.benchmark = None
            st.success(f"Loaded {len(st.session_state.df):,} rows")
        except Exception as e:
            st.error(f"Could not read the file: {e}")

    if demo_button:
        from demo_data import make_demo_data
        st.session_state.df = make_demo_data()
        st.session_state.results = None
        st.session_state.benchmark = None
        st.success("Loaded demo data")

df = st.session_state.df

if df is None:
    st.info("Upload your wholesale Excel/CSV, or use the demo data to see the complete workflow.")
    st.markdown("""
### What Collection Radar does

1. Reads your spreadsheet locally.
2. Learns from historical payment outcomes.
3. Uses **TabPFN** to estimate late-payment probability.
4. Ranks current invoices by **risk × amount**.
5. Shows a collection worklist.

**No LLM, no cloud database, no external AI API during local inference.**
""")
    st.stop()

if df.empty:
    st.error("The uploaded spreadsheet contains no rows.")
    st.stop()

columns = list(df.columns)

customer_guess = guess_column(columns, ["Customer","Customer Name","Party Name","Dealer","Client","Buyer"])
amount_guess = guess_column(columns, ["Invoice Amount","Amount","Bill Amount","Net Amount","Invoice Value","Total Amount"])
target_guess = guess_column(columns, ["Paid Late","Late Payment","Payment Late","Paid Late?","Late","Late Payment Outcome"])
invoice_guess = guess_column(columns, ["Invoice ID","Invoice Number","Invoice No","Invoice #","Bill No","Bill Number","Document ID"])
date_guess = guess_column(columns, ["Invoice Date","Bill Date","Document Date","Date"])

st.markdown("## 2 · Map your spreadsheet")
st.caption("Choose what each important column means. The spreadsheet stays local.")

with st.expander("What do these fields mean?"):
    x, y = st.columns(2)
    with x:
        st.markdown("**Customer** — who owes you money.\n\n**Invoice amount** — original invoice value.\n\n**Historical late-payment outcome** — past yes/no result the model learns from.")
    with y:
        st.markdown("**Invoice / document ID** — bill reference.\n\n**Invoice date** — optional issue date.\n\n**Risk %** — estimated probability of late payment, not a guarantee.")

c1, c2, c3 = st.columns(3)

with c1:
    opts = [NONE] + columns
    customer_col = st.selectbox("Customer", opts, option_index(opts, customer_guess), key="map_customer",
                                 help="Customer/dealer/party name.")
    amount_col = st.selectbox("Invoice amount", opts, option_index(opts, amount_guess), key="map_amount",
                              help="Original invoice or bill amount.")

with c2:
    target_col = st.selectbox("Historical late-payment outcome", opts, option_index(opts, target_guess), key="map_target",
                              help="Known historical yes/no late-payment outcome.")
    invoice_col = st.selectbox("Invoice / document ID", opts, option_index(opts, invoice_guess), key="map_invoice",
                               help="Invoice, bill or document number.")

with c3:
    date_col = st.selectbox("Invoice date", opts, option_index(opts, date_guess), key="map_date",
                            help="Optional invoice/bill date.")
    current_only = st.checkbox("Only rank rows with blank outcome", True, key="current_only",
                               help="Recommended: known outcomes train the model; blank outcomes are scored.")

if target_col == NONE:
    st.warning("Select the historical late-payment outcome column before running the model.")
    st.stop()

try:
    prepared = prepare_dataset(
        df,
        target_col,
        None if amount_col == NONE else amount_col,
        None if customer_col == NONE else customer_col,
        None if invoice_col == NONE else invoice_col,
        None if date_col == NONE else date_col,
        current_only,
    )
except Exception as e:
    st.error(f"Could not prepare the dataset: {e}")
    st.stop()

labeled = prepared["labeled"]
current = prepared["current"]
X_train = prepared["X_train"]
y_train = prepared["y_train"]
X_current = prepared["X_current"]

a,b,c,d = st.columns(4)
a.metric("Rows loaded", f"{len(df):,}")
b.metric("Historical examples", f"{len(labeled):,}")
c.metric("Invoices to rank", f"{len(current):,}")
d.metric("Data location", "Local")

st.caption(f"Using {len(labeled):,} historical labeled invoices and {len(current):,} current invoices.")

st.markdown("---")
st.markdown("## 3 · Run the local model")
run_col, bench_col = st.columns(2)

with run_col:
    st.markdown('<div class="radar-card"><div class="radar-card-title">TabPFN analysis</div><div class="radar-card-text">Train on historical invoices and rank current unresolved invoices.</div></div>', unsafe_allow_html=True)

    if st.button("Run TabPFN analysis", type="primary", width="stretch", key="run_tabpfn"):
        if len(labeled) < 30:
            st.error("You need more historical labeled rows. Aim for at least ~100 if available.")
        elif len(current) == 0:
            st.error("No current/unlabeled invoices were found to rank.")
        else:
            try:
                with st.spinner("Running TabPFN locally…"):
                    start = time.perf_counter()
                    model = train_tabpfn(X_train, y_train)
                    probs = score_current_invoices(model, X_current)
                    elapsed = time.perf_counter() - start

                results = make_priority_table(
                    current,
                    probs,
                    None if amount_col == NONE else amount_col,
                    None if customer_col == NONE else customer_col,
                    None if invoice_col == NONE else invoice_col,
                )
                results["Risk Level"] = results["Risk %"].apply(classify_risk)
                results["_risk_order"] = results["Risk Level"].map({"High":0,"Medium":1,"Low":2})
                results = results.sort_values(["_risk_order","Potential Exposure"], ascending=[True,False]).drop(columns="_risk_order").reset_index(drop=True)
                results.attrs["elapsed"] = elapsed
                st.session_state.results = results
                st.success(f"Analysis complete in {elapsed:.1f}s.")
            except Exception as e:
                st.error(f"TabPFN analysis failed: {e}")

with bench_col:
    st.markdown('<div class="radar-card"><div class="radar-card-title">Model benchmark</div><div class="radar-card-text">Compare TabPFN with XGBoost on the same historical data.</div></div>', unsafe_allow_html=True)

    if st.button("Benchmark TabPFN vs XGBoost", width="stretch", key="run_benchmark"):
        if len(labeled) < 80:
            st.warning("For a useful benchmark, try to have at least ~80 historical labeled rows.")
        else:
            try:
                progress = st.progress(0, text="Preparing benchmark…")
                progress.progress(10, text="Creating held-out test set…")
                with st.spinner("Running TabPFN vs XGBoost locally…"):
                    start = time.perf_counter()
                    bench = evaluate_models(X_train, y_train)
                    elapsed = time.perf_counter() - start
                progress.progress(100, text="Benchmark complete.")
                st.session_state.benchmark = bench
                st.success(f"Benchmark completed in {elapsed:.1f}s.")
            except MemoryError:
                st.error("The benchmark ran out of memory. Close other applications and try again.")
            except Exception as e:
                st.error(f"Benchmark could not be completed: {e}")
                st.info("The collection analysis is unaffected. The benchmark is only a comparison.")

if st.session_state.benchmark:
    st.markdown("---")
    st.markdown("### Model benchmark")
    st.caption("These are measured on your dataset. Do not use placeholder numbers in the pitch.")
    st.dataframe(pd.DataFrame(st.session_state.benchmark), width="stretch", hide_index=True)

results = st.session_state.results

if results is not None:
    st.markdown("---")
    st.markdown("## Today's collection priorities")
    st.caption("Start with invoices where late-payment risk and potential cash exposure are highest.")

    total = pd.to_numeric(results["Potential Exposure"], errors="coerce").fillna(0).sum()
    high = (results["Risk Level"] == "High").sum()
    medium = (results["Risk Level"] == "Medium").sum()
    low = (results["Risk Level"] == "Low").sum()

    m1,m2,m3,m4 = st.columns(4)
    m1.metric("Potential exposure", f"₹{total:,.0f}")
    m2.metric("🔴 High risk", f"{high:,}", help=f"Predicted late-payment probability ≥ {HIGH_RISK_THRESHOLD}%.")
    m3.metric("🟠 Medium risk", f"{medium:,}", help=f"Predicted probability {MEDIUM_RISK_THRESHOLD}%–{HIGH_RISK_THRESHOLD-0.1:.1f}%.")
    m4.metric("🟢 Low risk", f"{low:,}", help=f"Predicted probability < {MEDIUM_RISK_THRESHOLD}%.")

    st.markdown(f"**Risk bands:** 🔴 High ≥ {HIGH_RISK_THRESHOLD}% &nbsp;&nbsp; 🟠 Medium {MEDIUM_RISK_THRESHOLD}%–{HIGH_RISK_THRESHOLD-0.1:.1f}% &nbsp;&nbsp; 🟢 Low < {MEDIUM_RISK_THRESHOLD}%")
    st.markdown("### Collection worklist")

    preferred = ["Customer","Invoice","Invoice Amount","Risk %","Risk Level","Potential Exposure"]
    display_cols = [x for x in preferred if x in results.columns]
    shown = results[display_cols].copy()

    formats = {}
    if "Risk %" in shown: formats["Risk %"] = "{:.1f}%"
    if "Invoice Amount" in shown: formats["Invoice Amount"] = "₹{:,.0f}"
    if "Potential Exposure" in shown: formats["Potential Exposure"] = "₹{:,.0f}"

    st.dataframe(shown.style.format(formats), width="stretch", hide_index=True)

    if len(results):
        top = results.iloc[0]
        customer = top.get("Customer","Customer")
        invoice = top.get("Invoice","Invoice")
        risk = top.get("Risk %", None)
        exposure = top.get("Potential Exposure", None)

        st.markdown("### Suggested first follow-up")
        p1,p2,p3 = st.columns(3)
        with p1:
            st.markdown(f'<div class="metric-card"><div class="metric-label">CUSTOMER</div><div class="metric-value">{customer}</div></div>', unsafe_allow_html=True)
        with p2:
            st.markdown(f'<div class="metric-card"><div class="metric-label">INVOICE</div><div class="metric-value">{invoice}</div></div>', unsafe_allow_html=True)
        with p3:
            r = f"{risk:.1f}% risk" if pd.notna(risk) else "—"
            e = f"₹{exposure:,.0f}" if pd.notna(exposure) else "—"
            st.markdown(f'<div class="metric-card"><div class="metric-label">PRIORITY SIGNAL</div><div class="metric-value">{r}</div><div class="muted">Potential exposure: {e}</div></div>', unsafe_allow_html=True)

    st.markdown("### Export")
    st.download_button(
        "Export collection priority CSV",
        results.to_csv(index=False).encode("utf-8"),
        "collection_priority.csv",
        "text/csv",
        width="stretch",
    )
    st.caption("Risk is a model probability, not a guarantee. Validate predictions against real payment outcomes.")

st.markdown("---")
st.caption("Collection Radar • Local-first prototype • TabPFN-powered")
