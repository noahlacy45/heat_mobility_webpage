"""
Mobility program generator — scoring, ranking, and day-assignment logic.

Given a row from mobility_assessments, this module:
  1. Scores every raw test value against mobility_test_reference
     (Bad=25, Average=50, Good=75, Elite=100 -- direction-agnostic,
     since the reference bands already encode which way is "better").
  2. Averages test scores into a 0-100 score per muscle group.
  3. Ranks the 4 groups (rank 1 = lowest score = most restricted).
  4. Assigns Primary/Secondary groups to Day 1-3 using the confirmed rule:
        Day 1: Primary = Rank 1, Secondary = Rank 2
        Day 2: Primary = Rank 1, Secondary = Rank 3
        Day 3: Primary = Rank 2, Secondary = Rank 4
  5. Selects drills per day/slot from mobility_drill_defaults, avoiding
     repeating the same drill NAME anywhere else in the program (the
     drill library has a few same-name drills under different groups/ids,
     so dedup is done on name, not drill_id).

Does not include PDF rendering -- see the (upcoming) program_pdf module.
"""

from collections import defaultdict
import random

CATEGORY_SCORE = {"Bad": 25, "Average": 50, "Good": 75, "Elite": 100}

# assessment table column -> reference test_name.
# Columns without _left/_right are single values already.
TEST_COLUMN_MAP = {
    "cervical_rotation_left": "Cervical Rotation",
    "cervical_rotation_right": "Cervical Rotation",
    "cervical_flexion": "Cervical Flexion",
    "cervical_extension": "Cervical Extension",

    "shoulder_flexion_left": "Shoulder Flexion",
    "shoulder_flexion_right": "Shoulder Flexion",
    "shoulder_abduction_left": "Shoulder ABD",
    "shoulder_abduction_right": "Shoulder ABD",
    "shoulder_er_left": "Shoulder ER",
    "shoulder_er_right": "Shoulder ER",
    "shoulder_ir_left": "Shoulder IR",
    "shoulder_ir_right": "Shoulder IR",

    "elbow_flexion_left": "Elbow Flexion",
    "elbow_flexion_right": "Elbow Flexion",
    "elbow_extension_left": "Elbow Extension",
    "elbow_extension_right": "Elbow Extension",

    "wrist_flexion_left": "Wrist Flexion",
    "wrist_flexion_right": "Wrist Flexion",
    "wrist_extension_left": "Wrist Extension",
    "wrist_extension_right": "Wrist Extension",
    "forearm_supination_left": "Forearm Supination",
    "forearm_supination_right": "Forearm Supination",
    "forearm_pronation_left": "Forearm Pronation",
    "forearm_pronation_right": "Forearm Pronation",
    "ulnar_deviation_left": "Ulnar Deviation",
    "ulnar_deviation_right": "Ulnar Deviation",
    "radial_deviation_left": "Radial Deviation",
    "radial_deviation_right": "Radial Deviation",

    "hip_flexion_left": "Hip Flexion",
    "hip_flexion_right": "Hip Flexion",
    "hip_extension_left": "Hip Extension",
    "hip_extension_right": "Hip Extension",
    "hip_abduction_left": "Hip ABD",
    "hip_abduction_right": "Hip ABD",
    "hip_adduction_left": "Hip ADD",
    "hip_adduction_right": "Hip ADD",
    "hip_ir_left": "Hip IR",
    "hip_ir_right": "Hip IR",
    "hip_er_left": "Hip ER",
    "hip_er_right": "Hip ER",

    "thomas_test_errors": "Thomas Test",
    "cossack_squat_errors": "Cossack Squat",
    "overhead_squat_errors": "Overhead Squat Assessment",

    "ankle_dorsiflexion_left": "Ankle Dorsiflexion (cm)",
    "ankle_dorsiflexion_right": "Ankle Dorsiflexion (cm)",
    "ankle_inversion_left": "Ankle Inversion",
    "ankle_inversion_right": "Ankle Inversion",
    "ankle_eversion_left": "Ankle Eversion",
    "ankle_eversion_right": "Ankle Eversion",

    "lumbar_locked_rotation_left": "Lumbar Locked T-Spine Rotation",
    "lumbar_locked_rotation_right": "Lumbar Locked T-Spine Rotation",

    "ybt_ant": "YBT Ant",
    "ybt_pm": "YBT PostMed",
    "ybt_pl": "YBT PostLat",

    "bess_left_errors": "Dynamic BESS Test",
    "bess_right_errors": "Dynamic BESS Test",
}

DAY_PLAN = [
    {"day": 1, "primary_rank": 1, "secondary_rank": 2},
    {"day": 2, "primary_rank": 1, "secondary_rank": 3},
    {"day": 3, "primary_rank": 2, "secondary_rank": 4},
]

DRILLS_PER_SLOT = {"Primary": 5, "Secondary": 3}


def load_test_reference(cur):
    """Returns {test_name: [(min, max, category), ...]} from the DB."""
    cur.execute("SELECT test_name, min_value, max_value, category FROM mobility_test_reference")
    ref = defaultdict(list)
    for test_name, min_v, max_v, category in cur.fetchall():
        ref[test_name].append((float(min_v), float(max_v), category))
    return ref


