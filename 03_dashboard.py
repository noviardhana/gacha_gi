"""
03_dashboard.py
================
Interactive Streamlit Dashboard untuk Genshin Impact gacha analytics.

Load data_clean.csv dari 01_preprocessing.py dan transform menjadi
dashboard interaktif dengan:
    ✅ Account selector (filter by akun main atau secondary)
    ✅ 7 insights dalam tabs
    ✅ Interactive Plotly charts (hover, zoom, export)
    ✅ Metrics/KPI cards
    ✅ Account comparison mode (compare 2+ akun side-by-side)
    ✅ Data download (CSV export)

Cara pakai:
    pip install streamlit pandas plotly
    streamlit run 03_dashboard.py

    Atau untuk custom data:
    streamlit run 03_dashboard.py -- --data data/data_clean_887284572.csv
"""

import argparse
import sys
from pathlib import Path

import pandas as pd
import plotly.graph_objects as go
import plotly.express as px
import streamlit as st

BASE_DIR = Path(__file__).resolve().parent
DATA_DIR = BASE_DIR / "data"

# Color palette Genshin-inspired
RARITY_COLORS = {3: "#5b8fd6", 4: "#a256c9", 5: "#c98a3e"}
BANNER_COLORS = {
    "Character Event": "#c98a3e",
    "Weapon Event": "#5b8fd6",
    "Standard": "#6bbf7b",
    "Beginners": "#c9576a",
}
HARD_PITY = {
    "Character Event": 90,
    "Standard": 90,
    "Weapon Event": 77,
    "Beginners": 20,
}

# Page config
st.set_page_config(
    page_title="Genshin Gacha Dashboard",
    page_icon="🎮",
    layout="wide",
    initial_sidebar_state="expanded",
)

# CSS styling
st.markdown(
    """
    <style>
    .metric-card {
        background: linear-gradient(135deg, #c98a3e 0%, #a256c9 100%);
        padding: 20px;
        border-radius: 10px;
        color: white;
        text-align: center;
        box-shadow: 0 4px 15px rgba(0, 0, 0, 0.1);
    }
    .metric-value {
        font-size: 2.2em;
        font-weight: bold;
        margin: 10px 0;
    }
    .metric-label {
        font-size: 0.9em;
        opacity: 0.9;
    }
    .insight-header {
        border-bottom: 3px solid #c98a3e;
        padding-bottom: 10px;
        margin-bottom: 20px;
    }
    </style>
    """,
    unsafe_allow_html=True,
)


@st.cache_data
def load_data(filepath: str) -> pd.DataFrame:
    """Load dan clean data CSV."""
    df = pd.read_csv(filepath)
    df["datetime"] = pd.to_datetime(df["datetime"], errors="coerce")
    df["date"] = df["datetime"].dt.date
    df["year_month"] = df["datetime"].dt.to_period("M").astype(str)
    df["is_5star"] = df["rarity"] == 5
    df["is_4star"] = df["rarity"] == 4
    df["is_3star"] = df["rarity"] == 3
    return df


def display_metrics_row(df: pd.DataFrame):
    """Display KPI metrics di top."""
    col1, col2, col3, col4, col5 = st.columns(5)

    total_pulls = len(df)
    five_star_pct = (df["is_5star"].sum() / total_pulls * 100) if total_pulls > 0 else 0
    avg_pity_5 = df[df["is_5star"]]["pity"].mean() if df["is_5star"].sum() > 0 else 0
    five_star_count = df["is_5star"].sum()
    active_days = (df["datetime"].max() - df["datetime"].min()).days if len(df) > 0 else 0

    with col1:
        st.metric("📊 Total Pull", f"{total_pulls:,}", delta=None)

    with col2:
        st.metric("⭐ 5★ Count", f"{five_star_count:,}", delta=f"{five_star_pct:.1f}%")

    with col3:
        st.metric("🍀 Avg Pity 5★", f"{avg_pity_5:.0f}", delta=None)

    with col4:
        win_rate = calculate_win_rate(df)
        st.metric("🏆 50-50 Win Rate", f"{win_rate:.0f}%", delta=None)

    with col5:
        st.metric("📅 Active Days", f"{active_days:,}", delta=None)


