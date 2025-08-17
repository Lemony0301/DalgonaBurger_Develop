-- ===========================================
-- Clean setup for "gameapp" on database dalgona_db
-- Creates role, schema, tables, seed, triggers
-- All ASCII, UTF-8 safe
-- ===========================================

-- Optional: CREATE DATABASE dalgona_db;

SET client_encoding = 'UTF8';

-- 1) App role
DO $$
BEGIN
  IF NOT EXISTS (SELECT FROM pg_roles WHERE rolname = 'gameapp_user') THEN
    CREATE ROLE gameapp_user LOGIN PASSWORD '1234';
  END IF;
END$$;

-- 2) DB connect privilege
GRANT CONNECT ON DATABASE dalgona_db TO gameapp_user;

-- 3) Schema
CREATE SCHEMA IF NOT EXISTS gameapp AUTHORIZATION gameapp_user;

-- 4) Fix search_path for the role on this DB
ALTER ROLE gameapp_user IN DATABASE dalgona_db SET search_path = gameapp, public;

-- 5) Build objects under gameapp and owned by gameapp_user
SET search_path TO gameapp, public;
SET ROLE gameapp_user;

-- ========== Tables ==========

CREATE TABLE IF NOT EXISTS users (
  user_id    TEXT PRIMARY KEY,
  created_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE TABLE IF NOT EXISTS stages (
  stage_id       SERIAL PRIMARY KEY,
  code           TEXT NOT NULL UNIQUE,
  next_stage_id  INT NULL REFERENCES stages(stage_id)
);

CREATE TABLE IF NOT EXISTS user_stage_progress (
  user_id        TEXT NOT NULL REFERENCES users(user_id) ON DELETE CASCADE,
  stage_id       INT  NOT NULL REFERENCES stages(stage_id),
  unlocked       BOOLEAN NOT NULL DEFAULT FALSE,
  cleared        BOOLEAN NOT NULL DEFAULT FALSE,
  prompt_length  INT NULL,
  clear_time_ms  BIGINT NULL,
  cleared_at     TIMESTAMPTZ NULL,
  updated_at     TIMESTAMPTZ NOT NULL DEFAULT now(),
  PRIMARY KEY (user_id, stage_id),
  CHECK (cleared = FALSE OR unlocked = TRUE),
  CHECK (
    (cleared = TRUE AND prompt_length IS NOT NULL AND clear_time_ms IS NOT NULL)
    OR (cleared = FALSE)
  )
);

CREATE TABLE IF NOT EXISTS run_logs (
  record_id      BIGSERIAL PRIMARY KEY,
  user_id        TEXT NOT NULL REFERENCES users(user_id) ON DELETE CASCADE,
  stage_code     TEXT NOT NULL REFERENCES stages(code),
  prompt_length  INT  NOT NULL,
  clear_time_ms  BIGINT NOT NULL,
  cleared_at     TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE INDEX IF NOT EXISTS idx_stages_code        ON stages(code);
CREATE INDEX IF NOT EXISTS idx_progress_user      ON user_stage_progress(user_id);
CREATE INDEX IF NOT EXISTS idx_progress_stage     ON user_stage_progress(stage_id);
CREATE INDEX IF NOT EXISTS idx_runlogs_user       ON run_logs(user_id);
CREATE INDEX IF NOT EXISTS idx_runlogs_stage_code ON run_logs(stage_code);
CREATE INDEX IF NOT EXISTS idx_runlogs_cleared_at ON run_logs(cleared_at);

-- ========== Triggers/Functions ==========

CREATE OR REPLACE FUNCTION set_updated_at()
RETURNS TRIGGER AS $$
BEGIN
  NEW.updated_at := now();
  RETURN NEW;
END; $$ LANGUAGE plpgsql;

DROP TRIGGER IF EXISTS trg_progress_updated_at ON user_stage_progress;
CREATE TRIGGER trg_progress_updated_at
BEFORE UPDATE ON user_stage_progress
FOR EACH ROW EXECUTE FUNCTION set_updated_at();

CREATE OR REPLACE FUNCTION init_user_progress()
RETURNS TRIGGER AS $$
BEGIN
  INSERT INTO user_stage_progress (user_id, stage_id, unlocked, cleared)
  SELECT NEW.user_id, s.stage_id, (s.code = 'A1') AS unlocked, FALSE
  FROM stages s;
  RETURN NEW;
END; $$ LANGUAGE plpgsql;

DROP TRIGGER IF EXISTS trg_init_user_progress ON users;
CREATE TRIGGER trg_init_user_progress
AFTER INSERT ON users
FOR EACH ROW EXECUTE FUNCTION init_user_progress();

CREATE OR REPLACE FUNCTION unlock_next_stage()
RETURNS TRIGGER AS $$
DECLARE
  next_id INT;
BEGIN
  IF NEW.cleared = TRUE AND (OLD.cleared IS DISTINCT FROM TRUE) THEN
    SELECT next_stage_id INTO next_id
    FROM stages WHERE stage_id = NEW.stage_id;

    IF next_id IS NOT NULL THEN
      UPDATE user_stage_progress
      SET unlocked = TRUE
      WHERE user_id = NEW.user_id AND stage_id = next_id;
    END IF;
  END IF;
  RETURN NEW;
END; $$ LANGUAGE plpgsql;

DROP TRIGGER IF EXISTS trg_unlock_next ON user_stage_progress;
CREATE TRIGGER trg_unlock_next
AFTER UPDATE OF cleared ON user_stage_progress
FOR EACH ROW EXECUTE FUNCTION unlock_next_stage();

-- ========== Seed stages (A1..A5, B1..B5, ... E1..E5) ==========

DO $$
DECLARE
  g TEXT;
  i INT;
BEGIN
  -- Insert codes
  FOREACH g IN ARRAY ARRAY['A','B','C','D','E'] LOOP
    FOR i IN 1..5 LOOP
      INSERT INTO stages(code) VALUES (g || i)
      ON CONFLICT (code) DO NOTHING;
    END LOOP;
  END LOOP;

  -- Link next_stage_id within each group
  FOREACH g IN ARRAY ARRAY['A','B','C','D','E'] LOOP
    FOR i IN 1..4 LOOP
      UPDATE stages s
      SET next_stage_id = s2.stage_id
      FROM stages s2
      WHERE s.code = (g || i) AND s2.code = (g || (i+1));
    END LOOP;
  END LOOP;
END $$;

-- Reset to superuser if this was run by postgres
RESET ROLE;