"""
Single source of truth for the mobility assessment's joint/test fields.
Used by main.py (via /api/field-groups, /api/field-help, /api/test-reference)
to drive the frontend's inputs and help content, and to know which
mobility_assessments columns to read from submitted data.

FIELD_GROUPS: (group_label, [(field_base, display_label, paired, unit), ...])
  paired=True  -> renders/reads {field_base}_left and {field_base}_right,
                  UNLESS a 5th tuple element is present:
                  (field_base, display_label, paired, unit, [left_col, right_col])
                  which gives the exact DB column names to use instead --
                  needed when a field's real columns don't follow the
                  {base}_left/{base}_right pattern (e.g. Dynamic BESS uses
                  bess_left_errors/bess_right_errors, not bess_left/bess_right,
                  and we don't want to rename those DB columns).
  paired=False -> renders/reads {field_base} as a single column

GROUP_HELP: keyed by group label, from the original Google Form --
  "description": section-level Purpose text
  "videos": [{"label", "url", "fields": [field_base, ...]}, ...]
    Each video lists which field(s) it demonstrates, in the order they
    should render directly beneath it (video -> its test(s) -> next video).
    A field not covered by any video (e.g. Hip IR/ER, Shoulder Extension --
    no dedicated video in the original form) renders at the end of the
    section with no video above it.
  "tests": {field_base: {"description": ..., "errors": [...] (optional)}}
    per-test Setup/Execution/Common-Errors text. "errors" only appears for
    the count-based movement screens (Thomas, Cossack, Overhead, BESS).
"""

FIELD_GROUPS = [
    ("Cervical", [
        ("cervical_rotation", "Cervical Rotation", True, "deg"),
        ("cervical_flexion", "Cervical Flexion", False, "deg"),
        ("cervical_extension", "Cervical Extension", False, "deg"),
    ]),
    ("Wrist & Forearm", [
        ("wrist_flexion", "Wrist Flexion", True, "deg"),
        ("wrist_extension", "Wrist Extension", True, "deg"),
        ("forearm_supination", "Forearm Supination", True, "deg"),
        ("forearm_pronation", "Forearm Pronation", True, "deg"),
        ("ulnar_deviation", "Ulnar Deviation", True, "deg"),
        ("radial_deviation", "Radial Deviation", True, "deg"),
    ]),
    ("Elbow", [
        ("elbow_flexion", "Elbow Flexion", True, "deg"),
        ("elbow_extension", "Elbow Extension", True, "deg"),
    ]),
    ("Ankle", [
        ("ankle_dorsiflexion", "Ankle Dorsiflexion", True, "cm"),
        ("ankle_inversion", "Ankle Inversion", True, "deg"),
        ("ankle_eversion", "Ankle Eversion", True, "deg"),
    ]),
    ("Shoulder", [
        ("shoulder_flexion", "Shoulder Flexion", True, "deg"),
        ("shoulder_abduction", "Shoulder Abduction", True, "deg"),
        ("shoulder_er", "Shoulder External Rotation", True, "deg"),
        ("shoulder_ir", "Shoulder Internal Rotation", True, "deg"),
    ]),
    ("Hip", [
        ("hip_flexion", "Hip Flexion", True, "deg"),
        ("hip_extension", "Hip Extension", True, "deg"),
        ("hip_abduction", "Hip Abduction", True, "deg"),
        ("hip_adduction", "Hip Adduction", True, "deg"),
        ("hip_ir", "Hip Internal Rotation", True, "deg"),
        ("hip_er", "Hip External Rotation", True, "deg"),
    ]),
    ("Lumbar / T-Spine", [
        ("lumbar_locked_rotation", "Lumbar Locked Rotation", True, "deg"),
    ]),
    ("Y-Balance Test", [
        ("ybt_ant", "YBT Anterior", False, "cm"),
        ("ybt_pm", "YBT Posteromedial", False, "cm"),
        ("ybt_pl", "YBT Posterolateral", False, "cm"),
    ]),
    ("Movement Screens (error counts)", [
        ("thomas_test_errors", "Thomas Test", False, "errors"),
        ("cossack_squat_errors", "Cossack Squat", False, "errors"),
        ("overhead_squat_errors", "Overhead Squat", False, "errors"),
    ]),
    ("Dynamic BESS (errors)", [
        ("bess", "Dynamic BESS Test", True, "errors", ["bess_left_errors", "bess_right_errors"]),
    ]),
]