def calculate_win_rate(df: pd.DataFrame) -> float:
    """Hitung win rate 50-50."""
    decisive = df[(df["win_50_50"].isin(["Win", "Lose"])) & (df["is_5star"] | df["is_4star"])]
    if len(decisive) == 0:
        return 0
    win_count = (decisive["win_50_50"] == "Win").sum()
    return (win_count / len(decisive) * 100) if len(decisive) > 0 else 0


# ============================================================================
# INSIGHT 1: Total Pull & Progress
# ============================================================================
def insight_1_total_pull(df: pd.DataFrame):
    st.markdown("### 📊 Total Pull & Progress Akun", unsafe_allow_html=True)

    summary = (
        df.groupby("account")
        .agg(
            uid=("uid", "first"),
            adventure_rank=("adventure_rank", "first"),
            world_level=("world_level", "first"),
            total_pull=("item_id", "count"),
            pull_5star=("is_5star", "sum"),
            pull_4star=("is_4star", "sum"),
            pull_3star=("is_3star", "sum"),
        )
        .reset_index()
    )
    summary["pct_5star"] = (summary["pull_5star"] / summary["total_pull"] * 100).round(2)

    col1, col2 = st.columns(2)

    with col1:
        fig = go.Figure()
        fig.add_trace(
            go.Bar(
                x=summary["account"],
                y=summary["pull_3star"],
                name="3★",
                marker_color=RARITY_COLORS[3],
            )
        )
        fig.add_trace(
            go.Bar(
                x=summary["account"],
                y=summary["pull_4star"],
                name="4★",
                marker_color=RARITY_COLORS[4],
            )
        )
        fig.add_trace(
            go.Bar(
                x=summary["account"],
                y=summary["pull_5star"],
                name="5★",
                marker_color=RARITY_COLORS[5],
            )
        )
        fig.update_layout(
            barmode="stack",
            title="Total Pull per Akun (breakdown rarity)",
            xaxis_title="Account",
            yaxis_title="Jumlah Pull",
            hovermode="x unified",
            height=400,
        )
        st.plotly_chart(fig, width='stretch')

    with col2:
        fig = go.Figure()
        fig.add_trace(
            go.Bar(
                x=summary["account"],
                y=summary["adventure_rank"],
                name="Adventure Rank",
                marker_color="#c98a3e",
            )
        )
        fig.add_trace(
            go.Bar(
                x=summary["account"],
                y=summary["world_level"],
                name="World Level",
                marker_color="#5b8fd6",
            )
        )
        fig.update_layout(
            barmode="group",
            title="Progress Akun (AR & WL)",
            xaxis_title="Account",
            yaxis_title="Level",
            height=400,
        )
        st.plotly_chart(fig, width='stretch')

    with st.expander("📋 Detail Data"):
        st.dataframe(summary, width='stretch', hide_index=True)


# ============================================================================
# INSIGHT 2: Timeline Wish
# ============================================================================
def insight_2_timeline(df: pd.DataFrame):
    st.markdown("### 📈 Timeline Wish", unsafe_allow_html=True)

    timeline = (
        df.groupby(["year_month", "banner_type"])
        .size()
        .reset_index(name="jumlah_pull")
        .sort_values("year_month")
    )

    pivot = timeline.pivot(index="year_month", columns="banner_type", values="jumlah_pull").fillna(0)
    banner_order = ["Character Event", "Weapon Event", "Standard", "Beginners"]
    pivot = pivot.reindex(columns=[b for b in banner_order if b in pivot.columns])

    fig = go.Figure()
    for banner in pivot.columns:
        fig.add_trace(
            go.Bar(
                x=pivot.index,
                y=pivot[banner],
                name=banner,
                marker_color=BANNER_COLORS.get(banner, "#999999"),
            )
        )
    fig.update_layout(
        barmode="stack",
        title="Timeline Wish per Bulan (breakdown banner)",
        xaxis_title="Bulan",
        yaxis_title="Jumlah Pull",
        hovermode="x unified",
        height=500,
    )
    st.plotly_chart(fig, width='stretch')

    with st.expander("📋 Detail Data"):
        st.dataframe(timeline, width='stretch', hide_index=True)


