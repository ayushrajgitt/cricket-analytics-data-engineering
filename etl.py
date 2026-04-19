"""
╔══════════════════════════════════════════════════════════════════╗
║   Cricket Match Statistics — REAL DATA ETL Pipeline             ║
║   Source : cricsheet.org  (FREE, no API key needed)             ║
║   Data   : Ball-by-ball JSON for ODIs, T20Is, Tests, IPL, BBL   ║
║                                                                  ║
║   What this script does:                                        ║
║     1. Downloads real match ZIP files from cricsheet.org        ║
║     2. Parses every JSON match file (ball-by-ball)              ║
║     3. Cleans and transforms into 5 normalised tables           ║
║     4. Loads into MySQL (cricket_db)                            ║
║                                                                  ║
║   Expected row counts (all formats combined):                   ║
║     matches      :  ~21,000+  (all formats)                     ║
║     deliveries   : ~1,200,000+ (ball-by-ball — the fact table)  ║
║     players      :  ~5,000+                                     ║
║     teams        :  ~400+                                       ║
║     venues       :  ~200+                                       ║
║                                                                  ║
║   Run: python etl.py                                            ║
║   Deps: pip install requests tqdm sqlalchemy mysql-connector-python pandas ║
╚══════════════════════════════════════════════════════════════════╝
"""

import os, io, json, zipfile, time, hashlib, warnings
import requests
import pandas as pd
import numpy as np
import mysql.connector
from sqlalchemy import create_engine, text
from pathlib import Path
from collections import defaultdict

warnings.filterwarnings("ignore")

try:
    from tqdm import tqdm
    USE_TQDM = True
except ImportError:
    USE_TQDM = False
    class tqdm:
        def __init__(self, iterable=None, **kw):
            self.it = list(iterable) if iterable else []
            self.total = kw.get('total', len(self.it))
            self._n = 0
        def __iter__(self):
            for x in self.it:
                self._n += 1
                if self._n % 500 == 0 or self._n == self.total:
                    print(f"   {self._n}/{self.total}", end="\r")
                yield x
        def update(self, n=1): pass
        def __enter__(self): return self
        def __exit__(self, *a): pass

# ──────────────────────────────────────────────────────────────────
# CONFIG
# ──────────────────────────────────────────────────────────────────
DB_CONFIG = {
    "host":     "127.0.0.1",
    "user":     "root",
    "password": "1234",    # <── CHANGE THIS
    "database": "cricket_db",
    "port":     3306,
}

DOWNLOAD_DIR = Path("data/raw")          # downloaded ZIPs + extracted JSON
DOWNLOAD_DIR.mkdir(parents=True, exist_ok=True)

# Cricsheet direct ZIP download URLs  (NO API KEY — completely free)
# We grab ODIs, T20Is, Tests, IPL, BBL, PSL, CPL = 21,000+ matches
CRICSHEET_ZIPS = [
    # Format               URL                                         Expected matches
    ("ODI",   "https://cricsheet.org/downloads/odis_male_json.zip"),    # ~2,500
    ("T20I",  "https://cricsheet.org/downloads/t20s_male_json.zip"),    # ~3,200
    ("Test",  "https://cricsheet.org/downloads/tests_male_json.zip"),   # ~877
    ("IPL",   "https://cricsheet.org/downloads/ipl_male_json.zip"),     # ~1,190
    ("BBL",   "https://cricsheet.org/downloads/bbl_male_json.zip"),     # ~660
    ("PSL",   "https://cricsheet.org/downloads/psl_male_json.zip"),     # ~250
    ("CPL",   "https://cricsheet.org/downloads/cpl_male_json.zip"),     # ~400
    ("WPL",   "https://cricsheet.org/downloads/wpl_female_json.zip"),   # ~88
    ("BPL",   "https://cricsheet.org/downloads/bpl_male_json.zip"),     # ~460
    ("SA20",  "https://cricsheet.org/downloads/sa20_male_json.zip"),    # ~80
]

