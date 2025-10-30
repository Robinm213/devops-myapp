import streamlit as st
from PIL import Image
import os, io, time
import pandas as pd
import plotly.express as px
from st_aggrid import AgGrid, GridOptionsBuilder, GridUpdateMode, DataReturnMode


# ---- existing utils from your repo ----
from utils.image_match import load_catalog_hashes, best_match
from utils.serial_check import validate_serial
from utils.anomaly import prepare_dataframe, fit_isolation_forest, supplier_risk_table
from utils.audit import log
from utils.report import generate_pdf

# ---- product database imports (new) ----
from utils.product_db import (
    load_db, save_db, search_products,
    distinct_brands, distinct_categories,
    csv_template_path, blank_row
)

# ---------- Quick Image Scan helper ----------
def image_auth_scan(img_pil, catalog_hashes, dist_threshold, sim_threshold):
    """
    Returns a dict with best match and a clear verdict using your thresholds.
    """
    result = {
        "best_file": None,
        "distance": None,
        "similarity": None,
        "verdict": "No catalog images found",
        "score": 0,
        "explanation": ""
    }
    if not catalog_hashes:
        result["explanation"] = "Add trusted images to data/catalog for visual matching."
        return result

    best, dist, sim = best_match(img_pil, catalog_hashes)
    if best is None:
        result["verdict"] = "Scan failed"
        result["explanation"] = "Could not compute image similarity."
        return result

    # Weighted score (0–100): 70 from similarity, 30 from distance
    sim_component = max(0.0, min(1.0, (sim or 0) / 100.0)) * 70
    # Distance is 0 (best) to 64 (worst). Map to [0..1] where lower is better.
    dist_component = 0.0
    if dist is not None:
        dist_component = max(0.0, min(1.0, (64 - float(dist)) / 64.0)) * 30

    score = int(sim_component + dist_component)

    # Verdict by thresholds you control from the sidebar
    if (dist is not None and dist <= dist_threshold) and (sim is not None and sim >= sim_threshold):
        verdict = "Authentic ✅"
        explanation = f"Similarity {sim:.1f}% ≥ {sim_threshold} and Hamming {dist} ≤ {dist_threshold}."
    elif sim is not None and sim >= (sim_threshold - 8):
        verdict = "Needs Review ⚠️"
        explanation = f"Close match (Similarity {sim:.1f}%). Distance {dist} vs threshold {dist_threshold}."
    else:
        verdict = "Suspected Counterfeit ❌"
        explanation = f"Similarity {sim:.1f}% below threshold or image signature too different (Hamming {dist})."

    result.update({
        "best_file": best["file"],
        "distance": dist,
        "similarity": sim,
        "verdict": verdict,
        "score": score,
        "explanation": explanation
    })
    return result

# -------------------- Page & basic styling --------------------
st.set_page_config(page_title="Supply Chain Transparency | Counterfeit Detection", layout="wide")
st.markdown("""
<style>
  .block-container { padding-top: 0.6rem; }
  .kpi-card {
    background: linear-gradient(180deg, #1d2230 0%, #141824 100%);
    border: 1px solid #252a39; border-radius: 16px; padding: 14px 16px;
  }
  .kpi-title { font-size: 12px; color:#a8b0c3; margin-bottom:4px; }
  .kpi-value { font-size: 22px; font-weight:700; color:#fff; }
  .glass-card {
    background: rgba(255,255,255,0.05);
    border-radius: 16px;
    padding: 16px;
    box-shadow: 0 4px 10px rgba(0,0,0,0.35);
    border: 1px solid rgba(255,255,255,0.08);
  }
  footer {visibility: hidden;}
</style>
""", unsafe_allow_html=True)

# -------------------- Header --------------------
col_logo, col_title, col_right = st.columns([1,6,2], vertical_alignment="center")
with col_title:
    st.title("AI-Powered Supply Chain Transparency – Counterfeit Detection (Platform)")
    st.caption("Image similarity • Serial validation • Unsupervised anomaly detection • Supplier risk")
with col_right:
    preset = st.selectbox("Preset", ["Balanced", "Strict", "Lenient"], index=0)

