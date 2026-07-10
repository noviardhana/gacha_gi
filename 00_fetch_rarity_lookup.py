"""
00_fetch_rarity_lookup.py
===========================
Paimon.moe export (paimon-moe-local-data.json) HANYA berisi id item, waktu,
tipe (character/weapon), dan pity per pull -- TIDAK ada info rarity (bintang
3/4/5) atau nama resmi item. Untuk EDA (distribusi pity 5*, top character,
dst) kita butuh tabel referensi id -> {name, rarity}.

Script ini mengambil tabel referensi tsb langsung dari source code resmi
Paimon.moe di GitHub (repo yang sama dengan situs yang dipakai untuk generate
file export kamu):
    https://github.com/MadeBaruna/paimon-moe
    - src/data/characters.js   -> daftar semua karakter + rarity
    - src/data/weaponList.js   -> daftar semua senjata + rarity

Output:
    data/char_full.json    -> { item_id: {"name": ..., "rarity": ...}, ... }
    data/weapon_full.json  -> { item_id: {"name": ..., "rarity": ...}, ... }

Jalankan script ini SEKALI sebelum 01_preprocessing.py (atau ulang kalau mau
refresh data terbaru dari repo). Butuh akses internet ke raw.githubusercontent.com.
"""

import json
import re
import urllib.request
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent
DATA_DIR = BASE_DIR / "data"

REPO_RAW_BASE = "https://raw.githubusercontent.com/MadeBaruna/paimon-moe/main"
SOURCES = {
    "char_full.json": f"{REPO_RAW_BASE}/src/data/characters.js",
    "weapon_full.json": f"{REPO_RAW_BASE}/src/data/weaponList.js",
}

# Regex utama: cari setiap "id: '...'", lalu cari name & rarity di sekitarnya.
# Dipakai window (bukan parse blok penuh) karena source-nya JS literal object,
# bukan JSON valid, dan urutan field name/id/rarity tidak konsisten antar file.
ID_RE = re.compile(r"id:\s*'([^']+)'")
NAME_RE = re.compile(r"name:\s*(?:'([^']*)'|\"([^\"]*)\")")
RARITY_RE = re.compile(r"rarity:\s*'?(\d+)'?")
WINDOW = 300  # karakter di kiri/kanan posisi "id:" untuk dicari name/rarity-nya


def fetch_text(url: str) -> str:
    with urllib.request.urlopen(url, timeout=30) as resp:
        return resp.read().decode("utf-8")


def parse_lookup(js_text: str) -> dict:
    result = {}
    for m in ID_RE.finditer(js_text):
        item_id = m.group(1)
        start = max(0, m.start() - WINDOW)
        end = min(len(js_text), m.end() + WINDOW)
        window = js_text[start:end]

        name_m = NAME_RE.search(window)
        name = None
        if name_m:
            name = name_m.group(1) if name_m.group(1) is not None else name_m.group(2)

        rarity_m = RARITY_RE.search(window)
        rarity = int(rarity_m.group(1)) if rarity_m else None

        result[item_id] = {"name": name, "rarity": rarity}
    return result


def main():
    DATA_DIR.mkdir(parents=True, exist_ok=True)

    for out_filename, url in SOURCES.items():
        print(f"Fetching {url} ...")
        js_text = fetch_text(url)
        lookup = parse_lookup(js_text)

        missing_name = [k for k, v in lookup.items() if v["name"] is None]
        missing_rarity = [k for k, v in lookup.items() if v["rarity"] is None]
        print(f"  -> {len(lookup)} item ditemukan "
              f"({len(missing_name)} tanpa nama, {len(missing_rarity)} tanpa rarity)")

        out_path = DATA_DIR / out_filename
        with open(out_path, "w", encoding="utf-8") as f:
            json.dump(lookup, f, ensure_ascii=False, indent=2)
        print(f"  -> disimpan ke {out_path}")

    print("\nSelesai. Lanjut jalankan 01_preprocessing.py")


if __name__ == "__main__":
    main()