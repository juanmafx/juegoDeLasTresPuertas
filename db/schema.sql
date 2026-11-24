-- SQLite schema for monty-lab exact, simulate and optimum results recorded from any implementation.
-- tools/record_run.py applies it and loads CLI output; the original document is kept in output_json.
CREATE TABLE IF NOT EXISTS lab_runs (
    id INTEGER PRIMARY KEY,
    recorded_at TEXT NOT NULL DEFAULT (strftime('%Y-%m-%dT%H:%M:%fZ', 'now')),
    implementation TEXT NOT NULL CHECK (implementation IN ('python', 'java', 'php', 'c')),
    implementation_version TEXT NOT NULL CHECK (length(implementation_version) BETWEEN 1 AND 64),
    command TEXT NOT NULL CHECK (command IN ('exact', 'simulate', 'optimum')),
    doors INTEGER NOT NULL CHECK (doors BETWEEN 3 AND 64),
    prizes INTEGER NOT NULL CHECK (prizes BETWEEN 1 AND doors - 2),
    prior TEXT NOT NULL CHECK (prior = 'uniform' OR json_valid(prior)),
    pick INTEGER NOT NULL CHECK (pick BETWEEN 0 AND doors - 1),
    reveals INTEGER CHECK (reveals BETWEEN 0 AND doors - prizes - 1),
    host TEXT NOT NULL CHECK (host IN ('informed', 'random', 'biased', 'adversarial')),
    host_weights TEXT CHECK (json_valid(host_weights)),
    mixed TEXT NOT NULL CHECK (mixed GLOB '*/*'),
    observed TEXT CHECK (json_valid(observed)),
    seed INTEGER CHECK (seed >= 0),
    trials INTEGER CHECK (trials BETWEEN 1 AND 100000000),
    strategy TEXT CHECK (strategy IN ('stay', 'switch', 'mixed')),
    cost TEXT CHECK (cost GLOB '*/*'),
    output_json TEXT NOT NULL CHECK (json_valid(output_json)),
    CHECK (json_extract(output_json, '$.command') = command),
    CHECK ((command = 'optimum') = (reveals IS NULL)),
    CHECK ((command = 'simulate') = (seed IS NOT NULL AND trials IS NOT NULL)),
    CHECK ((command = 'simulate') OR (seed IS NULL AND trials IS NULL)),
    CHECK ((command = 'optimum') = (strategy IS NOT NULL AND cost IS NOT NULL)),
    CHECK ((command = 'optimum') OR (strategy IS NULL AND cost IS NULL)),
    CHECK ((host = 'biased') = (host_weights IS NOT NULL))
) STRICT;

CREATE INDEX IF NOT EXISTS idx_lab_runs_scenario
    ON lab_runs (command, doors, prizes, host, implementation);

CREATE TABLE IF NOT EXISTS lab_exact_results (
    run_id INTEGER PRIMARY KEY REFERENCES lab_runs (id) ON DELETE CASCADE,
    prize_at_pick TEXT NOT NULL CHECK (prize_at_pick GLOB '*/*'),
    decision TEXT NOT NULL CHECK (decision GLOB '*/*'),
    void_games TEXT NOT NULL CHECK (void_games GLOB '*/*'),
    no_offer TEXT NOT NULL CHECK (no_offer GLOB '*/*'),
    observed TEXT CHECK (observed GLOB '*/*'),
    stay_win TEXT CHECK (stay_win GLOB '*/*'),
    switch_win TEXT CHECK (switch_win GLOB '*/*'),
    mixed_win TEXT CHECK (mixed_win GLOB '*/*')
) STRICT;

CREATE TABLE IF NOT EXISTS lab_simulation_counts (
    run_id INTEGER PRIMARY KEY REFERENCES lab_runs (id) ON DELETE CASCADE,
    decision INTEGER NOT NULL CHECK (decision >= 0),
    void_games INTEGER NOT NULL CHECK (void_games >= 0),
    no_offer INTEGER NOT NULL CHECK (no_offer >= 0),
    observed INTEGER CHECK (observed BETWEEN 0 AND decision),
    sample_size INTEGER NOT NULL CHECK (sample_size BETWEEN 0 AND decision),
    stay_wins INTEGER NOT NULL CHECK (stay_wins BETWEEN 0 AND sample_size),
    switch_wins INTEGER NOT NULL CHECK (switch_wins BETWEEN 0 AND sample_size),
    mixed_wins INTEGER NOT NULL CHECK (mixed_wins BETWEEN 0 AND sample_size)
) STRICT;

CREATE TABLE IF NOT EXISTS lab_optimum_results (
    run_id INTEGER PRIMARY KEY REFERENCES lab_runs (id) ON DELETE CASCADE,
    optimum_reveals INTEGER NOT NULL CHECK (optimum_reveals >= 0),
    optimum_value TEXT NOT NULL CHECK (optimum_value GLOB '*/*'),
    parabola_shape TEXT CHECK (parabola_shape IN ('concave', 'convex', 'linear')),
    vertex_reveals TEXT CHECK (vertex_reveals GLOB '*/*'),
    rounded_vertex_regret TEXT CHECK (rounded_vertex_regret GLOB '*/*'),
    fitted_choice_reveals INTEGER CHECK (fitted_choice_reveals >= 0),
    fitted_choice_regret TEXT CHECK (fitted_choice_regret GLOB '*/*')
) STRICT;

CREATE VIEW IF NOT EXISTS lab_simulation_rates AS
SELECT
    r.id,
    r.implementation,
    r.implementation_version,
    r.doors,
    r.prizes,
    r.host,
    r.reveals,
    r.seed,
    r.trials,
    c.sample_size,
    CAST(c.stay_wins AS REAL) / NULLIF(c.sample_size, 0) AS stay_win_rate,
    CAST(c.switch_wins AS REAL) / NULLIF(c.sample_size, 0) AS switch_win_rate,
    CAST(c.mixed_wins AS REAL) / NULLIF(c.sample_size, 0) AS mixed_win_rate
FROM lab_runs AS r
JOIN lab_simulation_counts AS c ON c.run_id = r.id;

CREATE VIEW IF NOT EXISTS lab_simulation_disagreements AS
SELECT
    r.doors,
    r.prizes,
    r.prior,
    r.pick,
    r.reveals,
    r.host,
    r.host_weights,
    r.mixed,
    r.observed,
    r.seed,
    r.trials,
    COUNT(DISTINCT r.implementation) AS implementations,
    COUNT(DISTINCT c.decision || ',' || c.void_games || ',' || c.no_offer || ',' ||
        IFNULL(c.observed, '') || ',' || c.stay_wins || ',' || c.switch_wins || ',' ||
        c.mixed_wins) AS distinct_counts
FROM lab_runs AS r
JOIN lab_simulation_counts AS c ON c.run_id = r.id
GROUP BY r.doors, r.prizes, r.prior, r.pick, r.reveals, r.host, r.host_weights, r.mixed,
    r.observed, r.seed, r.trials
HAVING COUNT(DISTINCT c.decision || ',' || c.void_games || ',' || c.no_offer || ',' ||
    IFNULL(c.observed, '') || ',' || c.stay_wins || ',' || c.switch_wins || ',' ||
    c.mixed_wins) > 1;