# ============================================================================
# INSIGHT 3: Pity Distribution 5★
# ============================================================================
def insight_3_pity_distribution(df: pd.DataFrame):
    st.markdown("### 🍀 Distribusi Pity 5★", unsafe_allow_html=True)

    five_star = df[df["is_5star"]].copy()
    if len(five_star) == 0:
        st.warning("Tidak ada 5★ di akun ini.")
        return

    five_star["hard_pity"] = five_star["banner_type"].map(HARD_PITY).fillna(90)

    banners = sorted(five_star["banner_type"].unique())
    cols = st.columns(len(banners)) if banners else []

    for col, banner in zip(cols, banners):
        with col:
            vals = five_star.loc[five_star["banner_type"] == banner, "pity"]
            if len(vals) > 0:
                fig = go.Figure()
                fig.add_trace(
                    go.Histogram(
                        x=vals,
                        nbinsx=20,
                        marker_color=BANNER_COLORS.get(banner, "#999999"),
                        name=banner,
                    )
                )
                fig.add_vline(
                    x=vals.mean(),
                    line_dash="dash",
                    line_color="#222222",
                    annotation_text=f"Rata-rata: {vals.mean():.1f}",
                )
                fig.update_layout(
                    title=banner,
                    xaxis_title="Pity",
                    yaxis_title="Frequency",
                    height=400,
                    showlegend=False,
                )
                st.plotly_chart(fig, width='stretch')

    with st.expander("📋 Detail Data"):
        detail = five_star[["banner_type", "datetime", "item_name", "item_category", "pity", "win_50_50"]].sort_values("datetime")
        st.dataframe(detail, width='stretch', hide_index=True)


# ============================================================================
# INSIGHT 4: Win/Lose 50-50
# ============================================================================
def insight_4_win_lose(df: pd.DataFrame):
    st.markdown("### 🏆 Win/Lose 50-50", unsafe_allow_html=True)

    rate_df = df[df["win_50_50"].notna()].copy()
    if len(rate_df) == 0:
        st.warning("Tidak ada data 50-50 untuk akun ini.")
        return

    col1, col2 = st.columns(2)

    with col1:
        summary = (
            rate_df.groupby(["banner_type", "rarity", "win_50_50"])
            .size()
            .reset_index(name="jumlah")
        )
        pivot = summary.pivot_table(
            index=["banner_type", "rarity"],
            columns="win_50_50",
            values="jumlah",
            fill_value=0,
        )
        pivot = pivot.reindex(columns=[c for c in ["Win", "Lose", "Guaranteed"] if c in pivot.columns])

        labels = [f"{b}<br>{r}★" for b, r in pivot.index]
        fig = go.Figure()
        colors_50_50 = {"Win": "#6bbf7b", "Lose": "#c9576a", "Guaranteed": "#c9a13e"}
        for col in pivot.columns:
            fig.add_trace(go.Bar(x=labels, y=pivot[col], name=col, marker_color=colors_50_50.get(col)))
        fig.update_layout(
            barmode="stack",
            title="Komposisi Win / Lose / Guaranteed",
            xaxis_title="Banner & Rarity",
            yaxis_title="Jumlah Pull",
            height=400,
        )
        st.plotly_chart(fig, width='stretch')

    with col2:
        decisive = rate_df[rate_df["win_50_50"].isin(["Win", "Lose"])]
        win_rate = (
            decisive.groupby(["banner_type", "rarity"])["win_50_50"]
            .apply(lambda s: (s == "Win").mean() * 100)
            .reset_index(name="win_rate_pct")
        )
        labels_wr = [f"{b}<br>{r}★" for b, r in zip(win_rate["banner_type"], win_rate["rarity"])]
        fig = go.Figure()
        fig.add_trace(go.Bar(x=labels_wr, y=win_rate["win_rate_pct"], marker_color="#6bbf7b"))
        fig.add_hline(y=50, line_dash="dash", line_color="#222222", annotation_text="50% (Baseline)")
        fig.update_layout(
            title="Win Rate 50/50 (Win vs Lose)",
            xaxis_title="Banner & Rarity",
            yaxis_title="Win Rate (%)",
            height=400,
            yaxis=dict(range=[0, 100]),
        )
        st.plotly_chart(fig, width='stretch')

    with st.expander("📋 Detail Data"):
        st.dataframe(summary, width='stretch', hide_index=True)


