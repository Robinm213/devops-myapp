# AI‑Powered Supply Chain Transparency for Counterfeit Detection (Demo)

This is a **one‑day demo** you can show live. It has three parts:

1. **Product Authenticity Check**  
   - Upload a product photo. The app compares its perceptual hash to your **trusted catalog** images and estimates similarity.  
   - Enter or scan a serial/QR string. The app runs format + Luhn‑style checks and validates against an allow‑list.

2. **Transaction/Invoice Anomaly Detection**  
   - Upload a CSV (or use the sample). The app trains an **IsolationForest** and flags suspicious rows with scores.

3. **Simple Supplier Risk View**  
   - Aggregates anomalies by supplier to produce a quick **risk score** and a bar chart you can show.

> This demo avoids cloud dependencies so it runs completely offline.

---

## Quickstart

```bash
# 1) (optional) create a venv
python -m venv venv && source venv/bin/activate   # on Windows: venv\Scripts\activate

# 2) install requirements
pip install -r requirements.txt

# 3) add 3–10 **trusted** product images to data/catalog/
#    (real product photos from your brand). Filenames become product IDs.
#    If you don't have images yet, the app still runs with a low-confidence warning.

# 4) run the app
streamlit run app.py
```

Then open the local URL Streamlit shows (usually http://localhost:8501).

---

## Project Structure

```
ai_supplychain_counterfeit_demo/
├── app.py
├── requirements.txt
├── README.md
├── utils/
│   ├── image_match.py
│   ├── serial_check.py
│   └── anomaly.py
├── data/
│   └── catalog/        # put trusted product images here (jpg/png)
└── sample_data/
    └── sample_transactions.csv
```

---

## How the Demo Works (talk track)

- **Image match:** computes a perceptual hash (pHash) for the uploaded image and compares to your trusted catalog with Hamming distance. Displays best match & similarity %. Below a threshold → **possible counterfeit**.
- **Serial check:** validates with regex pattern + Luhn‑like checksum; optional allowlist matches.
- **Anomaly detection:** trains **IsolationForest** on numeric features (amount, unit price, quantity, lead time). Rows with high anomaly scores are highlighted.
- **Supplier risk:** counts anomalies per supplier and normalizes into a 0–100 score you can explain to stakeholders.

---

## Notes

- This is a **reference demo**, not production. For a real system:
  - Replace pHash with a fine‑tuned CNN/transformer or CLIP embedding search.
  - Back serial checks with a secure server & cryptographic signatures.
  - Use feature stores, lineage & audit trails, and a proper graph view.
- The thresholds are configurable in the UI.
```
