-- ================================================================
-- Cricket Match Statistics — database.sql
-- REAL DATA version  (source: cricsheet.org)
-- Fact table: deliveries (~4.5M+ ball-by-ball rows)
-- ================================================================

CREATE DATABASE IF NOT EXISTS cricket_db;
USE cricket_db;

-- ────────────────────────────────────────────────────────────────
-- SECTION A: DDL
-- ────────────────────────────────────────────────────────────────

CREATE TABLE IF NOT EXISTS teams (
    team_id   INT          NOT NULL AUTO_INCREMENT,
    team_name VARCHAR(200) NOT NULL,
    PRIMARY KEY (team_id),
    UNIQUE KEY uq_team (team_name)
) ENGINE=InnoDB;

CREATE TABLE IF NOT EXISTS venues (
    venue_id   INT          NOT NULL AUTO_INCREMENT,
    venue_name VARCHAR(300) NOT NULL,
    PRIMARY KEY (venue_id),
    UNIQUE KEY uq_venue (venue_name(150))
) ENGINE=InnoDB;

CREATE TABLE IF NOT EXISTS players (
    player_id    INT          NOT NULL AUTO_INCREMENT,
    player_name  VARCHAR(200) NOT NULL,
    primary_team VARCHAR(200),
    PRIMARY KEY (player_id),
    KEY idx_pl_name (player_name(100))
) ENGINE=InnoDB;

CREATE TABLE IF NOT EXISTS matches (
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
    KEY idx_m_date    (match_date),
    KEY idx_m_type    (match_type),
    KEY idx_m_season  (season),
    KEY idx_m_t1      (team1_id),
    KEY idx_m_t2      (team2_id),
    CONSTRAINT fk_m_t1   FOREIGN KEY (team1_id)       REFERENCES teams(team_id),
    CONSTRAINT fk_m_t2   FOREIGN KEY (team2_id)       REFERENCES teams(team_id),
    CONSTRAINT fk_m_ven  FOREIGN KEY (venue_id)       REFERENCES venues(venue_id),
    CONSTRAINT fk_m_win  FOREIGN KEY (winner_id)      REFERENCES teams(team_id),
    CONSTRAINT fk_m_toss FOREIGN KEY (toss_winner_id) REFERENCES teams(team_id)
) ENGINE=InnoDB;

CREATE TABLE IF NOT EXISTS deliveries (
    delivery_id      BIGINT      NOT NULL AUTO_INCREMENT,
    match_id         INT,
    inning           TINYINT,
    `over`           INT,
    ball             INT,
    batting_team_id  INT,
    batter_id        INT,
    bowler_id        INT,
    runs_batter      TINYINT     DEFAULT 0,
    runs_extras      TINYINT     DEFAULT 0,
    runs_total       TINYINT     DEFAULT 0,
    wides            TINYINT     DEFAULT 0,
    no_balls         TINYINT     DEFAULT 0,
    byes             TINYINT     DEFAULT 0,
    leg_byes         TINYINT     DEFAULT 0,
    is_wicket        TINYINT(1)  DEFAULT 0,
    wicket_kind      VARCHAR(30),
    dismissed_batter VARCHAR(200),
    PRIMARY KEY (delivery_id),
    KEY idx_d_match   (match_id),
    KEY idx_d_batter  (batter_id),
    KEY idx_d_bowler  (bowler_id),
    KEY idx_d_wicket  (is_wicket),
    KEY idx_d_runs    (runs_total),
    CONSTRAINT fk_d_match   FOREIGN KEY (match_id)        REFERENCES matches(match_id),
    CONSTRAINT fk_d_batter  FOREIGN KEY (batter_id)       REFERENCES players(player_id),
    CONSTRAINT fk_d_bowler  FOREIGN KEY (bowler_id)       REFERENCES players(player_id),
    CONSTRAINT fk_d_bteam   FOREIGN KEY (batting_team_id) REFERENCES teams(team_id)
) ENGINE=InnoDB;


-- ────────────────────────────────────────────────────────────────
-- SECTION B: ANALYTICAL QUERIES  (real ball-by-ball data)
-- ────────────────────────────────────────────────────────────────

-- Q1. Top 15 Run Scorers (all formats, all time)
SELECT
    p.player_name,
    COUNT(DISTINCT d.match_id)     AS innings,
    SUM(d.runs_batter)             AS total_runs,
    MAX(d.runs_batter)             AS max_runs_single_ball,
    ROUND(AVG(d.runs_batter), 4)   AS avg_per_ball,
    SUM(CASE WHEN d.runs_batter = 6 THEN 1 ELSE 0 END) AS sixes,
    SUM(CASE WHEN d.runs_batter = 4 THEN 1 ELSE 0 END) AS fours,
    SUM(d.is_wicket)               AS times_dismissed
FROM deliveries d
JOIN players p ON d.batter_id = p.player_id
GROUP BY p.player_name
ORDER BY total_runs DESC
LIMIT 15;