CATALOG_DIR = os.path.join("data", "catalog")

# -------------------- Sidebar --------------------
with st.sidebar:
    st.header("Settings")
    st.write("**Catalog path:**", CATALOG_DIR)

    if preset == "Balanced":
        dist_default, sim_default, cont_default = 12, 80, 0.07
    elif preset == "Strict":
        dist_default, sim_default, cont_default = 8, 88, 0.05
    else:
        dist_default, sim_default, cont_default = 16, 70, 0.10

    dist_threshold = st.slider("Max Hamming distance (lower = stricter)", 0, 64, dist_default)
    sim_threshold  = st.slider("Min similarity % to consider authentic", 0, 100, sim_default)
    contamination  = st.slider("Anomaly rate (IsolationForest) %", 1, 20, int(cont_default*100)) / 100.0

    st.markdown("---")
    st.caption("Tip: Add 3–10 trusted product images into `data/catalog` before the demo.")
    st.caption(f"Session: {time.strftime('%Y-%m-%d %H:%M:%S')}")

# -------------------- Tabs --------------------
tab1, tab2, tab3, tab4, tab5 = st.tabs([
    "🔍 Product Check",
    "📄 Invoice Anomalies",
    "🏭 Supplier Risk",
    "🧾 Export & Audit",
    "📚 Product Catalog"
])