# ============================================================================
# INSIGHT 5: Top Character & Weapon
# ============================================================================
def insight_5_top_items(df: pd.DataFrame, top_n: int = 10):
    st.markdown("### 👑 Top Character & Weapon", unsafe_allow_html=True)

    col1, col2 = st.columns(2)

    with col1:
        char_df = df[(df["item_category"] == "character") & (df["rarity"] >= 4)]
        if len(char_df) > 0:
            top_char = (
                char_df.groupby(["item_name", "rarity"])
                .size()
                .reset_index(name="jumlah_didapat")
                .sort_values("jumlah_didapat", ascending=False)
                .head(top_n)
            )
            colors = [RARITY_COLORS.get(r, "#999999") for r in top_char["rarity"]]
            fig = go.Figure()
            fig.add_trace(
                go.Bar(
                    y=top_char["item_name"],
                    x=top_char["jumlah_didapat"],
                    orientation="h",
                    marker_color=colors,
                )
            )
            fig.update_layout(
                title="Top Character (4★ & 5★)",
                xaxis_title="Jumlah Didapat",
                yaxis_title="Character",
                height=500,
            )
            st.plotly_chart(fig, width='stretch')
        else:
            st.info("Tidak ada character 4★ atau 5★.")

    with col2:
        weapon_df = df[(df["item_category"] == "weapon") & (df["rarity"] >= 4)]
        if len(weapon_df) > 0:
            top_weapon = (
                weapon_df.groupby(["item_name", "rarity"])
                .size()
                .reset_index(name="jumlah_didapat")
                .sort_values("jumlah_didapat", ascending=False)
                .head(top_n)
            )
            colors = [RARITY_COLORS.get(r, "#999999") for r in top_weapon["rarity"]]
            fig = go.Figure()
            fig.add_trace(
                go.Bar(
                    y=top_weapon["item_name"],
                    x=top_weapon["jumlah_didapat"],
                    orientation="h",
                    marker_color=colors,
                )
            )
            fig.update_layout(
                title="Top Weapon (4★ & 5★)",
                xaxis_title="Jumlah Didapat",
                yaxis_title="Weapon",
                height=500,
            )
            st.plotly_chart(fig, width='stretch')
        else:
            st.info("Tidak ada weapon 4★ atau 5★.")


# ============================================================================
# INSIGHT 6: Banner Performance
# ============================================================================
def insight_6_banner_performance(df: pd.DataFrame):
    st.markdown("### 📍 Banner Performance", unsafe_allow_html=True)

    perf = (
        df.groupby("banner_type")
        .agg(
            total_pull=("item_id", "count"),
            pull_5star=("is_5star", "sum"),
            pull_4star=("is_4star", "sum"),
        )
        .reset_index()
    )
    perf["pull_per_5star"] = (perf["total_pull"] / perf["pull_5star"].replace(0, float("nan"))).round(1)
    perf["rate_5star_pct"] = (perf["pull_5star"] / perf["total_pull"] * 100).round(2)

    col1, col2, col3 = st.columns(3)

    with col1:
        fig = go.Figure()
        fig.add_trace(
            go.Bar(
                x=perf["banner_type"],
                y=perf["total_pull"],
                marker_color=[BANNER_COLORS.get(b, "#999") for b in perf["banner_type"]],
            )
        )
        fig.update_layout(title="Total Pull per Banner", xaxis_title="Banner", yaxis_title="Jumlah Pull", height=400)
        st.plotly_chart(fig, width='stretch')

    with col2:
        fig = go.Figure()
        fig.add_trace(
            go.Bar(
                x=perf["banner_type"],
                y=perf["pull_per_5star"],
                marker_color=[BANNER_COLORS.get(b, "#999") for b in perf["banner_type"]],
            )
        )
        fig.update_layout(
            title='Pull per 5★ (Semakin rendah = lebih efisien)',
            xaxis_title="Banner",
            yaxis_title="Pull per 5★",
            height=400,
        )
        st.plotly_chart(fig, width='stretch')

    with col3:
        decisive = df[(df["win_50_50"].isin(["Win", "Lose"])) & (df["is_5star"] | df["is_4star"])]
        if len(decisive) > 0:
            win_rate = (
                decisive.groupby("banner_type")["win_50_50"]
                .apply(lambda s: (s == "Win").mean() * 100)
                .reset_index(name="win_rate_pct")
            )
            fig = go.Figure()
            fig.add_trace(
                go.Bar(
                    x=win_rate["banner_type"],
                    y=win_rate["win_rate_pct"],
                    marker_color="#6bbf7b",
                )
            )
            fig.add_hline(y=50, line_dash="dash", line_color="#222222", annotation_text="Baseline 50%")
            fig.update_layout(
                title="Win Rate 50/50 per Banner",
                xaxis_title="Banner",
                yaxis_title="Win Rate (%)",
                height=400,
                yaxis=dict(range=[0, 100]),
            )
            st.plotly_chart(fig, width='stretch')

    with st.expander("📋 Detail Data"):
        st.dataframe(perf, width='stretch', hide_index=True)


