# 🎮 Genshin Impact Gacha Analytics

Pipeline end-to-end untuk menganalisis riwayat wish (gacha) Genshin Impact dari
export [Paimon.moe](https://paimon.moe) menjadi insight & dashboard interaktif:
Total Pull, Timeline, Distribusi Pity 5★, Win/Lose 50-50, Top Character/Weapon,
Banner Performance, sampai Luck Score.

```
Paimon.moe export (JSON)
        │
        ▼
00_fetch_rarity_lookup.py   → ambil tabel nama & rarity item dari repo Paimon.moe
        │
        ▼
01_preprocessing.py         → gabungkan export + lookup → data_clean.csv (tidy)
        │
        ▼
02_analytics.py             → 7 insight → CSV ringkasan + chart PNG (outputs/)
        │
        ▼
03_dashboard.py             → dashboard Streamlit interaktif (baca data_clean.csv)
```

---

## 📁 Struktur Folder

```
.
├── 00_fetch_rarity_lookup.py
├── 01_preprocessing.py
├── 02_analytics.py
├── 03_dashboard.py
├── requirements.txt
├── data/
│   ├── paimon-moe-local-data.json   ← kamu siapkan sendiri (lihat di bawah)
│   ├── char_full.json               ← dihasilkan step 00
│   ├── weapon_full.json             ← dihasilkan step 00
│   └── data_clean.csv               ← dihasilkan step 01
└── outputs/
    ├── 01_total_pull_progress_akun.(csv|png)
    ├── 02_timeline_wish.(csv|png)
    ├── 03_pity_distribution_5star.(csv|png)
    ├── 04_win_lose_50_50.(csv|png)
    ├── 05_top_character.csv, 05_top_weapon.csv, 05_top_character_weapon.png
    ├── 06_banner_performance.(csv|png)
    └── 07_luck_score.(csv|png)
```

## 📦 Cara Mendapatkan `paimon-moe-local-data.json`

1. Buka [paimon.moe](https://paimon.moe) dan lengkapi data wish kamu (manual input
   atau import lewat UIGF/link import bawaan situsnya).
2. Masuk ke halaman **Wish Counter**, lalu cari opsi **Export Data** (biasanya di
   pengaturan/menu titik tiga).
3. Simpan file hasil export sebagai `data/paimon-moe-local-data.json`.

---

## ⚙️ Instalasi

Butuh **Python 3.9+**.

```bash
pip install -r requirements.txt
```

Isi `requirements.txt`:

```
pandas>=2.0
matplotlib>=3.7
streamlit>=1.38
plotly>=5.20
```

---

## 🚀 Cara Pakai (urut sesuai pipeline)

### 1. `00_fetch_rarity_lookup.py`
Export Paimon.moe tidak menyertakan nama & rarity item — hanya id, waktu, tipe,
dan pity. Script ini mengambil tabel referensi id → `{name, rarity}` langsung
dari source code resmi Paimon.moe di GitHub.

```bash
python3 00_fetch_rarity_lookup.py
```

Butuh koneksi internet ke `raw.githubusercontent.com`. Output:
`data/char_full.json`, `data/weapon_full.json`. Jalankan ulang kapan saja untuk
refresh data karakter/senjata terbaru.

### 2. `01_preprocessing.py`
Menggabungkan raw export + lookup rarity menjadi satu tabel tidy (1 baris = 1
pull), siap dipakai untuk EDA maupun dashboard.

```bash
python3 01_preprocessing.py                 # semua akun → data/data_clean.csv
python3 01_preprocessing.py --list-uid      # lihat daftar UID yang tersedia
python3 01_preprocessing.py --uid 887284572 # hanya akun itu → data/data_clean_887284572.csv
```

Kolom output antara lain: `account`, `uid`, `adventure_rank`, `world_level`,
`banner_type`, `banner_code`, `pull_number`, `datetime`, `item_id`,
`item_name`, `item_category`, `rarity`, `pity`, `rate_raw`, `win_50_50`,
`date`, `year_month`, `is_5star`, `is_4star`, `is_3star`.

### 3. `02_analytics.py`
Menghasilkan 7 insight EDA, masing-masing sepasang file `.csv` (tabel
ringkasan) + `.png` (chart) di folder `outputs/`:

| # | Insight | File |
|---|---------|------|
| 1 | Total Pull & Progress Akun | `01_total_pull_progress_akun.*` |
| 2 | Timeline Wish per bulan | `02_timeline_wish.*` |
| 3 | Distribusi Pity 5★ | `03_pity_distribution_5star.*` |
| 4 | Win/Lose 50-50 | `04_win_lose_50_50.*` |
| 5 | Top Character & Top Weapon | `05_top_character*.csv`, `05_top_character_weapon.png` |
| 6 | Banner Performance | `06_banner_performance.*` |
| 7 | Luck Score (60% efisiensi pity + 40% win-rate) | `07_luck_score.*` |

```bash
python3 02_analytics.py
python3 02_analytics.py --input data/data_clean_887284572.csv --outdir outputs_887284572
```

### 4. `03_dashboard.py`
Dashboard Streamlit interaktif dengan filter akun, filter tanggal & banner,
7 tab insight (chart Plotly interaktif + tabel), mode perbandingan antar akun,
dan tombol download data.

```bash
streamlit run 03_dashboard.py
# atau untuk data akun tertentu:
streamlit run 03_dashboard.py -- --data data/data_clean_887284572.csv
```

Buka `http://localhost:8501` di browser.

---

## 🩹 Perbaikan Terbaru

- **Fix deprecation warning Streamlit**: seluruh pemakaian
  `use_container_width=True` di `03_dashboard.py` (17 lokasi, pada
  `st.plotly_chart` dan `st.dataframe`) sudah diganti menjadi `width='stretch'`
  sesuai anjuran resmi Streamlit (parameter `use_container_width` akan
  dihapus setelah 2025-12-31). Tidak ada perubahan perilaku — chart & tabel
  tetap melebar mengikuti container.

Kalau kamu meng-upgrade Streamlit di masa depan dan menemukan warning
deprecation baru, cukup jalankan pengecekan cepat:

```bash
grep -n "use_container_width" 03_dashboard.py
```

harus kosong (tidak ada hasil).

---

## 🧯 Troubleshooting

- **`FileNotFoundError: Lookup rarity belum ada`** → jalankan
  `00_fetch_rarity_lookup.py` dulu sebelum `01_preprocessing.py`.
- **`[WARN] N baris tidak punya mapping rarity`** saat preprocessing → ada
  `item_id` di export kamu yang belum ada di lookup Paimon.moe (biasanya
  karakter/senjata rilis baru). Jalankan ulang `00_fetch_rarity_lookup.py`
  untuk refresh, lalu preprocessing ulang.
- **Dashboard tidak menemukan data** → pastikan `data/data_clean.csv` sudah
  dibuat (jalankan step 1), atau arahkan manual dengan `-- --data <path>`.
- **Error koneksi saat `00_fetch_rarity_lookup.py`** → pastikan ada akses
  internet ke `raw.githubusercontent.com` (proxy/firewall kadang memblokirnya).

---

## 📜 Sumber & Kredit

- Data referensi nama/rarity karakter & senjata diambil dari source code
  [Paimon.moe](https://github.com/MadeBaruna/paimon-moe) (`src/data/characters.js`,
  `src/data/weaponList.js`).
- Genshin Impact adalah merek dagang milik HoYoverse/miHoYo. Proyek ini hanya
  alat analisis data pribadi, tidak berafiliasi dengan HoYoverse.