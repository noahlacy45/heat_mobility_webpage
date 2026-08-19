import logging
import os
from datetime import date, datetime
from io import BytesIO

import mysql.connector
from dotenv import load_dotenv
from flask import Flask, jsonify, request, send_file
from flask_cors import CORS
from google.cloud import storage

# Loads backend/.env for local development if it exists. In production
# (Cloud Run), there's no .env file, so this is a harmless no-op -- real
# env vars are set via deploy.sh instead.
load_dotenv()

import field_defs
import mobility_program_generator as gen
import program_pdf
import secrets_config

app = Flask(__name__)

# Enable CORS for the frontend, which is hosted separately (Firebase Hosting
# or a GCS static bucket) and calls this API cross-origin.
# Update origins to your specific frontend domain once deployed.
CORS(app, resources={
    r"/api/*": {
        "origins": ["*"],  # Change to your specific domain in production
        "methods": ["GET", "POST", "OPTIONS"],
        "allow_headers": ["Content-Type"],
    }
})

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Not a secret -- just the bucket name, set as a plain Cloud Run env var.
GCS_BUCKET_NAME = os.environ.get("GCS_BUCKET_NAME")


def get_db_connection():
    # Fetched fresh (not cached at import time) so a rotated secret is
    # picked up without a redeploy -- see secrets_config.get_secret().
    return mysql.connector.connect(**secrets_config.get_db_config())


def _parse_float(value):
    if value is None or value == "":
        return None
    return float(value)


@app.route("/health", methods=["GET"])
def health_check():
    """Health check endpoint for Cloud Run."""
    try:
        conn = get_db_connection()
        conn.close()
        return jsonify({"status": "healthy", "database": "connected"}), 200
    except Exception as e:
        logger.error(f"Health check failed: {str(e)}")
        return jsonify({"status": "unhealthy", "error": str(e)}), 503


@app.route("/api/athletes", methods=["GET"])
def list_athletes():
    conn = get_db_connection()
    cur = conn.cursor()
    try:
        cur.execute(
            "SELECT Player_Id, hittrax_UserName, date_of_birth, current_level_of_play "
            "FROM player_directory WHERE hittrax_UserName IS NOT NULL ORDER BY hittrax_UserName"
        )
        athletes = [
            {
                "id": row[0],
                "name": row[1],
                "date_of_birth": row[2].isoformat() if row[2] else None,
                "current_level_of_play": row[3],
            }
            for row in cur.fetchall()
        ]
        return jsonify(athletes)
    finally:
        cur.close()
        conn.close()


@app.route("/api/field-groups", methods=["GET"])
def get_field_groups():
    """
    Lets the frontend build its joint/test inputs from the same source of
    truth the backend uses (field_defs.FIELD_GROUPS), instead of keeping a
    second hardcoded copy in the static HTML. Column names are resolved
    explicitly server-side (see field_defs.resolved_field_groups) so the
    frontend never has to guess a DB column name from a naming convention.
    """
    return jsonify(field_defs.resolved_field_groups())


@app.route("/api/field-help", methods=["GET"])
def get_field_help():
    """Per-group descriptions and How-To video links, from the original form."""
    return jsonify(field_defs.GROUP_HELP)


@app.route("/api/test-reference", methods=["GET"])
def get_test_reference():
    """
    Bad/Average/Good/Elite threshold bands per field, read live from
    mobility_test_reference (not duplicated/hardcoded here) so the legend
    shown on the form always matches the actual scoring thresholds in the DB.
    Keyed by field base name (e.g. "shoulder_flexion"), matching FIELD_GROUPS.
    """
    conn = get_db_connection()
    cur = conn.cursor()
    try:
        cur.execute("SELECT test_name, min_value, max_value, category FROM mobility_test_reference")
        rows = cur.fetchall()
    finally:
        cur.close()
        conn.close()

    category_order = {"Bad": 0, "Average": 1, "Good": 2, "Elite": 3}
    by_test_name = {}
    for test_name, min_v, max_v, category in rows:
        by_test_name.setdefault(test_name, []).append({
            "category": category,
            "min": float(min_v),
            "max": float(max_v),
        })
    for bands in by_test_name.values():
        bands.sort(key=lambda b: category_order.get(b["category"], 99))

    # Map each field's real column(s) -> test_name via field_defs, not by
    # guessing from column-name suffixes -- this correctly handles fields
    # with explicit column overrides (e.g. Dynamic BESS).
    base_to_test_name = {}
    for base, cols in field_defs.field_column_map().items():
        test_name = gen.TEST_COLUMN_MAP.get(cols[0])
        if test_name:
            base_to_test_name[base] = test_name

    result = {
        base: by_test_name[test_name]
        for base, test_name in base_to_test_name.items()
        if test_name in by_test_name
    }
    return jsonify(result)