CHUNK_DB   = 1000   # rows per MySQL insert batch
DB_TIMEOUT = 300

# ──────────────────────────────────────────────────────────────────
# STEP 1 — DOWNLOAD ZIPs FROM CRICSHEET
# ──────────────────────────────────────────────────────────────────

def download_zip(label: str, url: str) -> Path:
    """Download a cricsheet ZIP, skip if already present."""
    local = DOWNLOAD_DIR / f"{label}.zip"
    if local.exists():
        print(f"   [CACHE] {label}.zip already downloaded, skipping.")
        return local

    print(f"   [DL] Downloading {label} from cricsheet.org ...")
    try:
        r = requests.get(url, stream=True, timeout=120,
                         headers={"User-Agent": "cricket-de-project/1.0"})
        r.raise_for_status()
        total = int(r.headers.get("content-length", 0))
        downloaded = 0
        with open(local, "wb") as f:
            for chunk in r.iter_content(chunk_size=65536):
                f.write(chunk)
                downloaded += len(chunk)
                if total:
                    pct = downloaded / total * 100
                    print(f"       {pct:.0f}%  {downloaded/1024/1024:.1f} MB / "
                          f"{total/1024/1024:.1f} MB", end="\r")
        print(f"\n   [DL] ✓ {label}.zip saved ({downloaded/1024/1024:.1f} MB)")
    except Exception as e:
        print(f"\n   [DL] ✗ FAILED for {label}: {e}")
        if local.exists():
            local.unlink()
        return None
    return local


def extract_zip(label: str, zip_path: Path) -> Path:
    """Extract JSON files from ZIP into a labelled subfolder."""
    if zip_path is None:
        return None
    out_dir = DOWNLOAD_DIR / label
    if out_dir.exists() and any(out_dir.glob("*.json")):
        print(f"   [CACHE] {label}/ already extracted.")
        return out_dir
    out_dir.mkdir(exist_ok=True)
    with zipfile.ZipFile(zip_path, "r") as zf:
        json_files = [n for n in zf.namelist() if n.endswith(".json")]
        print(f"   [EXTRACT] {label}: extracting {len(json_files):,} JSON files ...")
        for name in json_files:
            zf.extract(name, out_dir)
    return out_dir


# ──────────────────────────────────────────────────────────────────
# STEP 2 — PARSE JSON MATCH FILES
# ──────────────────────────────────────────────────────────────────
# Cricsheet JSON structure:
# {
#   "info": { "teams": [...], "venue": "...", "dates": [...],
#             "toss": {...}, "outcome": {...}, "players": {...} ... },
#   "innings": [
#     { "team": "...", "overs": [
#         { "over": 0, "deliveries": [
#             { "batter":"...", "bowler":"...", "runs": {"batter":0,"extras":0,"total":1},
#               "wickets": [...] } ... ] }
#       ] }
#   ]
# }

def _safe_str(v, maxlen=200):
    if v is None:
        return None
    return str(v)[:maxlen]


