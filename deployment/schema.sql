-- ============================================================
-- HEAT Mobility Assessment & Drill Library — Schema
-- ============================================================

-- Muscle / body-region groups used by the mobility program logic
CREATE TABLE mobility_muscle_groups (
    id INT AUTO_INCREMENT PRIMARY KEY,
    name VARCHAR(50) UNIQUE NOT NULL
);

-- Reference thresholds: raw test value -> Bad/Average/Good/Elite, per test
CREATE TABLE mobility_test_reference (
    id INT AUTO_INCREMENT PRIMARY KEY,
    test_name VARCHAR(60) NOT NULL,
    group_id INT NOT NULL,
    min_value DECIMAL(6,1) NOT NULL,
    max_value DECIMAL(6,1) NOT NULL,
    category ENUM('Bad','Average','Good','Elite') NOT NULL,
    FOREIGN KEY (group_id) REFERENCES mobility_muscle_groups(id),
    INDEX idx_test_name (test_name)
);

-- Core identity for every drill, regardless of discipline/context
CREATE TABLE drills (
    id INT AUTO_INCREMENT PRIMARY KEY,
    drill_name VARCHAR(150) NOT NULL,
    video_link VARCHAR(255),
    video_title VARCHAR(255),
    video_description TEXT,
    active BOOLEAN DEFAULT TRUE,
    created_by VARCHAR(100),
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP
);

-- Flexible tag dimensions (category, player_type, and room for more later)
CREATE TABLE tags (
    id INT AUTO_INCREMENT PRIMARY KEY,
    tag_type ENUM('category','player_type') NOT NULL,
    name VARCHAR(50) NOT NULL,
    UNIQUE KEY uq_tag (tag_type, name)
);

-- Many-to-many: a drill can carry any number of tags
CREATE TABLE drill_tags (
    drill_id INT NOT NULL,
    tag_id INT NOT NULL,
    PRIMARY KEY (drill_id, tag_id),
    FOREIGN KEY (drill_id) REFERENCES drills(id) ON DELETE CASCADE,
    FOREIGN KEY (tag_id) REFERENCES tags(id) ON DELETE CASCADE
);

-- Mobility-specific extension: only for drills used in auto-programming
CREATE TABLE mobility_drill_defaults (
    drill_id INT PRIMARY KEY,
    group_id INT NOT NULL,
    default_sets VARCHAR(20),
    default_reps VARCHAR(30),
    notes VARCHAR(120),
    FOREIGN KEY (drill_id) REFERENCES drills(id) ON DELETE CASCADE,
    FOREIGN KEY (group_id) REFERENCES mobility_muscle_groups(id)
);

-- Raw assessment submissions from the webpage
CREATE TABLE mobility_assessments (
    id INT AUTO_INCREMENT PRIMARY KEY,
    athlete_name VARCHAR(100) NOT NULL,
    assessment_type ENUM('Initial Assessment','Retest') NOT NULL,
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,

    cervical_rotation_left DECIMAL(5,1), cervical_rotation_right DECIMAL(5,1),
    cervical_flexion DECIMAL(5,1), cervical_extension DECIMAL(5,1),

    shoulder_flexion_left DECIMAL(5,1), shoulder_flexion_right DECIMAL(5,1),
    shoulder_abduction_left DECIMAL(5,1), shoulder_abduction_right DECIMAL(5,1),
    shoulder_er_left DECIMAL(5,1), shoulder_er_right DECIMAL(5,1),
    shoulder_ir_left DECIMAL(5,1), shoulder_ir_right DECIMAL(5,1),
    shoulder_extension_left DECIMAL(5,1), shoulder_extension_right DECIMAL(5,1),

    elbow_flexion_left DECIMAL(5,1), elbow_flexion_right DECIMAL(5,1),
    elbow_extension_left DECIMAL(5,1), elbow_extension_right DECIMAL(5,1),

    wrist_flexion_left DECIMAL(5,1), wrist_flexion_right DECIMAL(5,1),
    wrist_extension_left DECIMAL(5,1), wrist_extension_right DECIMAL(5,1),
    forearm_supination_left DECIMAL(5,1), forearm_supination_right DECIMAL(5,1),
    forearm_pronation_left DECIMAL(5,1), forearm_pronation_right DECIMAL(5,1),
    ulnar_deviation_left DECIMAL(5,1), ulnar_deviation_right DECIMAL(5,1),
    radial_deviation_left DECIMAL(5,1), radial_deviation_right DECIMAL(5,1),

    hip_flexion_left DECIMAL(5,1), hip_flexion_right DECIMAL(5,1),
    hip_extension_left DECIMAL(5,1), hip_extension_right DECIMAL(5,1),
    hip_abduction_left DECIMAL(5,1), hip_abduction_right DECIMAL(5,1),
    hip_adduction_left DECIMAL(5,1), hip_adduction_right DECIMAL(5,1),
    hip_ir_left DECIMAL(5,1), hip_ir_right DECIMAL(5,1),
    hip_er_left DECIMAL(5,1), hip_er_right DECIMAL(5,1),

    thomas_test_errors TINYINT,
    cossack_squat_errors TINYINT,
    overhead_squat_errors TINYINT,

    ankle_dorsiflexion_left DECIMAL(5,1), ankle_dorsiflexion_right DECIMAL(5,1),
    ankle_inversion_left DECIMAL(5,1), ankle_inversion_right DECIMAL(5,1),
    ankle_eversion_left DECIMAL(5,1), ankle_eversion_right DECIMAL(5,1),

    lumbar_locked_rotation_left DECIMAL(5,1), lumbar_locked_rotation_right DECIMAL(5,1),

    ybt_ant DECIMAL(5,1), ybt_pm DECIMAL(5,1), ybt_pl DECIMAL(5,1),

    bess_left_errors TINYINT,
    bess_right_errors TINYINT,

    program_pdf_gcs_path VARCHAR(255),

    INDEX idx_athlete (athlete_name)
);

-- What was actually prescribed for a given assessment (historical record)
CREATE TABLE mobility_program_drills (
    id INT AUTO_INCREMENT PRIMARY KEY,
    assessment_id INT NOT NULL,
    day TINYINT NOT NULL,
    slot ENUM('Primary','Secondary') NOT NULL,
    drill_id INT NOT NULL,
    sets_prescribed VARCHAR(20),
    reps_prescribed VARCHAR(30),
    FOREIGN KEY (assessment_id) REFERENCES mobility_assessments(id) ON DELETE CASCADE,
    FOREIGN KEY (drill_id) REFERENCES drills(id)
);
