"""
╔══════════════════════════════════════════════════════╗
║   Cricket Analytics — Professional Dashboard         ║
║   Run: streamlit run dashboard.py                    ║
║   Theme: Dark turf-green / cream / gold              ║
╚══════════════════════════════════════════════════════╝
"""

import streamlit as st
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import matplotlib.patches as mpatches
import matplotlib.ticker as mticker
from matplotlib.gridspec import GridSpec
import seaborn as sns
from sqlalchemy import create_engine
import warnings
warnings.filterwarnings("ignore")

# ─────────────────────────────────────────────────────
# PAGE CONFIG
# ─────────────────────────────────────────────────────
st.set_page_config(
    page_title="CricMetrics — Analytics Hub",
    page_icon="🏏",
    layout="wide",
    initial_sidebar_state="expanded",
)

# ─────────────────────────────────────────────────────
# DESIGN SYSTEM — CSS
# Palette:
#   bg-dark       #0b1a12   (deep cricket turf)
#   bg-card       #122218   (card surface)
#   bg-panel      #1a2e22   (lighter panel)
#   accent-gold   #d4a843   (cricket ball gold)
#   accent-cream  #f2ead8   (pitch cream)
#   accent-green  #4caf72   (outfield green)
#   accent-red    #c0392b   (cricket ball red)
#   text-primary  #f2ead8
#   text-muted    #8fa898
# ─────────────────────────────────────────────────────
st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=Playfair+Display:wght@700;800&family=DM+Sans:wght@300;400;500;600&family=DM+Mono:wght@400;500&display=swap');

/* ── GLOBAL ── */
html, body, [class*="css"], .stApp {
    background-color: #0b1a12 !important;
    font-family: 'DM Sans', sans-serif;
    color: #f2ead8;
}
.block-container { padding: 1.2rem 2rem 2rem !important; max-width: 1600px; }

/* ── HIDE STREAMLIT CHROME ── */
#MainMenu, footer, header { visibility: hidden; }