# ============================================================================
# INSIGHT 7: Luck Score
# ============================================================================
def insight_7_luck_score(df: pd.DataFrame):
    st.markdown("### ✨ Luck Score", unsafe_allow_html=True)

    five_star = df[df["is_5star"]].copy()
    if len(five_star) == 0:
        st.warning("Tidak ada 5★ di akun ini. Luck Score tidak dapat dihitung.")
        return

    five_star["hard_pity"] = five_star["banner_type"].map(HARD_PITY).fillna(90)
    five_star["pity_luck"] = (1 - (five_star["pity"] - 1) / (five_star["hard_pity"] - 1)) * 100

    pity_luck_by_account = five_star.groupby("account")["pity_luck"].mean()

    decisive = df[df["win_50_50"].isin(["Win", "Lose"])]
    winrate_by_account = (
        decisive.groupby("account")["win_50_50"].apply(lambda s: (s == "Win").mean() * 100)
        if len(decisive) > 0
        else pd.Series(dtype=float)
    )

    accounts = df["account"].unique()
    rows = []
    for acc in accounts:
        pity_luck = pity_luck_by_account.get(acc, float("nan"))
        winrate = winrate_by_account.get(acc, float("nan"))
        components = [c for c in [pity_luck, winrate] if pd.notna(c)]
        weights = []
        if pd.notna(pity_luck):
            weights.append((pity_luck, 0.6))
        if pd.notna(winrate):
            weights.append((winrate, 0.4))
        if weights:
            total_w = sum(w for _, w in weights)
            luck_score = sum(v * w for v, w in weights) / total_w
        else:
            luck_score = float("nan")

        rows.append(
            {
                "account": acc,
                "avg_pity_luck": round(pity_luck, 1) if pd.notna(pity_luck) else None,
                "win_rate_pct": round(winrate, 1) if pd.notna(winrate) else None,
                "luck_score": round(luck_score, 1) if pd.notna(luck_score) else None,
            }
        )

    luck_df = pd.DataFrame(rows).sort_values("luck_score", ascending=False, na_position="last")

    col1, col2 = st.columns(2)

    with col1:
        fig = go.Figure()
        fig.add_trace(
            go.Bar(
                x=luck_df["account"],
                y=luck_df["luck_score"],
                marker_color="#c98a3e",
            )
        )
        fig.add_hline(y=50, line_dash="dash", line_color="#222222", annotation_text="Baseline 50 (Netral)")
        fig.update_layout(
            title="Luck Score per Akun",
            xaxis_title="Account",
            yaxis_title="Luck Score (0-100+)",
            height=400,
        )
        st.plotly_chart(fig, width='stretch')

    with col2:
        st.markdown("""
        #### 📊 Rumus Luck Score
        - **60%** = Efisiensi Pity (semakin rendah pity = semakin tinggi score)
        - **40%** = Win Rate 50-50 (semakin tinggi win rate = semakin tinggi score)
        - **Baseline 50** = Netral (hasil rata-rata statistik)
        
        #### 🎯 Interpretasi
        - **> 70**: Sangat beruntung! 🍀
        - **50-70**: Di atas rata-rata
        - **< 50**: Kurang beruntung (tapi statistik seimbang dalam jangka panjang)
        """)

        with st.expander("📋 Detail Data"):
            st.dataframe(luck_df, width='stretch', hide_index=True)


