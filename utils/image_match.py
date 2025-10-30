from PIL import Image
import imagehash, os
from typing import List, Tuple

def load_catalog_hashes(catalog_dir: str):
    entries = []
    if not os.path.isdir(catalog_dir):
        return entries
    for fn in os.listdir(catalog_dir):
        if fn.lower().endswith((".jpg",".jpeg",".png",".webp",".bmp")):
            path = os.path.join(catalog_dir, fn)
            try:
                img = Image.open(path).convert("RGB")
                ph = imagehash.phash(img)
                entries.append({"file": fn, "hash": ph})
            except Exception:
                continue
    return entries

def phash_distance(h1, h2) -> int:
    return h1 - h2

def best_match(upload_img: Image.Image, catalog_hashes, hash_func=imagehash.phash):
    if not catalog_hashes:
        return None, None, None
    ph = hash_func(upload_img.convert("RGB"))
    best = None
    best_dist = 1e9
    for entry in catalog_hashes:
        d = phash_distance(ph, entry["hash"])
        if d < best_dist:
            best_dist = d
            best = entry
    # Normalize similarity from distance (0..64) into percent
    # For 64-bit pHash, max Hamming distance is 64
    similarity = max(0.0, 100.0 * (1.0 - best_dist/64.0))
    return best, best_dist, similarity
