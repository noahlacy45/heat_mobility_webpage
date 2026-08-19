-- ============================================================
-- Migration: level of play tracking
--   - player_directory.current_level_of_play: fast "what level are
--     they at right now" lookup, usable by any system, not just mobility
--   - player_level_history: full timestamped log of every level change,
--     for "when did they move from X to Y" analysis
-- mobility_assessments.level_of_play (added in migration 001) is left
-- as-is -- it's an immutable per-assessment snapshot, separate from this.
-- ============================================================

ALTER TABLE player_directory
    ADD COLUMN current_level_of_play ENUM('HS JV','HS Varsity','College','Pro') NULL
        AFTER date_of_birth;

CREATE TABLE player_level_history (
    id INT AUTO_INCREMENT PRIMARY KEY,
    player_id INT NOT NULL,
    level_of_play ENUM('HS JV','HS Varsity','College','Pro') NOT NULL,
    effective_date DATE NOT NULL,
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (player_id) REFERENCES player_directory(Player_Id)
);

CREATE INDEX idx_player_level_history_player ON player_level_history(player_id);