# ============================================================================
# MAIN APP
# ============================================================================
def main():
    # Parse arguments
    parser = argparse.ArgumentParser()
    parser.add_argument("--data", type=str, default=None, help="Path ke data_clean.csv")
    try:
        args = parser.parse_args()
    except SystemExit:
        args = argparse.Namespace(data=None)

    data_path = args.data if args.data else str(DATA_DIR / "data_clean.csv")
    if not Path(data_path).exists():
        st.error(f"❌ File tidak ditemukan: {data_path}")
        st.info("Jalankan 01_preprocessing.py untuk generate data_clean.csv")
        return

    # Load data
    df = load_data(data_path)

    # Sidebar: Account selector
    st.sidebar.title("⚙️ Filter")
    all_accounts = sorted(df["account"].unique())

    mode = st.sidebar.radio(
        "Mode Tampilan",
        options=["Single Account", "Compare Accounts", "All Accounts"],
        index=0,
    )

    if mode == "Single Account":
        selected_account = st.sidebar.selectbox("Pilih Akun", all_accounts, index=0)
        display_df = df[df["account"] == selected_account].copy()
        title = f"🎮 {selected_account} Account"
    elif mode == "Compare Accounts":
        selected_accounts = st.sidebar.multiselect("Pilih Akun untuk Dibandingkan", all_accounts, default=all_accounts[:min(2, len(all_accounts))])
        if not selected_accounts:
            st.warning("Pilih minimal 1 akun untuk dibandingkan.")
            return
        display_df = df[df["account"].isin(selected_accounts)].copy()
        title = f"🎮 Comparing: {', '.join(selected_accounts)}"
    else:  # All Accounts
        selected_accounts = all_accounts
        display_df = df.copy()
        title = "🎮 All Accounts"

    # Header
    st.title(title)
    st.divider()

    # Metrics
    display_metrics_row(display_df)
    st.divider()

    # Sidebar: Additional filters
    min_date = display_df["datetime"].min()
    max_date = display_df["datetime"].max()
    date_range = st.sidebar.slider(
        "Filter Tanggal",
        min_value=min_date.date(),
        max_value=max_date.date(),
        value=(min_date.date(), max_date.date()),
    )
    display_df = display_df[(display_df["datetime"].dt.date >= date_range[0]) & (display_df["datetime"].dt.date <= date_range[1])]

    banner_filter = st.sidebar.multiselect(
        "Filter Banner",
        options=display_df["banner_type"].unique(),
        default=display_df["banner_type"].unique(),
    )
    display_df = display_df[display_df["banner_type"].isin(banner_filter)]

    # Tabs for insights
    tab1, tab2, tab3, tab4, tab5, tab6, tab7 = st.tabs(
        ["📊 Total Pull", "📈 Timeline", "🍀 Pity 5★", "🏆 50-50", "👑 Top Items", "📍 Banner", "✨ Luck Score"]
    )

    with tab1:
        insight_1_total_pull(display_df)

    with tab2:
        insight_2_timeline(display_df)

    with tab3:
        insight_3_pity_distribution(display_df)

    with tab4:
        insight_4_win_lose(display_df)

    with tab5:
        insight_5_top_items(display_df)

    with tab6:
        insight_6_banner_performance(display_df)

    with tab7:
        insight_7_luck_score(display_df)

    # Data download
    st.divider()
    st.sidebar.markdown("---")
    st.sidebar.subheader("📥 Download Data")
    csv = display_df.to_csv(index=False)
    st.sidebar.download_button(
        label="📥 Download Filtered Data (CSV)",
        data=csv,
        file_name=f"gacha_data_{date_range[0]}_{date_range[1]}.csv",
        mime="text/csv",
    )


if __name__ == "__main__":
    main()