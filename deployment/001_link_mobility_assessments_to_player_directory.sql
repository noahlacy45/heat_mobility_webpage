-- ============================================================
-- Migration: link mobility_assessments to the EXISTING
-- player_directory table (shared with HitTrax/Blast/VALD),
-- and add level_of_play / per-visit height & weight.
--
-- player_directory itself is NOT modified -- it already has
-- date_of_birth, and its height/weight columns are intentionally
-- left alone (see chat notes: those are a different, static
-- snapshot and not what the mobility app writes to).
-- ============================================================

ALTER TABLE mobility_assessments
    ADD COLUMN player_id INT AFTER id,
    ADD COLUMN level_of_play ENUM('HS JV','HS Varsity','College','Pro') AFTER assessment_type,
    ADD COLUMN height_in DECIMAL(4,1) AFTER level_of_play,
    ADD COLUMN weight_lb DECIMAL(5,1) AFTER height_in,
    ADD CONSTRAINT fk_assessment_player FOREIGN KEY (player_id) REFERENCES player_directory(Player_Id);

ALTER TABLE mobility_assessments DROP COLUMN athlete_name;

CREATE INDEX idx_mobility_assessments_player ON mobility_assessments(player_id);