def _yt(video_id):
    return f"https://www.youtube.com/embed/{video_id}"


GROUP_HELP = {
    "Cervical": {
        "description": (
            "Assess neck mobility and control relevant to posture, rotation, and "
            "head positioning."
        ),
        "videos": [
            {"label": "Cervical Rotation", "url": _yt("0aQmSb8AiOA"), "fields": ["cervical_rotation"]},
            {"label": "Cervical Flexion & Extension", "url": _yt("zec_n8kwLps"),
             "fields": ["cervical_flexion", "cervical_extension"]},
        ],
        "tests": {
            "cervical_rotation": {
                "description": (
                    "Athlete seated. Goniometer axis at the crown of the head, both "
                    "arms aligned with the nose at the start. Athlete looks over one "
                    "shoulder while the moving arm follows the nose. Compare L vs R "
                    "to identify asymmetries or cervical tightness."
                ),
            },
            "cervical_flexion": {
                "description": (
                    "Axis through the ear, stationary arm vertical, moving arm "
                    "aligned with the tip of the nose. Athlete slowly brings chin "
                    "to chest."
                ),
            },
            "cervical_extension": {
                "description": "Same setup as flexion; athlete lifts chin up toward the sky.",
            },
        },
    },
    "Wrist & Forearm": {
        "description": (
            "Identify mobility restrictions influencing grip and swing/throw "
            "positions across all major wrist and forearm planes."
        ),
        "videos": [
            {"label": "Wrist & Forearm ROM", "url": _yt("zULpOzzUhdw"),
             "fields": ["wrist_flexion", "wrist_extension", "forearm_supination",
                        "forearm_pronation", "ulnar_deviation", "radial_deviation"]},
        ],
        "tests": {
            "wrist_flexion": {"description": "Bring palm toward forearm (avoid counting finger bend)."},
            "wrist_extension": {"description": "Bring back of hand toward forearm."},
            "forearm_supination": {"description": "Rotate forearm so palm faces the sky."},
            "forearm_pronation": {"description": "Rotate forearm so palm faces down."},
            "ulnar_deviation": {"description": "Move wrist toward pinky side."},
            "radial_deviation": {"description": "Move wrist toward thumb side."},
        },
    },
    "Elbow": {
        "description": "Measure joint integrity and tissue limitation at the elbow.",
        "videos": [
            {"label": "Elbow Flexion & Extension", "url": _yt("9skpF5rS7wk"),
             "fields": ["elbow_flexion", "elbow_extension"]},
        ],
        "tests": {
            "elbow_flexion": {
                "description": (
                    "Bend the elbow, bringing the hand toward the shoulder. Soft "
                    "tissue from the biceps may limit full flexion -- normal without "
                    "pain. Typical range ~140-150 deg."
                ),
            },
            "elbow_extension": {
                "description": (
                    "From a bent position, straighten the arm completely. Full "
                    "extension is 0 deg; minor hyperextension (up to 10 deg) can be "
                    "natural. Lack of extension or pain at end range may indicate "
                    "restriction."
                ),
            },
        },
    },
    "Ankle": {
        "description": "Evaluate functional ankle mobility related to squatting, cutting, and deceleration.",
        "videos": [
            {"label": "Ankle Dorsiflexion (Knee-to-Wall)", "url": _yt("IPGtEpWY7WE"),
             "fields": ["ankle_dorsiflexion"]},
            {"label": "Ankle Inversion & Eversion", "url": _yt("3dW7QGOMZak"),
             "fields": ["ankle_inversion", "ankle_eversion"]},
        ],
        "tests": {
            "ankle_dorsiflexion": {
                "description": (
                    "Knee-to-Wall test: athlete kneels facing a wall, one foot flat, "
                    "knee bent 90 deg. Move knee toward wall keeping heel down; "
                    "measure big-toe-to-wall distance in cm (~10-12 cm normal). "
                    "Errors: heel lifting, excessive foot rotation, loss of control."
                ),
            },
            "ankle_inversion": {
                "description": (
                    "Seated, ankle relaxed off the table edge. Turn the sole of the "
                    "foot inward toward the midline. Normal ~40-45 deg. Errors: "
                    "tension in the foot, compensating with hip rotation, or "
                    "rotating the whole leg instead of isolating the ankle."
                ),
            },
            "ankle_eversion": {
                "description": (
                    "Same setup as inversion; turn the sole outward, away from the "
                    "midline. Normal ~15-20 deg."
                ),
            },
        },
    },
    "Shoulder": {
        "description": (
            "Evaluate available motion of the shoulder joint to identify "
            "limitations or asymmetries that can influence throwing mechanics, "
            "swing patterns, and overhead control. Measure bilaterally; if full "
            "ROM is achieved easily supine, retest standing."
        ),
        "videos": [
            {"label": "Shoulder Flexion, Abduction, IR & ER", "url": _yt("krvCSLsXaoY"),
             "fields": ["shoulder_flexion", "shoulder_abduction", "shoulder_er", "shoulder_ir"]},
        ],
        "tests": {
            "shoulder_flexion": {
                "description": (
                    "Supine. Axis at the head of the humerus; stationary arm along "
                    "the torso; moving arm at the lateral epicondyle. Raise the arm "
                    "overhead, elbow straight, fist in front of the face. Normal "
                    "~180 deg. Errors: elbow bending, arching the back/lifting hips, "
                    "shoulder rotating forward."
                ),
            },
            "shoulder_abduction": {
                "description": (
                    "Supine. Axis at the head of the humerus (front); stationary arm "
                    "perpendicular to the shoulders; moving arm at the lateral "
                    "epicondyle. Raise the arm out to the side in a smooth arc, "
                    "elbow straight. Normal ~180 deg. Errors: early external "
                    "rotation, shoulder elevation/scapular lift, elbow bending or "
                    "trunk rotation."
                ),
            },
            "shoulder_er": {
                "description": (
                    "Supine, arm abducted 90 deg, elbow bent 90 deg. Rotate the hand "
                    "backward (back of hand toward the ground). Normal ~90 deg. "
                    "Errors: lifting/rolling the shoulder forward, arching the lower "
                    "back, elbow drifting out of alignment."
                ),
            },
            "shoulder_ir": {
                "description": (
                    "Same setup as External Rotation. Rotate the hand forward (palm "
                    "toward the ground). Normal ~70-80 deg. Same error checks as ER."
                ),
            },
        },
    },
    "Hip": {
        "description": (
            "Assess hip mobility and control across flexion/extension, "
            "abduction/adduction, and internal/external rotation -- key for "
            "sprinting, stride length, hip hinge mechanics, and rotational power."
        ),
        "videos": [
            {"label": "Hip Flexion & Extension", "url": _yt("Vs0ogo-8NwM"),
             "fields": ["hip_flexion", "hip_extension"]},
            {"label": "Hip Abduction & Adduction", "url": _yt("cTexv30hcpg"),
             "fields": ["hip_abduction", "hip_adduction"]},
            {"label": "Hip Internal & External Rotation", "url": _yt("0Wt6PajwacY"),
             "fields": ["hip_ir", "hip_er"]},
        ],
        "tests": {
            "hip_flexion": {
                "description": (
                    "Supine. Axis at the greater trochanter; stationary arm along "
                    "the torso; moving arm at the lateral knee. Squeeze the quad, "
                    "dorsiflex the foot, lift the leg straight up. Normal ~80-90 "
                    "deg. Errors: knee bend, hip rotation, lifting the lower back "
                    "off the table."
                ),
            },
            "hip_extension": {
                "description": (
                    "Prone. Axis at the greater trochanter; stationary arm along "
                    "the torso; moving arm at the lateral epicondyle of the knee. "
                    "Lift the straight leg toward the ceiling without arching the "
                    "back. Normal ~10-20 deg. Errors: lumbar arching, hip rotation, "
                    "bending the knee."
                ),
            },
            "hip_abduction": {
                "description": (
                    "Supine, legs straight. Axis at the ASIS; stationary arm across "
                    "the pelvis to the opposite ASIS; moving arm at the center of "
                    "the kneecap. Move the leg outward without external rotation. "
                    "Normal ~40-50 deg. Errors: rotating the hips, bending the knee, "
                    "lifting the lower back."
                ),
            },
            "hip_adduction": {
                "description": (
                    "Same setup as abduction; move the leg inward toward the "
                    "midline, opposite leg relaxed. Normal ~20-30 deg."
                ),
            },
            "hip_ir": {
                "description": (
                    "Seated at table edge, knees bent, legs hanging freely. Axis at "
                    "the front of the patella; stationary arm perpendicular to the "
                    "ground; moving arm along the shin. Foot moves outward, thigh "
                    "stays flat. Errors: lifting the hip, leaning, losing contact "
                    "with the table."
                ),
            },
            "hip_er": {
                "description": (
                    "Same setup as Internal Rotation; foot moves inward, heel moves "
                    "outward."
                ),
            },
        },
    },
    "Lumbar / T-Spine": {
        "description": "Evaluate thoracic spine rotation while limiting lumbar contribution.",
        "videos": [
            {"label": "Lumbar Locked Rotation", "url": _yt("GDZ9WPeVPI8"),
             "fields": ["lumbar_locked_rotation"]},
        ],
        "tests": {
            "lumbar_locked_rotation": {
                "description": (
                    "Child's pose, forearms down. Rotate the upper body outward, "
                    "elbow toward the ceiling, knees/hips stay grounded -- movement "
                    "should come from the thoracic spine, not the lower back. "
                    "Errors: lifting the hips, rotating the lower back, leading "
                    "with the elbow instead of the shoulder."
                ),
            },
        },
    },
    "Y-Balance Test": {
        "description": (
            "Assesses single-leg stability, control, and asymmetry in three "
            "directions (anterior, posterolateral, posteromedial)."
        ),
        "videos": [
            {"label": "Y-Balance Test", "url": _yt("xUu2amce4xk"),
             "fields": ["ybt_ant", "ybt_pm", "ybt_pl"],
             "image": "ybt_directions.png"},
        ],
        "tests": {
            "ybt_ant": {
                "description": (
                    "Anterior (ANT): Reaching straight forward directly in front "
                    "of the stance foot, testing quadriceps strength, ankle "
                    "dorsiflexion, and balance."
                ),
            },
            "ybt_pm": {
                "description": (
                    "Posteromedial (PM): Reaching behind and diagonal toward the "
                    "midline of the body behind the stance leg, assessing hip "
                    "extension, external rotation, and multi-planar stability."
                ),
            },
            "ybt_pl": {
                "description": (
                    "Posterolateral (PL): Reaching behind and diagonal away from "
                    "the midline of the body, challenging hip stability, "
                    "abduction control, and lateral ankle control."
                ),
            },
        },
    },
    "Movement Screens (error counts)": {
        "description": (
            "Dynamic, whole-body screens. Enter the total count of errors observed "
            "for each -- checklists below show exactly what to watch for."
        ),
        "videos": [
            {"label": "Thomas Test", "url": _yt("vlopnoKQbzY"), "fields": ["thomas_test_errors"]},
            {"label": "Cossack Squat", "url": _yt("w_LgmGyrqSI"), "fields": ["cossack_squat_errors"]},
            {"label": "Overhead Squat", "url": _yt("9G4haycerDU"), "fields": ["overhead_squat_errors"]},
        ],
        "tests": {
            "thomas_test_errors": {
                "description": (
                    "Identifies hip flexor and quad tightness. Athlete lifts one "
                    "knee to chest and lays back; opposite leg should stay relaxed "
                    "and flat. Thigh lifting off the table indicates hip flexor "
                    "tightness; lower leg extending indicates quad tightness."
                ),
                "errors": [
                    "Unable to lift knee to chest and lay back on the table unassisted",
                    "Pulls hip into too much flexion, creating posterior pelvic tilt that pulls the thigh off the table",
                    "Low back and sacrum are not flat on the table",
                    "Bringing both hips into flexion, allowing excessive posterior pelvic tilt",
                    "Improper pelvic stabilization, allowing anterior tilt that masks true hip flexor length",
                ],
            },
            "cossack_squat_errors": {
                "description": (
                    "Feet wider than shoulder width, toes out ~45 deg, hands "
                    "interlocked at chest. Shift weight to one side, heel of the "
                    "working leg stays down, opposite leg rotates so toes point up. "
                    "3 controlled reps per side."
                ),
                "errors": [
                    "Unable to reach heel to butt",
                    "Hands touch down in front",
                    "Unable to get out of the bottom of the squat",
                    "Opposite toe doesn't lift off and rotate (lack of proprioception)",
                    "Excessive trunk flexion",
                ],
            },
            "overhead_squat_errors": {
                "description": (
                    "Feet just wider than shoulder width, arms overhead in line "
                    "with the ears holding a PVC pipe. 5 deep squats, observed from "
                    "front and side."
                ),
                "errors": [
                    "Arms don't stay extended overhead (even with ears)",
                    "Knees don't track over toes",
                    "Hip crease doesn't reach knee level",
                    "Excessive trunk flexion",
                    "5 reps couldn't be completed",
                    "Feet point farther out than starting position",
                    "Loss of balance",
                    "Heels lift off",
                ],
            },
        },
    },
    "Dynamic BESS (errors)": {
        "description": (
            "Evaluates balance, proprioception, and cognitive response under "
            "movement challenge. Athlete balances one-legged on a foam pad, "
            "catches a tossed ball, responds to a directional verbal cue, then "
            "returns the ball. 10 reps per leg. Errors can repeat within a side -- "
            "e.g. 5 ball drops on the left is entered as 5."
        ),
        "videos": [
            {"label": "Dynamic BESS Test", "url": _yt("LjQwRGNqJMQ"),
             "fields": ["bess"]},
        ],
        "tests": {
            "bess": {
                "description": (
                    "Count of errors observed per leg. Errors can repeat within a "
                    "side -- e.g. 5 ball drops on the left is entered as 5."
                ),
                "errors": [
                    "Ball drop",
                    "Incorrect response to command (look right/left/up/down)",
                    "Step, stumble, or fall",
                    "Moving hip into >30 degrees abduction",
                    "Lifting forefoot or heel",
                    "Remaining out of test position >5 seconds",
                ],
            },
        },
    },
}