# ==================== TAB 1: PRODUCT CHECK ====================
with tab1:
    st.markdown("<h2 style='color:#7C4DFF;'>1️⃣ Product Authenticity Verification</h2>", unsafe_allow_html=True)

    st.markdown('<div class="glass-card">', unsafe_allow_html=True)
    col1, col2 = st.columns([1,1], gap="large")

    # ---------- LEFT: Search + Upload ----------
    with col1:
        st.markdown("#### 🔎 Search Product")

        bcol, ccol = st.columns([1,1])
        with bcol:
            sel_brands = st.multiselect("Brand", distinct_brands(), placeholder="All")
        with ccol:
            sel_cats = st.multiselect("Category", distinct_categories(), placeholder="All")

        with st.form(key="product_search_form", clear_on_submit=False):
            query = st.text_input(
                "Name / ID / Model / Category",
                key="product_query",
                placeholder="e.g., AirPods Pro 2 or SMG-S23",
            )
            submitted = st.form_submit_button("Search")

        q = st.session_state.get("product_query", "")
        if submitted or q is not None:
            matches = search_products((q or "").strip(), brands=sel_brands, categories=sel_cats)
        else:
            matches = search_products("", brands=sel_brands, categories=sel_cats)

        st.caption(f"{len(matches)} match(es)")
        view_cols = ["match_score","product_id","brand","product_name","model","category","sku","gtin","msrp","serial_prefix","notes"]
        view_cols = [c for c in view_cols if c in matches.columns]
        st.dataframe(matches[view_cols], use_container_width=True, hide_index=True)

        st.markdown("**Or upload a product image:**")
        uploaded = st.file_uploader("📸 Upload Image", type=["jpg","jpeg","png","webp"], key="product_image_upload")
        auto_scan = st.toggle("Auto-scan uploaded image", value=True, key="auto_scan_toggle")

    # ---------- RIGHT: Serial / QR ----------
    with col2:
        serial = st.text_input("🧾 Serial / QR Code", placeholder="e.g., APP-2025-123450")
        allowlist = st.text_area("Known-good serials (optional, one per line)")
        allow = {s.strip().upper() for s in allowlist.splitlines() if s.strip()}

        serial_valid = None
        serial_details = None
        if serial:
            res = validate_serial(serial)
            serial_details = res
            serial_valid = res["valid"]
            log("serial_checked", {"serial": res["normalized"], "valid": res["valid"]})
            (st.success if res["valid"] else st.error)("Serial validation: " + ("✅ Valid" if res["valid"] else "⚠️ Invalid"))
            with st.expander("Validation details"):
                st.json(res, expanded=False)
            if allow:
                st.info("Allow-list: " + ("✅ Found" if serial.strip().upper() in allow else "❌ Not found"))

    st.markdown('</div>', unsafe_allow_html=True)

    # ---------- IMAGE SCAN (single implementation) ----------
    catalog_hashes = load_catalog_hashes(CATALOG_DIR)

    image_sim = None
    distance = None
    best_file = None
    scan_score = 0
    scan_verdict = None

    if uploaded is not None and auto_scan:
        img = Image.open(uploaded).convert("RGB")

        # Run scan (assumes you added image_auth_scan helper)
        scan = image_auth_scan(img, catalog_hashes, dist_threshold, sim_threshold)

        best_file   = scan["best_file"]
        distance    = scan["distance"]
        image_sim   = scan["similarity"]
        scan_score  = scan["score"]
        scan_verdict= scan["verdict"]

        left, right = st.columns([1,1], gap="large")
        with left:
            st.image(img, caption="Uploaded Product Image", use_column_width=True)

        with right:
            st.markdown(
                f"""
                <div class="glass-card">
                    <h3 style="margin:0 0 8px 0;">Image Scan Result</h3>
                    <div style="font-size:22px;font-weight:700;">{scan['verdict']}</div>
                    <div style="margin:6px 0 12px 0;color:#a8b0c3;">Score: {scan['score']} / 100</div>
                    <div><b>Best catalog match:</b> {scan['best_file'] or '—'}</div>
                    <div><b>Similarity:</b> {f"{scan['similarity']:.1f}%" if scan['similarity'] is not None else "—"} | <b>Hamming:</b> {scan['distance'] if scan['distance'] is not None else "—"}</div>
                    <div style="margin-top:8px;color:#a8b0c3;">{scan['explanation']}</div>
                </div>
                """,
                unsafe_allow_html=True
            )
            st.progress(max(0, min(1, scan["score"]/100.0)))

            # Map best-file -> product details
            product_id_from_file = None
            if best_file:
                product_id_from_file = os.path.basename(best_file).split("_")[0]
            if product_id_from_file:
                try:
                    db = load_db()
                    row = db[db["product_id"] == product_id_from_file]
                    if len(row):
                        info = row.iloc[0]
                        st.markdown(
                            f"""
                            <div class="glass-card" style="margin-top:10px">
                              <div style="font-size:16px;font-weight:700;">Matched Product</div>
                              <div><b>ID:</b> {info['product_id']} | <b>Brand:</b> {info['brand']} | <b>Name:</b> {info['product_name']}</div>
                              <div><b>Model:</b> {info['model']} | <b>GTIN:</b> {info['gtin']} | <b>MSRP:</b> {info['msrp']}</div>
                              <div><b>Category:</b> {info['category']} | <b>Serial prefix:</b> {info['serial_prefix']}</div>
                            </div>
                            """,
                            unsafe_allow_html=True
                        )
                except Exception as e:
                    st.caption(f"(Could not map product details: {e})")

            # Log + session history
            log("image_auto_scanned", {
                "best_file": best_file,
                "distance": distance,
                "similarity": float(image_sim or 0),
                "score": int(scan_score),
                "verdict": scan_verdict
            })
            history = st.session_state.setdefault("scan_history", [])
            history.append({
                "file": uploaded.name,
                "best_match": best_file,
                "similarity": image_sim,
                "distance": distance,
                "score": scan_score,
                "verdict": scan_verdict,
                "time": time.strftime("%Y-%m-%d %H:%M:%S")
            })

    # ---------- Recent scans table ----------
    if "scan_history" in st.session_state and st.session_state["scan_history"]:
        st.markdown("#### Recent Image Scans (this session)")
        st.dataframe(pd.DataFrame(st.session_state["scan_history"]), use_container_width=True, hide_index=True)

    # ---------- Combined verdict (serial + image) ----------
    if (uploaded is not None and auto_scan) or (serial):
        combined = 0
        if serial_valid is True:
            combined += 50
        if image_sim is not None:
            combined += int(max(0.0, min(1.0, image_sim/100.0)) * 50)

        verdict = "Likely Authentic ✅" if combined >= 70 else ("Review Manually ⚠️" if combined >= 40 else "High Risk ❌")
        st.progress(max(0, min(1, combined/100.0)))
        st.markdown(f"**Combined authenticity score:** `{combined}` / 100  ·  **Verdict:** {verdict}")
        st.caption(f"Serial weight 50, Image weight 50  ·  Thresholds: dist ≤ {dist_threshold}, sim ≥ {sim_threshold}%")
    else:
        st.info("Tip: search a product, enter a serial, or upload an image to verify.")


