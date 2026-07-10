"""
01_preprocessing.py
====================
Preprocessing pipeline: paimon-moe-local-data.json -> data_clean.csv

Mengubah raw export Paimon.moe (Genshin Impact wish/gacha history) menjadi
satu tabel "tidy" (satu baris = satu pull) yang siap dipakai untuk EDA &
dashboard (Total Pull, Timeline, Pity Distribution, Win/Lose 50-50,
Top Character/Weapon, Banner Performance, Luck Score, dst).

Input :
    data/paimon-moe-local-data.json   -> raw export
    data/char_full.json               -> lookup id -> {name, rarity} karakter
    data/weapon_full.json             -> lookup id -> {name, rarity} senjata
    (dua file lookup di atas dihasilkan oleh 00_fetch_rarity_lookup.py --
    jalankan script itu dulu sebelum script ini)

Output:
    data/data_clean.csv            -> default, semua uid digabung
    data/data_clean_<uid>.csv      -> kalau dijalankan dengan --uid <uid>

Cara pakai:
    python3 01_preprocessing.py                # semua akun -> data_clean.csv
    python3 01_preprocessing.py --list-uid      # lihat daftar uid yang tersedia
    python3 01_preprocessing.py --uid 887284572 # cuma akun itu -> data_clean_887284572.csv
"""

import argparse
import json
from pathlib import Path

import pandas as pd

BASE_DIR = Path(__file__).resolve().parent
DATA_DIR = BASE_DIR / "data"

RAW_PATH = DATA_DIR / "paimon-moe-local-data.json"
CHAR_LOOKUP_PATH = DATA_DIR / "char_full.json"
WEAPON_LOOKUP_PATH = DATA_DIR / "weapon_full.json"

# Banner key -> label yang lebih rapi
BANNER_LABELS = {
    "wish-counter-character-event": "Character Event",
    "wish-counter-standard": "Standard",
    "wish-counter-weapon-event": "Weapon Event",
    "wish-counter-beginners": "Beginners",
}

# Field 'rate' hanya ada di banner event (Character Event & Weapon Event) untuk
# pull rarity 4* dan 5*, merepresentasikan hasil sistem rate-up/50-50:
#   0 = kalah 50/50 (dapat item standard/non rate-up)
#   1 = menang 50/50 (dapat item rate-up langsung)
#   2 = guaranteed (dapat item rate-up karena pull sebelumnya kalah)
RATE_LABELS = {0: "Lose", 1: "Win", 2: "Guaranteed"}


def load_json(path: Path) -> dict:
    with open(path, encoding="utf-8") as f:
        return json.load(f)


def build_account_map(raw: dict) -> dict:
    """
    Raw data menyimpan beberapa akun:
      - akun utama (aktif)  -> key TANPA prefix, mis. 'wish-counter-standard'
      - akun lain           -> key BERPREFIX, mis. 'account2-wish-counter-standard'
    Fungsi ini mengembalikan dict:
      { account_label: {"prefix": "" / "account2-" / ..., "uid": ..., "ar": ..., "wl": ...} }
    """
    other_accounts = [a.strip() for a in raw.get("accounts", "").split(",") if a.strip()]

    accounts = {
        "main": {
            "prefix": "",
            "uid": raw.get("wish-uid"),
            "ar": raw.get("ar"),
            "wl": raw.get("wl"),
        }
    }
    for acc in other_accounts:
        accounts[acc] = {
            "prefix": f"{acc}-",
            "uid": raw.get(f"{acc}-wish-uid"),
            "ar": raw.get(f"{acc}-ar"),
            "wl": raw.get(f"{acc}-wl"),
        }
    return accounts


def rarity_and_name(item_id: str, item_type: str, char_lookup: dict, weapon_lookup: dict):
    lookup = char_lookup if item_type == "character" else weapon_lookup
    entry = lookup.get(item_id)
    if entry is None:
        return None, None
    return entry.get("rarity"), entry.get("name")


