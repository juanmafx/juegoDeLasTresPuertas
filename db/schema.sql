-- Optional SQLite schema for persisted Monty Hall simulation runs.
CREATE TABLE IF NOT EXISTS simulation_runs (
    id INTEGER PRIMARY KEY,
    created_at TEXT NOT NULL DEFAULT (strftime('%Y-%m-%dT%H:%M:%fZ', 'now')),
    doors INTEGER NOT NULL CHECK (doors BETWEEN 3 AND 1024),
    opened_doors INTEGER NOT NULL CHECK (opened_doors >= 1 AND opened_doors <= doors - 2),
    host_policy TEXT NOT NULL CHECK (host_policy IN ('informed', 'random')),
    seed INTEGER NOT NULL CHECK (seed >= 0),
    requested_trials INTEGER NOT NULL CHECK (requested_trials BETWEEN 1 AND 100000000),
    valid_games INTEGER NOT NULL CHECK (valid_games BETWEEN 0 AND requested_trials),
    stay_wins INTEGER NOT NULL CHECK (stay_wins BETWEEN 0 AND valid_games),
    switch_wins INTEGER NOT NULL CHECK (switch_wins BETWEEN 0 AND valid_games),
    CHECK (host_policy = 'random' OR valid_games = requested_trials),
    CHECK (stay_wins + switch_wins <= valid_games)
) STRICT;

CREATE INDEX IF NOT EXISTS idx_simulation_runs_configuration
    ON simulation_runs (doors, opened_doors, host_policy, created_at);

CREATE VIEW IF NOT EXISTS simulation_run_rates AS
SELECT
    id,
    created_at,
    doors,
    opened_doors,
    host_policy,
    seed,
    valid_games,
    CAST(stay_wins AS REAL) / NULLIF(valid_games, 0) AS stay_win_rate,
    CAST(switch_wins AS REAL) / NULLIF(valid_games, 0) AS switch_win_rate
FROM simulation_runs;