# ==================== TAB 2: INVOICE ANOMALIES ====================
with tab2:
    st.subheader("2) Transaction / Invoice Anomaly Detection")
    st.write("CSV columns: `invoice_id,date,supplier,item,quantity,unit_price,lead_time_days,amount`.")

    sample_btn = st.toggle("Use bundled sample data", value=True)
    if sample_btn:
        df = pd.read_csv(os.path.join("sample_data","sample_transactions.csv"))
        log("sample_loaded", {"rows": len(df)})
    else:
        inv_file = st.file_uploader("Upload CSV", type=["csv"])
        df = pd.read_csv(inv_file) if inv_file is not None else None
        if inv_file is not None:
            log("file_uploaded", {"name": inv_file.name})

    if df is not None:
        df_clean = prepare_dataframe(df)
        df_scored, model = fit_isolation_forest(df_clean, contamination=contamination)

        # KPI cards
        anomalies = int(df_scored["is_anomaly"].sum())
        total = len(df_scored)
        rate = (anomalies / total * 100) if total else 0.0
        k1, k2, k3, k4 = st.columns(4)
        with k1: st.markdown(f"""<div class="kpi-card"><div class="kpi-title">Invoices</div><div class="kpi-value">{total}</div></div>""", unsafe_allow_html=True)
        with k2: st.markdown(f"""<div class="kpi-card"><div class="kpi-title">Anomalies</div><div class="kpi-value">{anomalies}</div></div>""", unsafe_allow_html=True)
        with k3: st.markdown(f"""<div class="kpi-card"><div class="kpi-title">Anomaly Rate</div><div class="kpi-value">{rate:.1f}%</div></div>""", unsafe_allow_html=True)
        with k4:
            high_amt = (df_scored["amount"] > df_scored["amount"].median()*1.8).sum()
            st.markdown(f"""<div class="kpi-card"><div class="kpi-title">Very High Amount</div><div class="kpi-value">{int(high_amt)}</div></div>""", unsafe_allow_html=True)

        # Order + explain reasons
        cols = ["invoice_id","date","supplier","item","quantity","unit_price","lead_time_days","amount","anomaly_score","is_anomaly","reason_top_features"]
        df_scored = df_scored[cols].sort_values(["is_anomaly","anomaly_score"], ascending=[False, False])

        # Interactive table with filters (AgGrid)
        gb = GridOptionsBuilder.from_dataframe(df_scored)
        gb.configure_pagination(paginationAutoPageSize=True)
        gb.configure_side_bar()
        gb.configure_default_column(filter=True, sortable=True, resizable=True)
        grid_options = gb.build()
        AgGrid(df_scored, gridOptions=grid_options, update_mode=GridUpdateMode.NO_UPDATE, theme="streamlit", height=360)

        # Plotly score chart
        fig = px.line(df_scored.reset_index(drop=True), y="anomaly_score", title="Anomaly Scores (higher = more anomalous)")
        st.plotly_chart(fig, use_container_width=True)

        # Downloads (CSV + Excel)
        st.download_button("⬇️ Scored invoices (CSV)", df_scored.to_csv(index=False).encode("utf-8"), file_name="scored_invoices.csv", mime="text/csv")
        bio = io.BytesIO()
        with pd.ExcelWriter(bio, engine="openpyxl") as w:
            df_scored.to_excel(w, index=False, sheet_name="Scored")
        st.download_button("⬇️ Scored invoices (Excel)", bio.getvalue(),
            file_name="scored_invoices.xlsx",
            mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
        )

        st.session_state["scored_df"] = df_scored
    else:
        st.info("Upload a CSV or use the sample to proceed.")