-- Q2. Top Run Scorers by Format
SELECT
    p.player_name,
    m.format_label,
    COUNT(DISTINCT d.match_id)   AS matches,
    SUM(d.runs_batter)           AS runs,
    SUM(CASE WHEN d.runs_batter = 6 THEN 1 ELSE 0 END) AS sixes,
    SUM(CASE WHEN d.runs_batter = 4 THEN 1 ELSE 0 END) AS fours
FROM deliveries d
JOIN players p ON d.batter_id = p.player_id
JOIN matches  m ON d.match_id  = m.match_id
GROUP BY p.player_name, m.format_label
ORDER BY m.format_label, runs DESC
LIMIT 60;


-- Q3. Best Bowling Figures (most wickets, lowest economy)
SELECT
    p.player_name,
    COUNT(DISTINCT d.match_id)                              AS matches,
    SUM(d.is_wicket)                                        AS total_wickets,
    SUM(d.runs_total)                                       AS runs_given,
    -- Economy = runs per 6 legal balls
    ROUND(SUM(d.runs_total) /
          NULLIF(COUNT(CASE WHEN d.wides=0 AND d.no_balls=0 THEN 1 END), 0)
          * 6, 2)                                           AS economy,
    ROUND(COUNT(CASE WHEN d.wides=0 AND d.no_balls=0 THEN 1 END) /
          NULLIF(SUM(d.is_wicket), 0), 1)                  AS balls_per_wicket
FROM deliveries d
JOIN players p ON d.bowler_id = p.player_id
GROUP BY p.player_name
HAVING total_wickets >= 10
ORDER BY total_wickets DESC, economy ASC
LIMIT 15;


-- Q4. Team Win / Loss Record (all formats)
SELECT
    t.team_name,
    COUNT(DISTINCT m.match_id)   AS matches_played,
    SUM(CASE WHEN m.winner_id = t.team_id THEN 1 ELSE 0 END)    AS wins,
    SUM(CASE WHEN m.winner_id != t.team_id
              AND m.result_type NOT IN ('draw','tie','no result') THEN 1 ELSE 0 END) AS losses,
    SUM(CASE WHEN m.result_type IN ('draw','tie') THEN 1 ELSE 0 END)  AS draws,
    ROUND(100.0 * SUM(CASE WHEN m.winner_id = t.team_id THEN 1 ELSE 0 END)
                / NULLIF(COUNT(DISTINCT m.match_id), 0), 1)           AS win_pct
FROM teams t
JOIN matches m ON t.team_id IN (m.team1_id, m.team2_id)
GROUP BY t.team_name
ORDER BY wins DESC
LIMIT 30;


-- Q5. Toss Decision Impact  (does batting/fielding first help?)
SELECT
    m.toss_decision,
    m.match_type,
    COUNT(*)  AS total_matches,
    SUM(CASE WHEN m.toss_winner_id = m.winner_id THEN 1 ELSE 0 END) AS toss_winner_won,
    ROUND(
        100.0 * SUM(CASE WHEN m.toss_winner_id = m.winner_id THEN 1 ELSE 0 END)
              / COUNT(*), 1
    ) AS win_pct_after_toss
FROM matches m
WHERE m.result_type IN ('runs','wickets','innings')
GROUP BY m.toss_decision, m.match_type
ORDER BY m.match_type, m.toss_decision;


-- Q6. Venue Analysis  (matches hosted, avg run-rate proxy)
SELECT
    v.venue_name,
    COUNT(DISTINCT m.match_id)   AS matches,
    SUM(d.runs_total)            AS total_runs_scored,
    ROUND(SUM(d.runs_total) / NULLIF(COUNT(DISTINCT m.match_id), 0)) AS avg_runs_per_match,
    SUM(d.is_wicket)             AS total_wickets_fell
FROM venues v
JOIN matches    m ON m.venue_id     = v.venue_id
JOIN deliveries d ON d.match_id     = m.match_id
GROUP BY v.venue_name
ORDER BY matches DESC
LIMIT 20;


-- Q7. Six-Hitters Leaderboard (Power Hitters)
SELECT
    p.player_name,
    t.team_name,
    SUM(CASE WHEN d.runs_batter = 6 THEN 1 ELSE 0 END) AS sixes,
    SUM(CASE WHEN d.runs_batter = 4 THEN 1 ELSE 0 END) AS fours,
    SUM(d.runs_batter)                                  AS total_runs
FROM deliveries d
JOIN players p ON d.batter_id = p.player_id
JOIN teams   t ON d.batting_team_id = t.team_id
GROUP BY p.player_name, t.team_name
ORDER BY sixes DESC
LIMIT 15;


-- Q8. Head-to-Head Record: India vs Australia
SELECT
    t.team_name                          AS winner,
    m.match_type,
    m.match_date,
    m.result_type,
    COALESCE(m.margin_runs, m.margin_wickets) AS margin,
    v.venue_name,
    m.season