def field_columns(entry):
    """
    Given a FIELD_GROUPS field entry (4- or 5-tuple), returns the list of
    real DB column names: [left, right] if paired, [col] if not.
    """
    base, label, paired, unit = entry[0], entry[1], entry[2], entry[3]
    override = entry[4] if len(entry) == 5 else None
    if paired:
        return list(override) if override else [f"{base}_left", f"{base}_right"]
    return [override[0]] if override else [base]


def field_column_map():
    """Returns {field_base: [column_name, ...]} across all groups."""
    result = {}
    for _, fields in FIELD_GROUPS:
        for entry in fields:
            result[entry[0]] = field_columns(entry)
    return result


def resolved_field_groups():
    """
    FIELD_GROUPS with every field's real column name(s) resolved explicitly,
    so the frontend never has to guess a column name from the base + a
    naming convention. Paired fields become 6 elements (..., left_col,
    right_col); single fields become 5 elements (..., col).
    """
    resolved = []
    for group_label, fields in FIELD_GROUPS:
        resolved_fields = []
        for entry in fields:
            base, label, paired, unit = entry[0], entry[1], entry[2], entry[3]
            cols = field_columns(entry)
            if paired:
                resolved_fields.append([base, label, paired, unit, cols[0], cols[1]])
            else:
                resolved_fields.append([base, label, paired, unit, cols[0]])
        resolved.append([group_label, resolved_fields])
    return resolved


def assessment_columns():
    """Returns the full list of mobility_assessments column names this form fills."""
    cols = []
    for _, fields in FIELD_GROUPS:
        for entry in fields:
            cols.extend(field_columns(entry))
    return cols