# ==================== TAB 3: SUPPLIER RISK ====================
with tab3:
    st.subheader("3) Supplier Risk Overview")

    if "scored_df" in st.session_state:
        scored = st.session_state["scored_df"]
    else:
        scored = pd.read_csv(os.path.join("sample_data","sample_transactions.csv"))
        scored = prepare_dataframe(scored)
        scored, _ = fit_isolation_forest(scored, contamination=0.07)

    agg = supplier_risk_table(scored)
    st.dataframe(agg, use_container_width=True, hide_index=True)

    fig2 = px.bar(agg, x="supplier", y="risk_score", title="Supplier Risk Score (0–100)")
    st.plotly_chart(fig2, use_container_width=True)

    st.download_button("⬇️ Supplier risk (CSV)", agg.to_csv(index=False).encode("utf-8"),
                       file_name="supplier_risk.csv", mime="text/csv")

# ==================== TAB 4: EXPORT & AUDIT ====================
with tab4:
    st.subheader("4) Export & Audit")
    st.write("All actions are logged to `data/audit_log.csv` for transparency.")

    log_path = os.path.join("data","audit_log.csv")
    if os.path.exists(log_path):
        df_log = pd.read_csv(log_path)
        st.dataframe(df_log.tail(200), use_container_width=True, hide_index=True)
    else:
        st.info("No audit entries yet. Run a few checks to populate the log.")

    if "scored_df" in st.session_state:
        scored = st.session_state["scored_df"]
        total = len(scored)
        anomalies = int(scored["is_anomaly"].sum())
        anomaly_rate = f"{(anomalies/total*100 if total else 0):.1f}%"
        agg = supplier_risk_table(scored)
        high_risk_suppliers = int((agg["risk_score"] >= 70).sum())

        summary = {
            "title": "Counterfeit & Anomaly Summary",
            "total_invoices": total,
            "anomalies": anomalies,
            "anomaly_rate": anomaly_rate,
            "high_risk_suppliers": high_risk_suppliers,
            "ts": time.strftime('%Y-%m-%d %H:%M:%S')
        }
        pdf_path = "counterfeit_report.pdf"
        if st.button("🧾 Generate PDF summary"):
            generate_pdf(summary, pdf_path)
            with open(pdf_path, "rb") as f:
                st.download_button("⬇️ Download PDF summary", f, file_name=pdf_path, mime="application/pdf")
    else:
        st.info("Run the anomaly detection first to enable PDF summary.")

# ==================== TAB 5: PRODUCT CATALOG (ADMIN) ====================
with tab5:
    st.subheader("5) Product Catalog (Admin)")

    df = load_db()

    # Editable grid (AgGrid)
    gb = GridOptionsBuilder.from_dataframe(df)
    gb.configure_default_column(editable=True, filter=True, sortable=True, resizable=True)
    gb.configure_pagination(paginationAutoPageSize=True)
    gb.configure_side_bar()
    grid_options = gb.build()

    grid_resp = AgGrid(
        df,
        gridOptions=grid_options,
        update_mode=GridUpdateMode.MODEL_CHANGED,
        data_return_mode=DataReturnMode.AS_INPUT,
        fit_columns_on_grid_load=True,
        theme="streamlit",
        height=420
    )
    edited_df = pd.DataFrame(grid_resp["data"])

    c1, c2, c3, c4 = st.columns([1,1,1,2])
    with c1:
        if st.button("➕ Add row"):
            edited_df = pd.concat([edited_df, pd.DataFrame([blank_row()])], ignore_index=True)
    with c2:
        if st.button("💾 Save"):
            save_db(edited_df)
            st.success("Saved product database.")
    with c3:
        tmpl = csv_template_path()
        with open(tmpl, "rb") as f:
            st.download_button("⬇️ CSV template", f, file_name="product_template.csv", mime="text/csv")

    st.markdown("##### Bulk import (CSV/Excel)")
    up = st.file_uploader("Upload CSV/Excel matching the template columns", type=["csv","xlsx"])
    if up is not None:
        try:
            if up.name.lower().endswith(".xlsx"):
                new_df = pd.read_excel(up)
            else:
                new_df = pd.read_csv(up)
            save_db(new_df)
            st.success(f"Imported {len(new_df)} rows.")
        except Exception as e:
            st.error(f"Failed to import: {e}")