def parse_match_file(filepath: Path, format_label: str):
    """
    Parse a single Cricsheet JSON file.
    Returns:
        match_row   : dict  (one row for matches table)
        player_rows : list  (player dicts — deduplicated upstream)
        delivery_rows: list (one row per ball — the fact table)
    """
    try:
        with open(filepath, "r", encoding="utf-8") as f:
            data = json.load(f)
    except Exception:
        return None, [], []

    info      = data.get("info", {})
    innings   = data.get("innings", [])

    # ── match metadata ──────────────────────────────────────────
    match_id_raw = filepath.stem           # e.g. "1234567"
    dates        = info.get("dates", [])
    match_date   = dates[0] if dates else None
    teams        = info.get("teams", [])
    team1        = _safe_str(teams[0]) if len(teams) > 0 else "Unknown"
    team2        = _safe_str(teams[1]) if len(teams) > 1 else "Unknown"
    venue        = _safe_str(info.get("venue", "Unknown"))
    match_type   = _safe_str(info.get("match_type", format_label))
    gender       = _safe_str(info.get("gender", "male"))
    season       = _safe_str(info.get("season", (match_date[:4] if match_date else "Unknown")))
    event_name   = _safe_str(info.get("event", {}).get("name", format_label))

    toss         = info.get("toss", {})
    toss_winner  = _safe_str(toss.get("winner", ""))
    toss_decision= _safe_str(toss.get("decision", ""))

    outcome      = info.get("outcome", {})
    winner       = _safe_str(outcome.get("winner", None))
    result_type  = "no result"
    margin_runs  = None
    margin_wkts  = None
    if "winner" in outcome:
        by = outcome.get("by", {})
        if "runs" in by:
            result_type  = "runs"
            margin_runs  = int(by["runs"])
        elif "wickets" in by:
            result_type  = "wickets"
            margin_wkts  = int(by["wickets"])
        elif "innings" in by:
            result_type  = "innings"
    elif "result" in outcome:
        result_type = _safe_str(outcome["result"])

    pom_list    = info.get("player_of_match", [])
    player_of_match = _safe_str(pom_list[0]) if pom_list else None

    match_row = {
        "match_id_raw":      match_id_raw,
        "match_date":        match_date,
        "team1":             team1,
        "team2":             team2,
        "venue":             venue,
        "match_type":        match_type,
        "format_label":      format_label,
        "event_name":        event_name,
        "gender":            gender,
        "season":            season,
        "toss_winner":       toss_winner,
        "toss_decision":     toss_decision,
        "winner":            winner,
        "result_type":       result_type,
        "margin_runs":       margin_runs,
        "margin_wickets":    margin_wkts,
        "player_of_match":   player_of_match,
        "balls_per_over":    int(info.get("balls_per_over", 6)),
    }

    # ── players ─────────────────────────────────────────────────
    players_in_match = info.get("players", {})  # { "TeamA": ["P1","P2",...], ... }
    player_rows = []
    for team_name, roster in players_in_match.items():
        for pname in roster:
            player_rows.append({
                "player_name": _safe_str(pname),
                "team_name":   _safe_str(team_name),
            })

    # ── deliveries (ball-by-ball) ────────────────────────────────
    delivery_rows = []
    for inning_idx, inning in enumerate(innings):
        batting_team = _safe_str(inning.get("team", ""))
        for over_data in inning.get("overs", []):
            over_num = int(over_data.get("over", 0))
            for ball_idx, delivery in enumerate(over_data.get("deliveries", [])):
                runs_d   = delivery.get("runs", {})
                extras_d = delivery.get("extras", {})
                wickets  = delivery.get("wickets", [])

                wicket_kind     = None
                dismissed_batter= None
                if wickets:
                    w = wickets[0]
                    wicket_kind      = _safe_str(w.get("kind", ""))
                    dismissed_batter = _safe_str(w.get("player_out", ""))

                delivery_rows.append({
                    "match_id_raw":    match_id_raw,
                    "inning":          inning_idx + 1,
                    "over":            over_num,
                    "ball":            ball_idx + 1,
                    "batting_team":    batting_team,
                    "batter":          _safe_str(delivery.get("batter", "")),
                    "non_striker":     _safe_str(delivery.get("non_striker", "")),
                    "bowler":          _safe_str(delivery.get("bowler", "")),
                    "runs_batter":     int(runs_d.get("batter", 0)),
                    "runs_extras":     int(runs_d.get("extras", 0)),
                    "runs_total":      int(runs_d.get("total", 0)),
                    "wides":           int(extras_d.get("wides", 0)),
                    "no_balls":        int(extras_d.get("noballs", 0)),
                    "byes":            int(extras_d.get("byes", 0)),
                    "leg_byes":        int(extras_d.get("legbyes", 0)),
                    "is_wicket":       1 if wickets else 0,
                    "wicket_kind":     wicket_kind,
                    "dismissed_batter":dismissed_batter,
                })

    return match_row, player_rows, delivery_rows