@app.route("/api/submit", methods=["POST", "OPTIONS"])
def submit_assessment():
    if request.method == "OPTIONS":
        return "", 204

    data = request.form

    assessment_type = data.get("assessment_type")
    level_of_play = data.get("level_of_play")
    if assessment_type not in ("Initial Assessment", "Retest"):
        return jsonify({"error": "Invalid assessment_type"}), 400

    conn = get_db_connection()
    cur = conn.cursor()
    try:
        # --- Resolve the athlete ---
        athlete_selection = data.get("existing_athlete_id")
        if not athlete_selection:
            return jsonify({"error": "Select an athlete or choose 'Add new athlete'"}), 400

        if athlete_selection == "__new__":
            athlete_name = data.get("athlete_name", "").strip()
            dob = data.get("date_of_birth") or None
            if not athlete_name:
                return jsonify({"error": "Athlete name is required"}), 400
            if not dob:
                return jsonify({"error": "Date of birth is required for a new athlete"}), 400

            # norm_name must match how sp_refresh_player_directory computes it
            # (LOWER(TRIM(name))), or the daily sync won't recognize this
            # athlete later and will create a duplicate row instead of
            # enriching this one with their HitTrax/Blast/VALD IDs.
            norm_name = athlete_name.strip().lower()

            cur.execute(
                "INSERT INTO player_directory (hittrax_UserName, norm_name, date_of_birth) "
                "VALUES (%s, %s, %s)",
                (athlete_name, norm_name, dob),
            )
            player_id = cur.lastrowid
        else:
            player_id = int(athlete_selection)
            cur.execute(
                "SELECT hittrax_UserName, date_of_birth FROM player_directory WHERE Player_Id = %s",
                (player_id,),
            )
            row = cur.fetchone()
            if row is None:
                return jsonify({"error": "Selected athlete not found"}), 400
            athlete_name, existing_dob = row

            if existing_dob is None:
                dob = data.get("date_of_birth") or None
                if dob:
                    cur.execute(
                        "UPDATE player_directory SET date_of_birth = %s WHERE Player_Id = %s",
                        (dob, player_id),
                    )

        height_in = _parse_float(data.get("height_in"))
        weight_lb = _parse_float(data.get("weight_lb"))
        if height_in is None or weight_lb is None:
            return jsonify({"error": "Height and weight are required"}), 400

        # --- Keep current_level_of_play and its history in sync ---
        cur.execute(
            "SELECT current_level_of_play FROM player_directory WHERE Player_Id = %s",
            (player_id,),
        )
        current_level = cur.fetchone()[0]
        if level_of_play != current_level:
            cur.execute(
                "UPDATE player_directory SET current_level_of_play = %s WHERE Player_Id = %s",
                (level_of_play, player_id),
            )
            cur.execute(
                """INSERT INTO player_level_history (player_id, level_of_play, effective_date)
                   VALUES (%s, %s, %s)""",
                (player_id, level_of_play, date.today()),
            )

        # --- Collect the raw joint/test values from the form ---
        assessment_row = {}
        for col in field_defs.assessment_columns():
            assessment_row[col] = _parse_float(data.get(col))

        # --- Insert the assessment row ---
        columns = [
            "player_id", "assessment_type", "level_of_play", "height_in", "weight_lb"
        ] + field_defs.assessment_columns()
        placeholders = ", ".join(["%s"] * len(columns))
        values = [player_id, assessment_type, level_of_play, height_in, weight_lb] + [
            assessment_row[c] for c in field_defs.assessment_columns()
        ]
        cur.execute(
            f"INSERT INTO mobility_assessments ({', '.join(columns)}) VALUES ({placeholders})",
            values,
        )
        assessment_id = cur.lastrowid

        # --- Score, rank, and build the program ---
        result = gen.generate_program(assessment_row, cur)

        for drill in result["program"]:
            cur.execute(
                """INSERT INTO mobility_program_drills
                   (assessment_id, day, slot, drill_id, sets_prescribed, reps_prescribed)
                   VALUES (%s, %s, %s, %s, %s, %s)""",
                (assessment_id, drill["day"], drill["slot"], drill["drill_id"], drill["sets"], drill["reps"]),
            )

        # --- Render the PDF ---
        pdf_bytes = program_pdf.render_program_pdf(
            athlete_name=athlete_name,
            assessment_type=assessment_type,
            level_of_play=level_of_play,
            assessment_date=date.today(),
            group_scores=result["group_scores"],
            ranked_groups=result["ranked_groups"],
            program=result["program"],
        )

        # --- Upload to GCS for historical reference ---
        safe_name = athlete_name.replace(" ", "_")
        gcs_path = f"programs/{date.today().year}/{safe_name}_{datetime.now().strftime('%Y-%m-%d_%H%M%S')}.pdf"

        storage_client = storage.Client()
        bucket = storage_client.bucket(GCS_BUCKET_NAME)
        blob = bucket.blob(gcs_path)
        blob.upload_from_string(pdf_bytes, content_type="application/pdf")

        cur.execute(
            "UPDATE mobility_assessments SET program_pdf_gcs_path = %s WHERE id = %s",
            (gcs_path, assessment_id),
        )

        conn.commit()

    except Exception:
        conn.rollback()
        raise
    finally:
        cur.close()
        conn.close()

    download_name = f"{athlete_name.replace(' ', '_')}_mobility_program.pdf"
    return send_file(
        BytesIO(pdf_bytes),
        mimetype="application/pdf",
        as_attachment=True,
        download_name=download_name,
    )


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=int(os.environ.get("PORT", 8080)), debug=False)