/* ── SIDEBAR ── */
section[data-testid="stSidebar"] {
    background: #0d1f14 !important;
    border-right: 1px solid #1e3626;
}
section[data-testid="stSidebar"] * { color: #c8dbc0 !important; }
section[data-testid="stSidebar"] .stSelectbox label,
section[data-testid="stSidebar"] .stSlider label { color: #8fa898 !important; font-size: 0.78rem; text-transform: uppercase; letter-spacing: 1px; }
section[data-testid="stSidebar"] [data-testid="stSelectbox"] > div > div {
    background: #1a2e22 !important;
    border: 1px solid #2a4a34 !important;
    color: #f2ead8 !important;
}

/* ── TOP BANNER ── */
.banner {
    background: linear-gradient(100deg, #0d2518 0%, #122a1c 40%, #0f2016 100%);
    border: 1px solid #2a4a34;
    border-radius: 14px;
    padding: 2rem 2.5rem;
    margin-bottom: 1.6rem;
    display: flex;
    align-items: center;
    justify-content: space-between;
    position: relative;
    overflow: hidden;
}
.banner::before {
    content: '';
    position: absolute;
    top: -40px; right: -40px;
    width: 220px; height: 220px;
    border-radius: 50%;
    background: radial-gradient(circle, rgba(212,168,67,0.08) 0%, transparent 70%);
}
.banner-title {
    font-family: 'Playfair Display', serif;
    font-size: 2.2rem;
    font-weight: 800;
    color: #f2ead8;
    letter-spacing: -0.5px;
    line-height: 1.1;
}
.banner-title span { color: #d4a843; }
.banner-sub {
    font-size: 0.82rem;
    color: #6a8a74;
    margin-top: 0.4rem;
    font-weight: 400;
    letter-spacing: 0.5px;
}
.banner-badge {
    background: #1a3a24;
    border: 1px solid #2e5a38;
    border-radius: 8px;
    padding: 0.6rem 1.2rem;
    font-size: 0.75rem;
    color: #4caf72;
    text-align: center;
    line-height: 1.7;
    font-family: 'DM Mono', monospace;
}
.live-dot {
    display: inline-block;
    width: 8px; height: 8px;
    background: #4caf72;
    border-radius: 50%;
    margin-right: 5px;
    animation: pulse 2s infinite;
}
@keyframes pulse { 0%,100%{opacity:1} 50%{opacity:0.3} }

/* ── KPI CARDS ── */
.kpi-row { display: flex; gap: 1rem; margin-bottom: 1.6rem; }
.kpi {
    flex: 1;
    background: #122218;
    border: 1px solid #1e3626;
    border-radius: 12px;
    padding: 1.1rem 1.2rem 0.9rem;
    position: relative;
    overflow: hidden;
    transition: border-color 0.2s;
}
.kpi:hover { border-color: #2e5a38; }
.kpi::after {
    content: '';
    position: absolute;
    bottom: 0; left: 0; right: 0;
    height: 2px;
    border-radius: 0 0 12px 12px;
}
.kpi.gold::after   { background: #d4a843; }
.kpi.green::after  { background: #4caf72; }
.kpi.red::after    { background: #c0392b; }
.kpi.cream::after  { background: #f2ead8; }
.kpi.teal::after   { background: #26a99a; }
.kpi-icon  { font-size: 1.3rem; margin-bottom: 0.3rem; line-height: 1; }
.kpi-val   { font-family: 'Playfair Display', serif; font-size: 1.85rem; font-weight: 700;
             color: #f2ead8; line-height: 1; }
.kpi-label { font-size: 0.7rem; color: #6a8a74; text-transform: uppercase;
             letter-spacing: 1.2px; margin-top: 0.35rem; font-weight: 500; }
.kpi-delta { font-size: 0.72rem; color: #4caf72; margin-top: 0.2rem; font-family:'DM Mono',monospace; }

/* ── SECTION HEADERS ── */
.sec-head {
    font-family: 'Playfair Display', serif;
    font-size: 1.05rem;
    color: #f2ead8;
    font-weight: 700;
    margin: 0 0 0.9rem 0;
    padding-bottom: 0.5rem;
    border-bottom: 1px solid #1e3626;
    display: flex;
    align-items: center;
    gap: 0.5rem;
}
.sec-head .dot { width:6px;height:6px;background:#d4a843;border-radius:50%;flex-shrink:0; }

/* ── CHART CARDS ── */
.chart-card {
    background: #122218;
    border: 1px solid #1e3626;
    border-radius: 12px;
    padding: 1.2rem 1.3rem 0.8rem;
    margin-bottom: 1.2rem;
}

/* ── DIVIDER ── */
.cdivider { border: none; border-top: 1px solid #1a2e22; margin: 1.2rem 0; }

/* ── DATA TABLE ── */
.stDataFrame { border-radius: 10px; overflow: hidden; }
div[data-testid="stDataFrameResizable"] {
    border: 1px solid #1e3626 !important;
    border-radius: 10px;
    background: #122218;
}

/* ── SELECTBOX / SLIDER ── */
.stSelectbox > div > div, .stMultiSelect > div > div {
    background: #1a2e22 !important;
    border-color: #2a4a34 !important;
}

/* ── SIDEBAR LOGO ── */
.sidebar-logo {
    font-family: 'Playfair Display', serif;
    font-size: 1.3rem;
    font-weight: 700;
    color: #d4a843;
    margin-bottom: 1.2rem;
    padding-bottom: 0.8rem;
    border-bottom: 1px solid #1e3626;
}
.sidebar-logo span { color: #4caf72; }

.filter-label {
    font-size: 0.7rem;
    color: #6a8a74;
    text-transform: uppercase;
    letter-spacing: 1px;
    margin-bottom: 0.2rem;
}
.sidebar-footer {
    font-size: 0.68rem;
    color: #3a5a44;
    padding-top: 1rem;
    border-top: 1px solid #1a2e22;
    line-height: 1.7;
}
</style>
""", unsafe_allow_html=True)


# ─────────────────────────────────────────────────────
# MATPLOTLIB THEME  (applies to all charts)
# ─────────────────────────────────────────────────────
BG       = "#122218"
BG_DARK  = "#0b1a12"
GOLD     = "#d4a843"
CREAM    = "#f2ead8"
GREEN    = "#4caf72"
RED      = "#c0392b"
MUTED    = "#4a6a54"
TEXT     = "#c8dbc0"

plt.rcParams.update({
    "figure.facecolor":  BG,
    "axes.facecolor":    BG,
    "axes.edgecolor":    "#1e3626",
    "axes.labelcolor":   TEXT,
    "axes.titlecolor":   CREAM,
    "axes.spines.top":   False,
    "axes.spines.right": False,
    "axes.spines.left":  True,
    "axes.spines.bottom":True,
    "xtick.color":       MUTED,
    "ytick.color":       TEXT,
    "text.color":        CREAM,
    "grid.color":        "#1a2e22",
    "grid.linewidth":    0.6,
    "font.family":       "DejaVu Sans",
    "font.size":         9.5,
    "figure.dpi":        130,
})


# ─────────────────────────────────────────────────────
# DATABASE
# ─────────────────────────────────────────────────────
@st.cache_resource
def get_engine():
    cfg = {
        "user":     "root",
        "password": "1234",         
        "host":     "localhost",
        "port":     3306,
        "database": "cricket_db",
    }
    return create_engine(
        f"mysql+mysqlconnector://{cfg['user']}:{cfg['password']}"
        f"@{cfg['host']}:{cfg['port']}/{cfg['database']}"
    )

@st.cache_data(ttl=300)
def q(sql):
    return pd.read_sql(sql, get_engine())


# ─────────────────────────────────────────────────────
# BANNER
# ─────────────────────────────────────────────────────
st.markdown("""
<div class="banner">
  <div>
    <div class="banner-title">Cric<span>Metrics</span></div>
    <div class="banner-sub">Ball-by-ball intelligence · Real data from cricsheet.org · MySQL backend</div>
  </div>
  <div class="banner-badge">
    <span class="live-dot"></span>LIVE DB<br>
    <span style="color:#f2ead8;font-size:1rem;font-family:'Playfair Display',serif">cricsheet.org</span><br>
    <span style="color:#6a8a74">9,700+ matches</span>
  </div>
</div>
""", unsafe_allow_html=True)


# ─────────────────────────────────────────────────────
# SIDEBAR
# ─────────────────────────────────────────────────────
with st.sidebar:
    st.markdown('<div class="sidebar-logo">🏏 Cric<span>Metrics</span></div>', unsafe_allow_html=True)

    st.markdown('<div class="filter-label">Match Format</div>', unsafe_allow_html=True)
    formats = ["All"] + q(
        "SELECT DISTINCT format_label FROM matches ORDER BY format_label"
    )["format_label"].tolist()
    sel_fmt = st.selectbox("", formats, label_visibility="collapsed")

    st.markdown('<div class="filter-label" style="margin-top:1rem">Season Range</div>', unsafe_allow_html=True)
    seasons_all = q("""
        SELECT DISTINCT season FROM matches
        WHERE season REGEXP '^[0-9]{4}$'
        ORDER BY season
    """)["season"].tolist()
    if len(seasons_all) >= 2:
        yr_min, yr_max = int(seasons_all[0]), int(seasons_all[-1])
        sel_years = st.slider("", yr_min, yr_max, (yr_min, yr_max), label_visibility="collapsed")
    else:
        sel_years = (2000, 2024)

    st.markdown('<div class="filter-label" style="margin-top:1rem">Top N Players</div>', unsafe_allow_html=True)
    top_n = st.slider("", 5, 25, 15, label_visibility="collapsed")

    st.markdown("""
    <div class="sidebar-footer">
      <b style="color:#4caf72">Data Source</b><br>
      cricsheet.org — free, open,<br>ball-by-ball cricket data<br><br>
      <b style="color:#4caf72">Stack</b><br>
      Python · MySQL · Streamlit<br>
      Matplotlib · Pandas
    </div>
    """, unsafe_allow_html=True)


# ─────────────────────────────────────────────────────
# FILTERS
# ─────────────────────────────────────────────────────
fmt_m  = "" if sel_fmt == "All" else f"AND m.format_label = '{sel_fmt}'"
fmt_dm = "" if sel_fmt == "All" else f"AND format_label = '{sel_fmt}'"
yr_cond = f"AND CAST(m.season AS UNSIGNED) BETWEEN {sel_years[0]} AND {sel_years[1]}"
yr_cond_dm = f"AND CAST(season AS UNSIGNED) BETWEEN {sel_years[0]} AND {sel_years[1]}"


# ─────────────────────────────────────────────────────
# KPIs
# ─────────────────────────────────────────────────────
kpi = q(f"""
    SELECT
        COUNT(DISTINCT m.match_id)                                  AS matches,
        COUNT(d.delivery_id)                                        AS deliveries,
        COALESCE(SUM(d.runs_batter),0)                              AS runs,
        COALESCE(SUM(d.is_wicket),0)                                AS wickets,
        COALESCE(SUM(CASE WHEN d.runs_batter=6 THEN 1 ELSE 0 END),0) AS sixes,
        COUNT(DISTINCT COALESCE(d.batter_id,0))                     AS batters
    FROM matches m
    JOIN deliveries d ON m.match_id = d.match_id
    WHERE 1=1 {fmt_m} {yr_cond}
""").iloc[0]

kpi_data = [
    ("🏟️", f"{int(kpi['matches']):,}",    "Matches",    "gold"),
    ("⚡", f"{int(kpi['deliveries']):,}", "Deliveries", "green"),
    ("🏏", f"{int(kpi['runs']):,}",       "Total Runs", "cream"),
    ("🎯", f"{int(kpi['wickets']):,}",    "Wickets",    "red"),
    ("💥", f"{int(kpi['sixes']):,}",      "Sixes",      "teal"),
]
cols = st.columns(5)
for col, (icon, val, lbl, color) in zip(cols, kpi_data):
    col.markdown(f"""
    <div class="kpi {color}">
      <div class="kpi-icon">{icon}</div>
      <div class="kpi-val">{val}</div>
      <div class="kpi-label">{lbl}</div>
    </div>""", unsafe_allow_html=True)

st.markdown('<hr class="cdivider">', unsafe_allow_html=True)


# ─────────────────────────────────────────────────────
# HELPER: chart card wrapper
# ─────────────────────────────────────────────────────
def chart_card(title, icon=""):
    st.markdown(f'<div class="sec-head"><span class="dot"></span>{icon} {title}</div>',
                unsafe_allow_html=True)


# ─────────────────────────────────────────────────────
# ROW 1 — Top Batsmen (H-bar)  +  Win Share (Donut)
# ─────────────────────────────────────────────────────
col1, col2 = st.columns([3, 2], gap="medium")

with col1:
    chart_card("Top Run Scorers", "🏅")
    bat = q(f"""
        SELECT p.player_name,
               SUM(d.runs_batter) AS runs,
               COUNT(DISTINCT d.match_id) AS inn,
               SUM(CASE WHEN d.runs_batter=4 THEN 1 ELSE 0 END) AS fours,
               SUM(CASE WHEN d.runs_batter=6 THEN 1 ELSE 0 END) AS sixes
        FROM deliveries d
        JOIN players p ON d.batter_id = p.player_id
        JOIN matches  m ON d.match_id  = m.match_id
        WHERE 1=1 {fmt_m} {yr_cond}
        GROUP BY p.player_name ORDER BY runs DESC LIMIT {top_n}
    """)

    fig, ax = plt.subplots(figsize=(9, max(4.5, top_n * 0.48)))
    fig.patch.set_facecolor(BG)
    ax.set_facecolor(BG)

    # gradient-like bars using two-segment stacked
    max_r  = bat["runs"].max()
    colors = [plt.cm.YlOrRd(0.35 + 0.6 * (i / max(len(bat)-1,1)))
              for i in range(len(bat))][::-1]

    y_pos = range(len(bat))
    bars  = ax.barh(y_pos, bat["runs"], color=colors, height=0.62,
                    linewidth=0, zorder=3)

    # subtle grid lines only on x
    ax.xaxis.grid(True, color="#1a2e22", linewidth=0.7, zorder=0)
    ax.set_axisbelow(True)

    # value labels
    for bar, (_, row) in zip(bars, bat.iterrows()):
        ax.text(bar.get_width() + max_r * 0.01, bar.get_y() + bar.get_height()/2,
                f"{int(row['runs']):,}", va="center", ha="left",
                color=CREAM, fontsize=8, fontfamily="DejaVu Sans")

    ax.set_yticks(list(y_pos))
    ax.set_yticklabels(bat["player_name"], fontsize=9, color=CREAM)
    ax.set_xlabel("Runs Scored", color=MUTED, fontsize=8.5)
    ax.tick_params(axis="x", colors=MUTED, labelsize=8)
    ax.tick_params(axis="y", length=0)
    ax.spines["left"].set_color("#1e3626")
    ax.spines["bottom"].set_color("#1e3626")
    ax.invert_yaxis()
    ax.set_xlim(0, max_r * 1.14)
    plt.tight_layout(pad=0.8)
    st.pyplot(fig)
    plt.close()

with col2:
    chart_card("Win Share by Team", "🏆")
    wins = q(f"""
        SELECT t.team_name, COUNT(*) AS wins
        FROM matches m JOIN teams t ON m.winner_id = t.team_id
        WHERE 1=1 {fmt_m} {yr_cond}
        GROUP BY t.team_name ORDER BY wins DESC LIMIT 9
    """)

    fig2, ax2 = plt.subplots(figsize=(5.2, 5.2))
    fig2.patch.set_facecolor(BG)
    ax2.set_facecolor(BG)

    palette = [
        "#d4a843","#4caf72","#c0392b","#26a99a","#8e6bbf",
        "#e87040","#4a90d9","#8fa898","#c8dbc0"
    ]
    wedges, texts, autos = ax2.pie(
        wins["wins"],
        labels=None,
        autopct="%1.0f%%",
        startangle=130,
        colors=palette[:len(wins)],
        pctdistance=0.78,
        wedgeprops={"linewidth": 1.5, "edgecolor": BG_DARK},
    )
    for auto in autos:
        auto.set_fontsize(7.5)
        auto.set_color("#0b1a12")
        auto.set_fontweight("bold")

    # donut hole
    centre = plt.Circle((0, 0), 0.52, color=BG)
    ax2.add_patch(centre)
    ax2.text(0, 0.08, "WINS", ha="center", va="center",
             fontsize=7.5, color=MUTED, fontfamily="DejaVu Sans")
    ax2.text(0, -0.15, f"{wins['wins'].sum():,}", ha="center", va="center",
             fontsize=13, color=CREAM, fontweight="bold",
             fontfamily="DejaVu Sans")

    # legend below
    legend_handles = [
        mpatches.Patch(color=palette[i], label=row["team_name"][:18])
        for i, (_, row) in enumerate(wins.iterrows())
    ]
    ax2.legend(handles=legend_handles, loc="lower center",
               bbox_to_anchor=(0.5, -0.32), ncol=2,
               frameon=False, fontsize=7.2,
               labelcolor=TEXT, handlelength=0.9, handleheight=0.9)
    plt.tight_layout(pad=0.5)
    st.pyplot(fig2)
    plt.close()

st.markdown('<hr class="cdivider">', unsafe_allow_html=True)


# ─────────────────────────────────────────────────────
# ROW 2 — Season Trend (full width)  FIXED x-axis
# ─────────────────────────────────────────────────────
chart_card("Run Scoring Trend by Season", "📈")
tr = q(f"""
    SELECT m.season,
           SUM(d.runs_total)              AS total_runs,
           COUNT(DISTINCT m.match_id)     AS matches,
           SUM(d.is_wicket)               AS wickets,
           SUM(CASE WHEN d.runs_batter=6 THEN 1 ELSE 0 END) AS sixes
    FROM matches m
    JOIN deliveries d ON m.match_id = d.match_id
    WHERE m.season IS NOT NULL
      AND m.season != 'Unknown'
      AND m.season REGEXP '^[0-9]{{4}}$'
      {fmt_dm} {yr_cond_dm}
    GROUP BY m.season ORDER BY m.season
""")

if len(tr) > 0:
    fig3, ax3 = plt.subplots(figsize=(14, 3.8))
    fig3.patch.set_facecolor(BG)
    ax3.set_facecolor(BG)

    x_idx = range(len(tr))

    # Runs area chart
    ax3.fill_between(x_idx, tr["total_runs"],
                     alpha=0.18, color=GOLD, linewidth=0)
    ax3.plot(x_idx, tr["total_runs"],
             color=GOLD, linewidth=2.2, zorder=4,
             solid_capstyle="round")
    ax3.scatter(x_idx, tr["total_runs"],
                color=GOLD, s=38, zorder=5, linewidths=0)

    # Sixes secondary axis
    ax3b = ax3.twinx()
    ax3b.set_facecolor(BG)
    ax3b.bar(x_idx, tr["sixes"],
             color=GREEN, alpha=0.35, width=0.55, zorder=2)
    ax3b.tick_params(axis="y", colors=GREEN, labelsize=7.5)
    ax3b.set_ylabel("Sixes", color=GREEN, fontsize=8)
    ax3b.spines["right"].set_color("#1e3626")
    ax3b.spines["top"].set_visible(False)
    ax3b.spines["left"].set_visible(False)
    ax3b.spines["bottom"].set_visible(False)

    # ── FIXED X-AXIS: show at most 15 evenly-spaced year labels ──
    n      = len(tr)
    MAX_LABELS = 15
    step   = max(1, int(np.ceil(n / MAX_LABELS)))
    tick_pos   = list(range(0, n, step))
    tick_labels = [tr["season"].iloc[i] for i in tick_pos]

    ax3.set_xticks(tick_pos)
    ax3.set_xticklabels(tick_labels, rotation=0, ha="center",
                        color=TEXT, fontsize=9)
    ax3.tick_params(axis="x", length=4, color="#1e3626")

    ax3.set_xlim(-0.5, n - 0.5)
    ax3.set_ylabel("Total Runs", color=MUTED, fontsize=8.5)
    ax3.tick_params(axis="y", colors=MUTED, labelsize=8)
    ax3.yaxis.set_major_formatter(mticker.FuncFormatter(
        lambda x, _: f"{int(x/1000)}K" if x >= 1000 else str(int(x))
    ))
    ax3.xaxis.grid(False)
    ax3.yaxis.grid(True, color="#1a2e22", linewidth=0.6, alpha=0.8)
    ax3.spines["left"].set_color("#1e3626")
    ax3.spines["bottom"].set_color("#1e3626")

    # legend
    leg_runs  = mpatches.Patch(color=GOLD,  alpha=0.9, label="Total Runs")
    leg_sixes = mpatches.Patch(color=GREEN, alpha=0.6, label="Sixes")
    ax3.legend(handles=[leg_runs, leg_sixes], loc="upper left",
               frameon=False, fontsize=8, labelcolor=TEXT)

    plt.tight_layout(pad=0.7)
    st.pyplot(fig3)
    plt.close()
else:
    st.info("No season data available for the selected filters.")

st.markdown('<hr class="cdivider">', unsafe_allow_html=True)


# ─────────────────────────────────────────────────────
# ROW 3 — Top Bowlers  +  Dismissal Types
# ─────────────────────────────────────────────────────
col3, col4 = st.columns(2, gap="medium")

with col3:
    chart_card("Top Wicket Takers", "🎳")
    bowl = q(f"""
        SELECT p.player_name,
               SUM(d.is_wicket) AS wickets,
               ROUND(SUM(d.runs_total) /
                     NULLIF(COUNT(CASE WHEN d.wides=0 AND d.no_balls=0 THEN 1 END),0) * 6, 2
               ) AS economy
        FROM deliveries d
        JOIN players p ON d.bowler_id = p.player_id
        JOIN matches  m ON d.match_id  = m.match_id
        WHERE 1=1 {fmt_m} {yr_cond}
        GROUP BY p.player_name HAVING wickets >= 5
        ORDER BY wickets DESC LIMIT {top_n}
    """)

    if len(bowl) > 0:
        fig4, ax4 = plt.subplots(figsize=(7, max(4.5, top_n * 0.48)))
        fig4.patch.set_facecolor(BG)
        ax4.set_facecolor(BG)

        cmap_b = [plt.cm.Blues(0.4 + 0.55 * (i / max(len(bowl)-1,1)))
                  for i in range(len(bowl))][::-1]
        bars4  = ax4.barh(range(len(bowl)), bowl["wickets"],
                          color=cmap_b, height=0.62,
                          linewidth=0, zorder=3)

        ax4.xaxis.grid(True, color="#1a2e22", linewidth=0.6, zorder=0)
        ax4.set_axisbelow(True)

        max_w = bowl["wickets"].max()
        for bar, (_, row) in zip(bars4, bowl.iterrows()):
            ax4.text(bar.get_width() + max_w * 0.01,
                     bar.get_y() + bar.get_height()/2,
                     f"{int(row['wickets'])}  eco:{row['economy']:.1f}",
                     va="center", ha="left", color=CREAM, fontsize=7.5)

        ax4.set_yticks(range(len(bowl)))
        ax4.set_yticklabels(bowl["player_name"], fontsize=9, color=CREAM)
        ax4.set_xlabel("Wickets", color=MUTED, fontsize=8.5)
        ax4.tick_params(axis="x", colors=MUTED, labelsize=8)
        ax4.tick_params(axis="y", length=0)
        ax4.spines["left"].set_color("#1e3626")
        ax4.spines["bottom"].set_color("#1e3626")
        ax4.invert_yaxis()
        ax4.set_xlim(0, max_w * 1.22)
        plt.tight_layout(pad=0.8)
        st.pyplot(fig4)
        plt.close()
    else:
        st.info("No bowling data for selected filters.")

with col4:
    chart_card("How Batsmen Get Out", "🎯")
    wkt = q(f"""
        SELECT d.wicket_kind,
               COUNT(*) AS cnt
        FROM deliveries d
        JOIN matches m ON d.match_id = m.match_id
        WHERE d.is_wicket = 1
          AND d.wicket_kind IS NOT NULL
          {fmt_m} {yr_cond}
        GROUP BY d.wicket_kind ORDER BY cnt DESC
    """)

    if len(wkt) > 0:
        fig5, ax5 = plt.subplots(figsize=(7, 4.5))
        fig5.patch.set_facecolor(BG)
        ax5.set_facecolor(BG)

        bar_colors = [
            "#d4a843","#4caf72","#c0392b","#26a99a",
            "#8e6bbf","#e87040","#4a90d9","#8fa898","#c8dbc0"
        ][:len(wkt)]

        bars5 = ax5.bar(range(len(wkt)), wkt["cnt"],
                        color=bar_colors, width=0.62,
                        linewidth=0, zorder=3)
        ax5.yaxis.grid(True, color="#1a2e22", linewidth=0.6, zorder=0)
        ax5.set_axisbelow(True)

        # percentage labels
        total_w = wkt["cnt"].sum()
        for bar, (_, row) in zip(bars5, wkt.iterrows()):
            pct = row["cnt"] / total_w * 100
            ax5.text(bar.get_x() + bar.get_width()/2,
                     bar.get_height() + total_w * 0.004,
                     f"{pct:.0f}%",
                     ha="center", va="bottom",
                     color=CREAM, fontsize=8)

        labels = [k.replace("-"," ").replace("_"," ").title()
                  for k in wkt["wicket_kind"]]
        ax5.set_xticks(range(len(wkt)))
        ax5.set_xticklabels(labels, rotation=32, ha="right",
                             fontsize=8.5, color=TEXT)
        ax5.tick_params(axis="y", colors=MUTED, labelsize=8)
        ax5.yaxis.set_major_formatter(mticker.FuncFormatter(
            lambda x, _: f"{int(x/1000)}K" if x >= 1000 else str(int(x))
        ))
        ax5.spines["left"].set_color("#1e3626")
        ax5.spines["bottom"].set_color("#1e3626")
        plt.tight_layout(pad=0.8)
        st.pyplot(fig5)
        plt.close()
    else:
        st.info("No dismissal data for selected filters.")

st.markdown('<hr class="cdivider">', unsafe_allow_html=True)


# ─────────────────────────────────────────────────────
# ROW 4 — Toss Impact  +  Format Distribution
# ─────────────────────────────────────────────────────
col5, col6 = st.columns(2, gap="medium")

with col5:
    chart_card("Toss Decision Impact", "🪙")
    toss = q(f"""
        SELECT toss_decision,
               COUNT(*) AS total,
               SUM(CASE WHEN toss_winner_id = winner_id THEN 1 ELSE 0 END) AS toss_won
        FROM matches
        WHERE result_type IN ('runs','wickets','innings')
          {fmt_dm} {yr_cond_dm}
        GROUP BY toss_decision
    """)

    if len(toss) > 0:
        toss["toss_lost"] = toss["total"] - toss["toss_won"]
        toss["win_pct"]   = (toss["toss_won"] / toss["total"] * 100).round(1)

        fig6, ax6 = plt.subplots(figsize=(6.5, 3.8))
        fig6.patch.set_facecolor(BG)
        ax6.set_facecolor(BG)

        x, w = np.arange(len(toss)), 0.34
        b1 = ax6.bar(x - w/2, toss["toss_won"],  w,
                     color=GREEN, alpha=0.9, linewidth=0, label="Won after toss")
        b2 = ax6.bar(x + w/2, toss["toss_lost"], w,
                     color=RED,   alpha=0.8, linewidth=0, label="Lost after toss")

        for bar in list(b1) + list(b2):
            ax6.text(bar.get_x() + bar.get_width()/2,
                     bar.get_height() + toss["total"].max() * 0.015,
                     f"{int(bar.get_height()):,}",
                     ha="center", va="bottom", fontsize=8, color=CREAM)

        # win% annotation
        for i, (_, row) in enumerate(toss.iterrows()):
            ax6.text(i, toss["total"].max() * 1.08,
                     f"{row['win_pct']}% win rate",
                     ha="center", fontsize=7.5, color=GOLD,
                     style="italic")

        ax6.set_xticks(x)
        ax6.set_xticklabels(
            [d.capitalize() + " first" for d in toss["toss_decision"]],
            fontsize=9.5, color=TEXT
        )
        ax6.yaxis.grid(True, color="#1a2e22", linewidth=0.6)
        ax6.tick_params(axis="y", colors=MUTED, labelsize=8)
        ax6.spines["left"].set_color("#1e3626")
        ax6.spines["bottom"].set_color("#1e3626")
        ax6.legend(frameon=False, fontsize=8, labelcolor=TEXT)
        ax6.set_ylabel("Matches", color=MUTED, fontsize=8.5)
        plt.tight_layout(pad=0.8)
        st.pyplot(fig6)
        plt.close()
    else:
        st.info("No toss data.")

with col6:
    chart_card("Matches by Format", "📊")
    fmt_dist = q("""
        SELECT format_label, COUNT(*) AS matches
        FROM matches GROUP BY format_label ORDER BY matches DESC
    """)

    if len(fmt_dist) > 0:
        fig7, ax7 = plt.subplots(figsize=(6.5, 3.8))
        fig7.patch.set_facecolor(BG)
        ax7.set_facecolor(BG)

        pal = ["#d4a843","#4caf72","#26a99a","#c0392b",
               "#8e6bbf","#e87040","#4a90d9","#8fa898","#c8dbc0","#6a8a74"]
        bars7 = ax7.bar(range(len(fmt_dist)), fmt_dist["matches"],
                        color=pal[:len(fmt_dist)], width=0.6, linewidth=0)

        for bar, (_, row) in zip(bars7, fmt_dist.iterrows()):
            ax7.text(bar.get_x() + bar.get_width()/2,
                     bar.get_height() + fmt_dist["matches"].max() * 0.015,
                     f"{row['matches']:,}",
                     ha="center", va="bottom", fontsize=8, color=CREAM)

        ax7.set_xticks(range(len(fmt_dist)))
        ax7.set_xticklabels(fmt_dist["format_label"],
                            fontsize=9, color=TEXT, rotation=15, ha="right")
        ax7.yaxis.grid(True, color="#1a2e22", linewidth=0.6)
        ax7.tick_params(axis="y", colors=MUTED, labelsize=8)
        ax7.spines["left"].set_color("#1e3626")
        ax7.spines["bottom"].set_color("#1e3626")
        ax7.set_ylabel("Matches", color=MUTED, fontsize=8.5)
        plt.tight_layout(pad=0.8)
        st.pyplot(fig7)
        plt.close()
    else:
        st.info("No format data.")

st.markdown('<hr class="cdivider">', unsafe_allow_html=True)


# ─────────────────────────────────────────────────────
# ROW 5 — Recent Matches Table
# ─────────────────────────────────────────────────────
chart_card("Recent Matches", "📋")

recent = q(f"""
    SELECT
        m.match_date         AS Date,
        t1.team_name         AS `Team 1`,
        t2.team_name         AS `Team 2`,
        tw.team_name         AS Winner,
        m.format_label       AS Format,
        m.event_name         AS Event,
        m.result_type        AS Result,
        COALESCE(
            CASE WHEN m.result_type='runs'
                 THEN CONCAT(m.margin_runs, ' runs')
                 WHEN m.result_type='wickets'
                 THEN CONCAT(m.margin_wickets, ' wkts')
                 ELSE m.result_type
            END, '—'
        )                    AS Margin,
        v.venue_name         AS Venue,
        m.season             AS Season
    FROM matches m
    JOIN teams  t1 ON m.team1_id = t1.team_id
    JOIN teams  t2 ON m.team2_id = t2.team_id
    LEFT JOIN teams tw ON m.winner_id = tw.team_id
    LEFT JOIN venues v  ON m.venue_id  = v.venue_id
    WHERE 1=1 {fmt_m} {yr_cond}
    ORDER BY m.match_date DESC LIMIT 150
""")

st.dataframe(
    recent,
    use_container_width=True,
    height=320,
    hide_index=True,
)

# ─────────────────────────────────────────────────────
# FOOTER
# ─────────────────────────────────────────────────────
st.markdown("""
<div style="text-align:center;padding:2rem 0 0.5rem;
     font-size:0.72rem;color:#3a5a44;letter-spacing:0.5px;
     border-top:1px solid #1a2e22;margin-top:1.5rem">
  CricMetrics · Data from <a href="https://cricsheet.org" target="_blank"
  style="color:#4caf72;text-decoration:none">cricsheet.org</a>
  · Built with Python, MySQL & Streamlit
</div>
""", unsafe_allow_html=True)