def parse_all_matches(format_dirs: list):
    """
    Iterate all extracted JSON folders, parse every match.
    Returns three lists: match_rows, player_set, delivery_rows
    """
    all_matches   = []
    player_set    = {}   # player_name -> {team_name, ...} — deduplicated
    all_deliveries= []

    print("\n[PARSE] Reading all JSON match files ...")
    total_files = sum(
        len(list(d.rglob("*.json"))) for _, d in format_dirs if d
    )
    print(f"   Total JSON files to parse: {total_files:,}")

    bar = tqdm(total=total_files, desc="  Parsing", unit="match") if USE_TQDM else None

    for fmt_label, dir_path in format_dirs:
        if not dir_path:
            continue
        json_files = sorted(dir_path.rglob("*.json"))
        for fp in json_files:
            if USE_TQDM:
                bar.update(1)
            match_row, player_rows, delivery_rows = parse_match_file(fp, fmt_label)
            if match_row is None:
                continue
            all_matches.append(match_row)
            for pr in player_rows:
                key = pr["player_name"]
                if key and key not in player_set:
                    player_set[key] = pr["team_name"]
            all_deliveries.extend(delivery_rows)

    if USE_TQDM:
        bar.close()

    print(f"\n   Parsed: {len(all_matches):,} matches | "
          f"{len(player_set):,} unique players | "
          f"{len(all_deliveries):,} deliveries")
    return all_matches, player_set, all_deliveries


# ──────────────────────────────────────────────────────────────────
# STEP 3 — TRANSFORM: build normalised tables
# ──────────────────────────────────────────────────────────────────

def build_tables(all_matches, player_set, all_deliveries):
    print("\n[TRANSFORM] Building normalised dimension tables ...")

    # ── TEAMS ────────────────────────────────────────────────────
    all_team_names = set()
    for m in all_matches:
        all_team_names.add(m["team1"])
        all_team_names.add(m["team2"])
    all_team_names.discard("Unknown")
    all_team_names.discard(None)
    teams_df = pd.DataFrame({
        "team_id":   range(1, len(all_team_names)+1),
        "team_name": sorted(all_team_names),
    })
    team_id_map = {r.team_name: r.team_id for r in teams_df.itertuples()}

    # ── VENUES ───────────────────────────────────────────────────
    all_venues = sorted(set(
        m["venue"] for m in all_matches
        if m["venue"] and m["venue"] != "Unknown"
    ))
    venues_df = pd.DataFrame({
        "venue_id":   range(1, len(all_venues)+1),
        "venue_name": all_venues,
    })
    venue_id_map = {r.venue_name: r.venue_id for r in venues_df.itertuples()}

    # ── PLAYERS ──────────────────────────────────────────────────
    players_list = [
        {"player_id": i+1, "player_name": name, "primary_team": team}
        for i, (name, team) in enumerate(sorted(player_set.items()))
    ]
    players_df = pd.DataFrame(players_list)
    player_id_map = {r.player_name: r.player_id for r in players_df.itertuples()}

    # ── MATCHES ──────────────────────────────────────────────────
    print("[TRANSFORM] Building matches table ...")
    match_rows_out = []
    match_id_map   = {}   # match_id_raw -> match_id (int)
    for i, m in enumerate(all_matches, 1):
        match_id_map[m["match_id_raw"]] = i
        match_rows_out.append({
            "match_id":        i,
            "match_id_raw":    m["match_id_raw"],
            "match_date":      m["match_date"],
            "team1_id":        team_id_map.get(m["team1"]),
            "team2_id":        team_id_map.get(m["team2"]),
            "venue_id":        venue_id_map.get(m["venue"]),
            "match_type":      m["match_type"][:15] if m["match_type"] else None,
            "format_label":    m["format_label"],
            "event_name":      (m["event_name"] or "")[:150],
            "gender":          m["gender"],
            "season":          (m["season"] or "")[:10],
            "toss_winner_id":  team_id_map.get(m["toss_winner"]),
            "toss_decision":   m["toss_decision"],
            "winner_id":       team_id_map.get(m["winner"]),
            "result_type":     m["result_type"],
            "margin_runs":     m["margin_runs"],
            "margin_wickets":  m["margin_wickets"],
            "player_of_match": m["player_of_match"],
            "balls_per_over":  m["balls_per_over"],
        })
    matches_df = pd.DataFrame(match_rows_out)
    matches_df["match_date"] = pd.to_datetime(matches_df["match_date"], errors="coerce")

    # ── DELIVERIES (fact table) ───────────────────────────────────
    print("[TRANSFORM] Building deliveries fact table ...")
    print(f"   Converting {len(all_deliveries):,} delivery dicts to DataFrame ...")
    deliveries_df = pd.DataFrame(all_deliveries)
    deliveries_df["match_id"] = deliveries_df["match_id_raw"].map(match_id_map)
    deliveries_df["batter_id"]    = deliveries_df["batter"].map(player_id_map)
    deliveries_df["bowler_id"]    = deliveries_df["bowler"].map(player_id_map)
    deliveries_df["batting_team_id"] = deliveries_df["batting_team"].map(team_id_map)

    deliveries_df.insert(0, "delivery_id", range(1, len(deliveries_df)+1))
    deliveries_df.drop(columns=["match_id_raw", "batting_team",
                                 "batter", "non_striker", "bowler"],
                        inplace=True, errors="ignore")
    deliveries_df.fillna({"runs_batter":0,"runs_extras":0,"runs_total":0,
                           "wides":0,"no_balls":0,"byes":0,"leg_byes":0,
                           "is_wicket":0}, inplace=True)

    print(f"\n   ✓ teams        : {len(teams_df):,}")
    print(f"   ✓ venues       : {len(venues_df):,}")
    print(f"   ✓ players      : {len(players_df):,}")
    print(f"   ✓ matches      : {len(matches_df):,}")
    print(f"   ✓ deliveries   : {len(deliveries_df):,}")

    return teams_df, venues_df, players_df, matches_df, deliveries_df