def load_group_ids(cur):
    cur.execute("SELECT id, name FROM mobility_muscle_groups")
    return {name: gid for gid, name in cur.fetchall()}


def load_test_group_map(cur):
    """test_name -> group_id, derived from mobility_test_reference rows."""
    cur.execute("SELECT DISTINCT test_name, group_id FROM mobility_test_reference")
    return dict(cur.fetchall())


def category_for_value(test_name, value, ref):
    """Finds which Bad/Average/Good/Elite band a raw value falls into."""
    if value is None:
        return None
    for min_v, max_v, category in ref.get(test_name, []):
        if min_v <= value <= max_v:
            return category
    return None  # value outside all defined bands -- worth logging/flagging


def score_assessment(assessment_row: dict, cur):
    """
    assessment_row: dict of column_name -> raw value, e.g. one row from
    mobility_assessments (as returned by a DictCursor, or built manually).

    Returns:
        group_scores: {group_name: score_0_to_100}
        ranked_groups: [group_name, ...] ordered worst (rank 1) to best (rank 4)
        unscored: [column_name, ...] columns that had a value but no matching
                  reference band (worth investigating, not silently dropped)
    """
    ref = load_test_reference(cur)
    test_group_map = load_test_group_map(cur)
    group_ids = load_group_ids(cur)
    id_to_group = {v: k for k, v in group_ids.items()}

    # test_name -> list of category scores (averaging L/R together per test)
    test_scores = defaultdict(list)
    unscored = []

    for column, test_name in TEST_COLUMN_MAP.items():
        value = assessment_row.get(column)
        if value is None:
            continue
        category = category_for_value(test_name, float(value), ref)
        if category is None:
            unscored.append(column)
            continue
        test_scores[test_name].append(CATEGORY_SCORE[category])

    # Average test scores within each group
    group_totals = defaultdict(list)
    for test_name, scores in test_scores.items():
        group_id = test_group_map.get(test_name)
        if group_id is None:
            continue
        group_name = id_to_group[group_id]
        group_totals[group_name].append(sum(scores) / len(scores))

    group_scores = {
        group: round(sum(scores) / len(scores), 1)
        for group, scores in group_totals.items()
    }

    ranked_groups = sorted(group_scores, key=lambda g: group_scores[g])  # worst first

    return group_scores, ranked_groups, unscored


def assign_days(ranked_groups):
    """
    ranked_groups: list of 4 group names, worst (rank 1) to best (rank 4).
    Returns [{day, slot, group_name}, ...] for all 6 day/slot blocks.
    """
    if len(ranked_groups) != 4:
        raise ValueError(f"Expected 4 ranked groups, got {len(ranked_groups)}")

    blocks = []
    for plan in DAY_PLAN:
        primary_group = ranked_groups[plan["primary_rank"] - 1]
        secondary_group = ranked_groups[plan["secondary_rank"] - 1]
        blocks.append({"day": plan["day"], "slot": "Primary", "group_name": primary_group})
        blocks.append({"day": plan["day"], "slot": "Secondary", "group_name": secondary_group})
    return blocks


def select_drills_for_program(blocks, cur):
    """
    blocks: output of assign_days().
    Returns [{day, slot, drill_id, drill_name, sets, reps, notes, video_link}, ...]
    Avoids repeating the same drill NAME anywhere else in the program.
    """
    cur.execute("""
        SELECT d.id, d.drill_name, d.video_link, m.group_id, m.default_sets, m.default_reps, m.notes
        FROM drills d
        JOIN mobility_drill_defaults m ON m.drill_id = d.id
        WHERE d.active = TRUE
    """)
    all_drills = cur.fetchall()

    group_ids = {}
    cur.execute("SELECT id, name FROM mobility_muscle_groups")
    for gid, name in cur.fetchall():
        group_ids[name] = gid

    by_group = defaultdict(list)
    for drill_id, drill_name, video_link, group_id, sets, reps, notes in all_drills:
        by_group[group_id].append(
            {"id": drill_id, "name": drill_name, "video_link": video_link,
             "sets": sets, "reps": reps, "notes": notes}
        )
    for pool in by_group.values():
        random.shuffle(pool)

    used_names = set()
    program = []

    for block in blocks:
        group_id = group_ids[block["group_name"]]
        count = DRILLS_PER_SLOT[block["slot"]]
        pool = by_group.get(group_id, [])

        chosen = []
        for drill in pool:
            if len(chosen) >= count:
                break
            if drill["name"] in used_names:
                continue
            chosen.append(drill)
            used_names.add(drill["name"])

        for drill in chosen:
            program.append({
                "day": block["day"],
                "slot": block["slot"],
                "drill_id": drill["id"],
                "drill_name": drill["name"],
                "sets": drill["sets"],
                "reps": drill["reps"],
                "notes": drill["notes"],
                "video_link": drill["video_link"],
            })

    return program


def generate_program(assessment_row: dict, cur):
    """Full pipeline: assessment row -> scored, ranked, day-assigned program."""
    group_scores, ranked_groups, unscored = score_assessment(assessment_row, cur)
    if unscored:
        print(f"WARNING: {len(unscored)} values had no matching reference band: {unscored}")

    blocks = assign_days(ranked_groups)
    program = select_drills_for_program(blocks, cur)

    return {
        "group_scores": group_scores,
        "ranked_groups": ranked_groups,
        "program": program,
    }