FROM matches m
JOIN teams  t ON m.winner_id  = t.team_id
JOIN venues v ON m.venue_id   = v.venue_id
WHERE (
        (SELECT team_name FROM teams WHERE team_id = m.team1_id) = 'India'
    AND (SELECT team_name FROM teams WHERE team_id = m.team2_id) = 'Australia'
) OR (
        (SELECT team_name FROM teams WHERE team_id = m.team1_id) = 'Australia'
    AND (SELECT team_name FROM teams WHERE team_id = m.team2_id) = 'India'
)
ORDER BY m.match_date DESC
LIMIT 50;


-- Q9. Season-wise Run Trends
SELECT
    m.season,
    m.format_label,
    COUNT(DISTINCT m.match_id)   AS matches,
    SUM(d.runs_total)            AS total_runs,
    SUM(d.is_wicket)             AS total_wickets,
    SUM(CASE WHEN d.runs_batter=6 THEN 1 ELSE 0 END) AS sixes,
    ROUND(SUM(d.runs_total) / NULLIF(COUNT(DISTINCT m.match_id),0)) AS avg_runs_per_match
FROM matches m
JOIN deliveries d ON d.match_id = m.match_id
GROUP BY m.season, m.format_label
ORDER BY m.season, m.format_label;


-- Q10. Most Dismissals per Wicket Type
SELECT
    wicket_kind,
    COUNT(*)                         AS total_dismissals,
    ROUND(100.0 * COUNT(*) /
          (SELECT COUNT(*) FROM deliveries WHERE is_wicket=1), 1) AS pct
FROM deliveries
WHERE is_wicket = 1 AND wicket_kind IS NOT NULL
GROUP BY wicket_kind
ORDER BY total_dismissals DESC;


-- Q11. Subquery: Players who faced more balls than the average batter
SELECT
    p.player_name,
    COUNT(*) AS balls_faced,
    SUM(d.runs_batter) AS runs
FROM deliveries d
JOIN players p ON d.batter_id = p.player_id
WHERE d.wides = 0     -- only legal balls faced
GROUP BY p.player_name
HAVING balls_faced > (
    SELECT AVG(ball_count)
    FROM (
        SELECT batter_id, COUNT(*) AS ball_count
        FROM deliveries WHERE wides = 0
        GROUP BY batter_id
    ) sub
)
ORDER BY balls_faced DESC
LIMIT 20;


-- Q12. Format-wise win % per team (Pivot-style)
SELECT
    t.team_name,
    COUNT(CASE WHEN m.format_label='ODI'  THEN 1 END) AS odi_played,
    SUM(CASE WHEN m.format_label='ODI'  AND m.winner_id=t.team_id THEN 1 ELSE 0 END) AS odi_wins,
    ROUND(100.0*SUM(CASE WHEN m.format_label='ODI'  AND m.winner_id=t.team_id THEN 1 ELSE 0 END)
               /NULLIF(COUNT(CASE WHEN m.format_label='ODI' THEN 1 END),0),1) AS odi_win_pct,

    COUNT(CASE WHEN m.format_label='T20I' THEN 1 END) AS t20i_played,
    SUM(CASE WHEN m.format_label='T20I' AND m.winner_id=t.team_id THEN 1 ELSE 0 END) AS t20i_wins,
    ROUND(100.0*SUM(CASE WHEN m.format_label='T20I' AND m.winner_id=t.team_id THEN 1 ELSE 0 END)
               /NULLIF(COUNT(CASE WHEN m.format_label='T20I' THEN 1 END),0),1) AS t20i_win_pct,

    COUNT(CASE WHEN m.format_label='Test' THEN 1 END) AS test_played,
    SUM(CASE WHEN m.format_label='Test' AND m.winner_id=t.team_id THEN 1 ELSE 0 END) AS test_wins,
    ROUND(100.0*SUM(CASE WHEN m.format_label='Test' AND m.winner_id=t.team_id THEN 1 ELSE 0 END)
               /NULLIF(COUNT(CASE WHEN m.format_label='Test' THEN 1 END),0),1) AS test_win_pct
FROM teams t
JOIN matches m ON t.team_id IN (m.team1_id, m.team2_id)
GROUP BY t.team_name
HAVING odi_played > 0 OR t20i_played > 0 OR test_played > 0
ORDER BY odi_wins DESC;


-- BONUS: Row count verification
SELECT 'teams'       AS tbl, COUNT(*) AS rows FROM teams
UNION ALL SELECT 'venues',     COUNT(*) FROM venues
UNION ALL SELECT 'players',    COUNT(*) FROM players
UNION ALL SELECT 'matches',    COUNT(*) FROM matches
UNION ALL SELECT 'deliveries', COUNT(*) FROM deliveries;