# ──────────────────────────────────────────────────────────────────
# STEP 4 — LOAD INTO MYSQL
# ──────────────────────────────────────────────────────────────────

def create_database(cfg):
    print("\n[LOAD] Creating database if not exists ...")
    conn = mysql.connector.connect(
        host=cfg["host"], user=cfg["user"],
        password=cfg["password"], port=cfg["port"],
        connection_timeout=10
    )
    cur = conn.cursor()
    cur.execute(f"CREATE DATABASE IF NOT EXISTS `{cfg['database']}`;")
    conn.commit(); cur.close(); conn.close()


def get_engine(cfg):
    url = (f"mysql+mysqlconnector://{cfg['user']}:{cfg['password']}"
           f"@{cfg['host']}:{cfg['port']}/{cfg['database']}"
           f"?connect_timeout={DB_TIMEOUT}")
    return create_engine(url, pool_pre_ping=True,
                         connect_args={"charset":"utf8mb4"})


def create_tables(engine):
    print("[LOAD] Dropping and recreating tables ...")
    stmts = [
        "SET FOREIGN_KEY_CHECKS = 0",
        "DROP TABLE IF EXISTS deliveries",
        "DROP TABLE IF EXISTS matches",
        "DROP TABLE IF EXISTS players",
        "DROP TABLE IF EXISTS venues",
        "DROP TABLE IF EXISTS teams",
        "SET FOREIGN_KEY_CHECKS = 1",

        # TEAMS
        """CREATE TABLE teams (
            team_id   INT          NOT NULL AUTO_INCREMENT,
            team_name VARCHAR(200) NOT NULL,
            PRIMARY KEY (team_id),
            UNIQUE KEY uq_team (team_name)
        ) ENGINE=InnoDB""",

        # VENUES
        """CREATE TABLE venues (
            venue_id   INT          NOT NULL AUTO_INCREMENT,
            venue_name VARCHAR(300) NOT NULL,
            PRIMARY KEY (venue_id),
            UNIQUE KEY uq_venue (venue_name(150))
        ) ENGINE=InnoDB""",

        # PLAYERS
        """CREATE TABLE players (
            player_id    INT          NOT NULL AUTO_INCREMENT,
            player_name  VARCHAR(200) NOT NULL,
            primary_team VARCHAR(200),
            PRIMARY KEY (player_id),
            KEY idx_pl_name (player_name(100))
        ) ENGINE=InnoDB""",

        # MATCHES
        """CREATE TABLE matches (
            match_id        INT          NOT NULL AUTO_INCREMENT,
            match_id_raw    VARCHAR(30),
            match_date      DATE,
            team1_id        INT,
            team2_id        INT,
            venue_id        INT,
            match_type      VARCHAR(20),
            format_label    VARCHAR(20),
            event_name      VARCHAR(150),
            gender          VARCHAR(10),
            season          VARCHAR(10),
            toss_winner_id  INT,
            toss_decision   VARCHAR(10),
            winner_id       INT,
            result_type     VARCHAR(20),
            margin_runs     INT,
            margin_wickets  INT,
            player_of_match VARCHAR(200),
            balls_per_over  INT DEFAULT 6,
            PRIMARY KEY (match_id),
            KEY idx_m_date   (match_date),
            KEY idx_m_type   (match_type),
            KEY idx_m_season (season),
            KEY idx_m_t1     (team1_id),
            KEY idx_m_t2     (team2_id),
            KEY idx_m_raw    (match_id_raw),
            CONSTRAINT fk_m_t1  FOREIGN KEY (team1_id)       REFERENCES teams(team_id),
            CONSTRAINT fk_m_t2  FOREIGN KEY (team2_id)       REFERENCES teams(team_id),
            CONSTRAINT fk_m_ven FOREIGN KEY (venue_id)       REFERENCES venues(venue_id),
            CONSTRAINT fk_m_win FOREIGN KEY (winner_id)      REFERENCES teams(team_id),
            CONSTRAINT fk_m_toss FOREIGN KEY (toss_winner_id) REFERENCES teams(team_id)
        ) ENGINE=InnoDB""",

        # DELIVERIES  (1M+ rows — the real fact table)
        """CREATE TABLE deliveries (
            delivery_id    BIGINT      NOT NULL AUTO_INCREMENT,
            match_id       INT,
            inning         TINYINT,
            `over`         INT,
            ball           INT,
            batting_team_id INT,
            batter_id      INT,
            bowler_id      INT,
            runs_batter    TINYINT     DEFAULT 0,
            runs_extras    TINYINT     DEFAULT 0,
            runs_total     TINYINT     DEFAULT 0,
            wides          TINYINT     DEFAULT 0,
            no_balls       TINYINT     DEFAULT 0,
            byes           TINYINT     DEFAULT 0,
            leg_byes       TINYINT     DEFAULT 0,
            is_wicket      TINYINT(1)  DEFAULT 0,
            wicket_kind    VARCHAR(30),
            dismissed_batter VARCHAR(200),
            PRIMARY KEY (delivery_id),
            KEY idx_d_match  (match_id),
            KEY idx_d_batter (batter_id),
            KEY idx_d_bowler (bowler_id),
            KEY idx_d_wicket (is_wicket),
            KEY idx_d_runs   (runs_total),
            CONSTRAINT fk_d_match  FOREIGN KEY (match_id)        REFERENCES matches(match_id),
            CONSTRAINT fk_d_batter FOREIGN KEY (batter_id)       REFERENCES players(player_id),
            CONSTRAINT fk_d_bowler FOREIGN KEY (bowler_id)       REFERENCES players(player_id),
            CONSTRAINT fk_d_bteam  FOREIGN KEY (batting_team_id) REFERENCES teams(team_id)
        ) ENGINE=InnoDB""",
    ]
    with engine.connect() as conn:
        for s in stmts:
            conn.execute(text(s))
        conn.commit()
    print("   ✓ All tables and indexes created.")


