# utils/product_db.py
import os
import pandas as pd
from rapidfuzz import process, fuzz

DB_PATH = os.path.join("data", "product_db.csv")

COLUMNS = [
    "product_id",        # unique short id, e.g., APP-AP2
    "brand",             # Apple, Nike, Samsung
    "product_name",      # Apple AirPods Pro 2
    "model",             # MQD83HN/A
    "category",          # Electronics, Shoes, Smartphone
    "sku",               # optional internal SKU
    "gtin",              # UPC/EAN/GTIN
    "msrp",              # float
    "serial_prefix",     # APP / NKZ / SMG
    "image",             # URL or relative path (e.g., data/catalog/APP-AP2_1.jpg)
    "notes",             # free text
]

STARTER = [
    {"product_id":"APP-AP2","brand":"Apple","product_name":"AirPods Pro 2","model":"MTJV3",
     "category":"Electronics","sku":"AP2-2023","gtin":"0194253416123","msrp":249.00,"serial_prefix":"APP",
     "image":"","notes":"Gen 2"},
    {"product_id":"NKZ-P39","brand":"Nike","product_name":"Air Zoom Pegasus 39","model":"DM0173-001",
     "category":"Shoes","sku":"NZ-P39","gtin":"196149738001","msrp":130.00,"serial_prefix":"NKZ",
     "image":"","notes":"Men"},
    {"product_id":"SMG-S23","brand":"Samsung","product_name":"Galaxy S23","model":"SM-S911B/DS",
     "category":"Smartphone","sku":"S23-128","gtin":"8806094823487","msrp":799.00,"serial_prefix":"SMG",
     "image":"","notes":"128GB"},
    {"product_id":"SON-WF1000XM5","brand":"Sony","product_name":"WF-1000XM5","model":"YY2953",
     "category":"Electronics","sku":"XM5-BLK","gtin":"4548736148886","msrp":299.99,"serial_prefix":"SNY",
     "image":"","notes":""},
    {"product_id":"ADID-ULTRA4","brand":"Adidas","product_name":"Ultraboost 4.0 DNA","model":"FY9121",
     "category":"Shoes","sku":"UB4-DNA","gtin":"4062063112230","msrp":180.00,"serial_prefix":"ADD",
     "image":"","notes":""},
    {"product_id":"LV-NANO","brand":"Louis Vuitton","product_name":"Nano Speedy","model":"M81085",
     "category":"Bags","sku":"LV-NANO","gtin":"","msrp":1800.00,"serial_prefix":"LVS",
     "image":"","notes":"Luxury example"},
]

def _ensure_db():
    os.makedirs("data", exist_ok=True)
    if not os.path.exists(DB_PATH):
        df = pd.DataFrame(STARTER)
        for c in COLUMNS:
            if c not in df.columns: df[c] = ""
        df[COLUMNS].to_csv(DB_PATH, index=False)

def load_db() -> pd.DataFrame:
    _ensure_db()
    df = pd.read_csv(DB_PATH, dtype=str)
    # fix dtypes
    if "msrp" in df.columns:
        df["msrp"] = pd.to_numeric(df["msrp"], errors="coerce")
    for c in COLUMNS:
        if c not in df.columns:
            df[c] = "" if c != "msrp" else 0.0
    return df[COLUMNS]

def save_db(df: pd.DataFrame):
    df = df.copy()
    for c in COLUMNS:
        if c not in df.columns:
            df[c] = "" if c != "msrp" else 0.0
    df[COLUMNS].to_csv(DB_PATH, index=False)

def search_products(
    query: str = "",
    brands: list[str] | None = None,
    categories: list[str] | None = None,
    max_results: int = 200,
) -> pd.DataFrame:
    """
    Fuzzy + filtered search across name, brand, model, product_id, and category.
    """
    df = load_db()
    work = df.copy()

    # Quick filters first
    if brands:
        work = work[work["brand"].isin(brands)]
    if categories:
        work = work[work["category"].isin(categories)]

    if not query:
        return work.head(max_results)

    # Build a search corpus (concat fields)
    work["_search"] = (
        work["brand"].fillna("") + " " +
        work["product_name"].fillna("") + " " +
        work["model"].fillna("") + " " +
        work["product_id"].fillna("") + " " +
        work["category"].fillna("")
    )

    # RapidFuzz: return best matches by score
    choices = work["_search"].tolist()
    results = process.extract(
        query,
        choices,
        scorer=fuzz.WRatio,
        limit=min(max_results, len(choices)),
    )

    # Map back to rows
    idxs = [r[2] for r in results]  # (match, score, index)
    scores = [r[1] for r in results]
    matched = work.iloc[idxs].copy()
    matched.insert(0, "match_score", scores)
    return matched.drop(columns=["_search"], errors="ignore")

def distinct_brands() -> list[str]:
    return sorted([b for b in load_db()["brand"].dropna().unique().tolist() if b])

def distinct_categories() -> list[str]:
    return sorted([c for c in load_db()["category"].dropna().unique().tolist() if c])

def blank_row() -> dict:
    return {c: (0.0 if c == "msrp" else "") for c in COLUMNS}

def csv_template_path() -> str:
    path = os.path.join("data", "product_template.csv")
    pd.DataFrame([blank_row()]).to_csv(path, index=False)
    return path
