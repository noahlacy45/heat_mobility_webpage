# HEAT Mobility Assessment

Replaces the Google Form + Apps Script program generator with a Flask API
(Cloud Run) and a static frontend, following the same pattern as the
Wellness Questionnaire project: separate `backend/` and `frontend/`,
secrets via Secret Manager (DB credentials only), plain env vars for
non-sensitive config.

## Structure

```
backend/     Flask API -- deployed to Cloud Run
frontend/    Static HTML -- deployed separately (Firebase Hosting / GCS bucket)
deployment/  Schema, migrations, and deploy scripts
```

## backend/

- `main.py` — routes: `/health`, `/api/field-groups`, `/api/athletes`, `/api/submit`
- `secrets_config.py` — fetches `DB_HOST`, `DB_USER`, `DB_PASS`, `DB_NAME`
  from Secret Manager at runtime (not via Cloud Run's `--set-secrets` env
  var injection). Falls back to plain env vars if they're set, so local
  testing doesn't need real GCP credentials. Not cached, so a rotated
  secret is picked up without a redeploy.
- `field_defs.py` — source of truth for the ~58 joint/test fields (frontend
  fetches this via `/api/field-groups` instead of keeping its own copy)
- `mobility_program_generator.py` — scoring, ranking, day assignment, drill selection
- `program_pdf.py` — PDF rendering (fpdf2)
- `GCS_BUCKET_NAME` is always a plain env var — not sensitive, not a secret

## frontend/

- `index.html` — single static file, styled to match the Wellness
  Questionnaire's branding. Calls the backend via `fetch()`, cross-origin
  (CORS is enabled on the backend for this).
- **Before deploying**: update the `API_URL` constant near the top of the
  `<script>` block to your deployed Cloud Run URL.
- Same asset (`RBI_HEAT_Logo.svg`) as the wellness project.

## deployment/

- `schema.sql` — full original mobility schema (already run if you built
  the DB tables earlier)
- `001_link_mobility_assessments_to_player_directory.sql` — links
  `mobility_assessments` to your EXISTING `player_directory` table (shared
  with HitTrax/Blast/VALD); adds `level_of_play`, `height_in`, `weight_lb`
- `002_level_of_play_history.sql` — adds `current_level_of_play` to
  `player_directory` and a `player_level_history` table
- `setup-secrets.sh` — one-time: creates DB_USER/DB_PASS/DB_HOST/DB_NAME
  secrets in Secret Manager and grants Cloud Run access
- `deploy.sh` — builds and deploys `backend/` to Cloud Run

## One-time setup

1. Run the two migrations (schema.sql should already be applied):
   ```
   mysql -h <host> -u <user> -p <database> < deployment/001_link_mobility_assessments_to_player_directory.sql
   mysql -h <host> -u <user> -p <database> < deployment/002_level_of_play_history.sql
   ```

2. Create a GCS bucket for the generated PDFs:
   ```
   gsutil mb -l us-east4 gs://heat-mobility-programs
   ```

3. Run `deployment/setup-secrets.sh` (one time) to create the DB secrets
   and grant the Cloud Run service account `roles/secretmanager.secretAccessor`
   — required since the app calls Secret Manager directly at runtime.

## Deploy

```
cd deployment
./deploy.sh
```

`deploy.sh` sets `GCP_PROJECT_ID` as a plain env var (so `secrets_config.py`
knows which project to query) — it does NOT pass DB credentials via
`--set-secrets`, since the app fetches them itself.

Then:
1. Copy the printed Cloud Run URL into `frontend/index.html`'s `API_URL`.
2. Deploy `frontend/` the same way you deployed the wellness questionnaire's
   frontend (Firebase Hosting or a GCS static bucket).
3. Grant the Cloud Run service account `roles/storage.objectCreator` on the
   GCS bucket (see the command `deploy.sh` prints at the end).

## Local test run

`secrets_config.py` uses plain env vars directly when they're set, so you
don't need real GCP Secret Manager access for local testing:

```
cd backend
pip install -r requirements.txt --break-system-packages
export DB_HOST=... DB_USER=... DB_PASS=... DB_NAME=... GCS_BUCKET_NAME=...
export GOOGLE_APPLICATION_CREDENTIALS=/path/to/service-account.json   # for local GCS auth
python main.py
```
Then open `frontend/index.html` locally with `API_URL` pointed at
`http://localhost:8080/api`.

## Known open items

- **`player_directory` is shared infrastructure**, synced daily by
  `sp_refresh_player_directory` from HitTrax/Blast/VALD (matches by ID
  first, then `norm_name`). New athletes created by this app populate
  `norm_name` for that reason — keep that in sync if the procedure's
  matching logic ever changes.
- **No duplicate-name protection** beyond what the sync procedure provides.
- **Level of play has two homes on purpose**:
  `mobility_assessments.level_of_play` is an immutable per-assessment
  snapshot; `player_directory.current_level_of_play` +
  `player_level_history` track the athlete's durable level over time.
- **CORS is wide open (`origins: ["*"]`)** in `main.py` — tighten to your
  actual frontend domain once deployed, same as the wellness questionnaire's
  backend comment suggests.