def load_table(engine, df: pd.DataFrame, table: str, chunksize=10000):
    """Load a DataFrame in chunks, showing progress."""
    total = len(df)
    loaded = 0
    for start in range(0, total, chunksize):
        chunk = df.iloc[start:start+chunksize]
        chunk.to_sql(table, engine, if_exists="append", index=False)
        loaded += len(chunk)
        pct = loaded / total * 100
        print(f"   {table:<15}: {loaded:>10,} / {total:,}  ({pct:.0f}%)", end="\r")
    print(f"   {table:<15}: {total:>10,} rows  ✓")


# ──────────────────────────────────────────────────────────────────
# MAIN
# ──────────────────────────────────────────────────────────────────

def main():
    t0 = time.time()
    SEP = "=" * 65
    print(SEP)
    print("  Cricket DE Pipeline — REAL DATA from cricsheet.org")
    print(SEP)

    # ── 1. Download all ZIPs ──────────────────────────────────────
    print("\n[STEP 1] Downloading ZIP files from cricsheet.org ...")
    format_dirs = []
    for label, url in CRICSHEET_ZIPS:
        zip_path  = download_zip(label, url)
        dir_path  = extract_zip(label, zip_path)
        format_dirs.append((label, dir_path))

    # ── 2. Parse all JSON files ───────────────────────────────────
    print("\n[STEP 2] Parsing match JSON files ...")
    all_matches, player_set, all_deliveries = parse_all_matches(format_dirs)

    if not all_matches:
        print("ERROR: No matches parsed. Check your internet connection and try again.")
        return

    # ── 3. Transform ─────────────────────────────────────────────
    print("\n[STEP 3] Transforming into normalised tables ...")
    teams_df, venues_df, players_df, matches_df, deliveries_df = build_tables(
        all_matches, player_set, all_deliveries
    )

    # Save CSVs for audit / notebook reference
    print("\n[CSV] Saving dimension tables to data/ ...")
    os.makedirs("data", exist_ok=True)
    teams_df.to_csv("data/teams.csv", index=False)
    venues_df.to_csv("data/venues.csv", index=False)
    players_df.to_csv("data/players.csv", index=False)
    matches_df.to_csv("data/matches.csv", index=False)
    # deliveries CSV omitted (too large; it's in MySQL)
    print("   ✓ teams, venues, players, matches CSVs saved")

    # ── 4. Load to MySQL ─────────────────────────────────────────
    print("\n[STEP 4] Loading into MySQL ...")
    create_database(DB_CONFIG)
    engine = get_engine(DB_CONFIG)
    create_tables(engine)

    load_table(engine, teams_df,    "teams",     chunksize=500)
    load_table(engine, venues_df,   "venues",    chunksize=500)
    load_table(engine, players_df,  "players",   chunksize=2000)
    # matches: drop delivery_id auto column conflicts; load with numeric ids
    load_table(engine, matches_df,  "matches",   chunksize=5000)
    load_table(engine, deliveries_df, "deliveries", chunksize=CHUNK_DB)

    # ── 5. Verify ─────────────────────────────────────────────────
    print("\n[VERIFY] Row counts in MySQL:")
    grand_total = 0
    with engine.connect() as conn:
        for tbl in ["teams","venues","players","matches","deliveries"]:
            cnt = conn.execute(text(f"SELECT COUNT(*) FROM {tbl}")).scalar()
            grand_total += cnt
            print(f"   {tbl:<15}: {cnt:>12,}")

    elapsed = time.time() - t0
    m, s    = divmod(int(elapsed), 60)
    print(f"\n{SEP}")
    print(f"  PIPELINE COMPLETE   Time: {m}m {s}s")
    print(f"  Grand total rows  : {grand_total:,}")
    print(SEP)
    print("""
  NEXT STEPS:
  1. Open MySQL Workbench → Database → Reverse Engineer (for ER diagram)
  2. Run: jupyter notebook notebooks/notebook.ipynb
  3. Run: streamlit run dashboard/dashboard.py
    """)


if __name__ == "__main__":
    main()