def build_rows(raw: dict, accounts: dict, char_lookup: dict, weapon_lookup: dict):
    rows = []

    for account_label, acc_info in accounts.items():
        prefix = acc_info["prefix"]

        for banner_key, banner_label in BANNER_LABELS.items():
            full_key = f"{prefix}{banner_key}"
            banner_data = raw.get(full_key)
            if not banner_data:
                continue

            pulls = banner_data.get("pulls", [])
            for pull_number, p in enumerate(pulls, start=1):
                item_id = p.get("id")
                item_type = p.get("type")  # 'character' or 'weapon'
                rarity, item_name = rarity_and_name(item_id, item_type, char_lookup, weapon_lookup)

                rate_raw = p.get("rate")
                win_50_50 = RATE_LABELS.get(rate_raw) if rate_raw is not None else None

                rows.append(
                    {
                        "account": account_label,
                        "uid": acc_info["uid"],
                        "adventure_rank": acc_info["ar"],
                        "world_level": acc_info["wl"],
                        "banner_type": banner_label,
                        "banner_code": p.get("code"),
                        "pull_number": pull_number,
                        "datetime": p.get("time"),
                        "item_id": item_id,
                        "item_name": item_name if item_name else item_id,
                        "item_category": item_type,
                        "rarity": rarity,
                        "pity": p.get("pity"),
                        "rate_raw": rate_raw,
                        "win_50_50": win_50_50,
                        "manual_input": p.get("manualInput"),
                    }
                )

    return pd.DataFrame(rows)


def postprocess(df: pd.DataFrame) -> pd.DataFrame:
    df["datetime"] = pd.to_datetime(df["datetime"], errors="coerce")
    df = df.sort_values(["account", "banner_type", "datetime", "pull_number"]).reset_index(drop=True)

    # kolom turunan (memudahkan EDA)
    df["date"] = df["datetime"].dt.date
    df["year_month"] = df["datetime"].dt.to_period("M").astype(str)
    df["is_5star"] = df["rarity"] == 5
    df["is_4star"] = df["rarity"] == 4
    df["is_3star"] = df["rarity"] == 3

    # rarity yang tidak ketemu mapping -> beri tahu (data quality check)
    n_unmapped = df["rarity"].isna().sum()
    if n_unmapped:
        print(f"[WARN] {n_unmapped} baris tidak punya mapping rarity (item_id tidak dikenal).")

    return df


def parse_args():
    parser = argparse.ArgumentParser(
        description="Preprocess paimon-moe wish export jadi CSV tidy untuk EDA."
    )
    parser.add_argument(
        "--uid",
        type=str,
        default=None,
        help="Hanya proses akun dengan UID ini. Kosongkan untuk proses semua akun.",
    )
    parser.add_argument(
        "--list-uid",
        action="store_true",
        help="Tampilkan daftar UID yang tersedia di file export lalu keluar.",
    )
    return parser.parse_args()


def main():
    args = parse_args()

    if not CHAR_LOOKUP_PATH.exists() or not WEAPON_LOOKUP_PATH.exists():
        raise FileNotFoundError(
            "Lookup rarity belum ada. Jalankan dulu: python3 00_fetch_rarity_lookup.py"
        )

    raw = load_json(RAW_PATH)
    accounts = build_account_map(raw)

    if args.list_uid:
        print("UID yang tersedia di file export:")
        for label, info in accounts.items():
            print(f"  - {label}: uid={info['uid']}, AR={info['ar']}, WL={info['wl']}")
        return

    print("Akun terdeteksi:")
    for label, info in accounts.items():
        print(f"  - {label}: uid={info['uid']}, AR={info['ar']}, WL={info['wl']}")

    # Kalau user minta uid tertentu, filter dulu daftar akun sebelum build_rows
    # supaya lebih efisien & filenya cuma isi 1 akun.
    if args.uid:
        target_uid = str(args.uid)
        accounts = {
            label: info for label, info in accounts.items()
            if str(info["uid"]) == target_uid
        }
        if not accounts:
            available = ", ".join(str(info["uid"]) for info in build_account_map(raw).values())
            raise ValueError(
                f"UID '{args.uid}' tidak ditemukan. UID yang tersedia: {available}"
            )
        out_path = DATA_DIR / f"data_clean_{target_uid}.csv"
    else:
        out_path = DATA_DIR / "data_clean.csv"

    char_lookup = load_json(CHAR_LOOKUP_PATH)
    weapon_lookup = load_json(WEAPON_LOOKUP_PATH)

    df = build_rows(raw, accounts, char_lookup, weapon_lookup)
    df = postprocess(df)

    DATA_DIR.mkdir(parents=True, exist_ok=True)
    df.to_csv(out_path, index=False)

    print(f"\nTotal baris (pull): {len(df):,}")
    print(f"Rentang waktu       : {df['datetime'].min()} -> {df['datetime'].max()}")
    print("\nJumlah pull per banner:")
    print(df["banner_type"].value_counts().to_string())
    print("\nDistribusi rarity:")
    print(df["rarity"].value_counts(dropna=False).sort_index().to_string())
    print("\nWin/Lose 50-50 per rarity (banner event, 4* & 5*):")
    print(
        df[df["win_50_50"].notna()]
        .groupby(["rarity", "win_50_50"])
        .size()
        .to_string()
    )
    print(f"\nFile output tersimpan di: {out_path}")


if __name__ == "__main__":
    main()