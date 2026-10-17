# UDAY — Render Deployment Guide

UDAY is a mental-wellness companion with a Streamlit interface, a FastAPI API, Neon PostgreSQL storage, and Gemini-generated replies. This guide explains how to deploy the project to Render with the `render.yaml` Blueprint in this repository.

> **Important:** UDAY is a prototype, not a medical device, clinician, diagnosis, treatment, or emergency service. The included Blueprint uses Render Free web services for a demo or evaluation. Render says Free instances are not for production use; they may sleep and their local files are ephemeral. Do not use this setup for a public clinical service or rely on it for urgent support. Read Render's current [Free instance limits](https://render.com/docs/free).

## What gets deployed

The Blueprint creates two Render services:

| Service | What it runs | Example URL |
| --- | --- | --- |
| `uday-api` | FastAPI authentication, chat, screening, memory, and data endpoints | `https://<api-service>.onrender.com` |
| `uday-ui` | The Streamlit app people use | `https://<ui-service>.onrender.com` |

The API stores data in Neon PostgreSQL. Render wires the UI's `UDAY_API_URL` to the API's public URL. The API's start command checks its required settings and initializes the schema before starting Uvicorn; Render checks `/health` after deploy.

## What you need

Before starting, have:

- The UDAY project in a GitHub repository, with `render.yaml` at its root.
- A Render account connected to GitHub.
- A Neon PostgreSQL project and its connection URI.
- A Gemini API key.

### Check the Gemini model setting

The local default in `config.py` is `gemini-3.5-flash`; the Render Blueprint in `render.yaml` overrides it with `gemini-3.6-flash`. Google's current documentation marks 3.5 deprecated and automatically routes it to 3.6; 3.6 is listed as a stable model. If you choose another model, update `GEMINI_MODEL` in `render.yaml` and, if you want the same model locally, `DEFAULT_MODEL_NAME` in `config.py`; then commit and push the change before deploying. A model must be enabled for the Google account associated with your key. See Google's [current stable model list](https://ai.google.dev/gemini-api/docs/models), [Gemini 3.6 Flash status](https://ai.google.dev/gemini-api/docs/models/gemini-3.6-flash), and [deprecation information](https://ai.google.dev/gemini-api/docs/deprecations).

## Step 1 — Prepare and push the repository

1. Confirm `render.yaml` is in the project root alongside `api.py`, `streamlit_app.py`, and `requirements.txt`.
2. Confirm your `.env` file is not committed. The project's `.gitignore` excludes `.env`, `.neon`, virtual environments, and local database files.
3. Do not put passwords, API keys, database URLs, or JWT secrets in source files, `render.yaml`, README text, screenshots, or public GitHub issues.
4. Commit and push the project to GitHub. Render deploys the branch you connect in the next step.

If you want to check the project locally first, see [Local checks](#local-checks).

## Step 2 — Get the Neon connection URI

1. Open the Neon project in the Neon Console.
2. Open the connection details for the branch and database UDAY should use.
3. Choose the pooled connection option and copy the complete PostgreSQL URI. Neon describes how to find it in [Connect from any application](https://neon.com/docs/connect/connect-from-any-app).
4. Treat the URI as a password: do not paste it into source control or a public message.

Use the Neon production branch for the live Render service. For testing schema changes with real-like data, use a separate Neon branch/database. UDAY initializes and upgrades tables on API startup, so do not point a test deploy at a database whose contents you cannot risk changing.

## Step 3 — Get a Gemini API key

1. Create or select a Google project with Gemini API access.
2. Create/copy its Gemini API key using Google's developer tooling.
3. Confirm the model selected in `GEMINI_MODEL` is available to that key.
4. Keep the key private. It belongs in Render's API service environment only.

Chat text and relevant, user-reviewed memory facts are sent to Gemini to generate a reply. Profile fields such as the user's name, age, gender, and focus area are not included in the Gemini prompt. Review Google's current API terms and data handling before using real personal data.

## Step 4 — Create the Render Blueprint

1. Sign in to the [Render Dashboard](https://dashboard.render.com/).
2. Select **New** → **Blueprint**.
3. Connect the GitHub repository containing UDAY.
4. Select the branch you pushed in Step 1.
5. Confirm the Blueprint path is `render.yaml` (the default when it is at the repository root).
6. Review the resources Render plans to create. You should see `uday-api` and `uday-ui`, both Python web services.
7. During initial setup, enter the prompted secret values:
   - `DATABASE_URL`: the Neon pooled PostgreSQL URI from Step 2.
   - `GEMINI_API_KEY`: the key from Step 3.
8. Review the Blueprint and select **Deploy Blueprint**.

Render's [Blueprint guide](https://render.com/docs/infrastructure-as-code) explains connecting a repository. Its [Blueprint YAML reference](https://render.com/docs/blueprint-spec) describes generated secrets, prompted secrets, and service references.

The Blueprint automatically:

- Generates `JWT_SECRET_KEY` for the API.
- Sets `UDAY_REQUIRE_DATABASE=1`, so the hosted API will not silently fall back to ephemeral SQLite.
- Sets `GEMINI_MODEL=gemini-3.6-flash` (the current value in `render.yaml`).
- Installs the NLTK VADER lexicon during the API build.
- Checks required settings and initializes the database before starting the API.
- Connects the UI's `UDAY_API_URL` to the API's `RENDER_EXTERNAL_URL`.

> **If these Render services already exist:** Render prompts for `sync: false` secrets during initial Blueprint creation. For an existing Blueprint, add or replace those values on the relevant service's **Environment** page, then redeploy. Do not add the secret values to YAML.

## Step 5 — Verify the Render environment settings

Open **uday-api** → **Environment** in the Render Dashboard and confirm:

| Variable | Expected value |
| --- | --- |
| `DATABASE_URL` | The full Neon pooled PostgreSQL URI |
| `GEMINI_API_KEY` | Your Gemini API key |
| `JWT_SECRET_KEY` | A generated, private random value of at least 32 characters |
| `UDAY_REQUIRE_DATABASE` | `1` |
| `GEMINI_MODEL` | `gemini-3.6-flash` in the current Blueprint; use a model ID available to your Gemini API key |

Open **uday-ui** → **Environment** and confirm `UDAY_API_URL` refers to the API's public Render URL. The Blueprint sets this service reference for you. Do not put the Neon URI or Gemini API key on the UI service.

If a required value is missing or Neon cannot be reached, the API's start or health check will fail rather than switching to local SQLite.

## Step 6 — Wait for deployment and open the app

1. In Render, open **Events** or **Deploys** and wait for both services to show a successful deployment.
2. Open the API URL followed by `/health`, for example:

   ```text
   https://<api-service>.onrender.com/health
   ```

   A healthy API returns:

   ```json
   {"status":"ok"}
   ```

3. To view the FastAPI interactive docs, open the API URL followed by `/docs`:

   ```text
   https://<api-service>.onrender.com/docs
   ```

4. In the Render Dashboard, open **uday-ui** and select its public URL. This is the link to share for the web interface.

## Step 7 — Test with a disposable account

Use a test account and non-sensitive test messages:

1. Create an account. Registration is restricted to adults aged 18 or older, requires a password of at least 12 characters, and requires acceptance of the data-use notice.
2. Sign in and send a short test message. Confirm the app receives a response.
3. Add a saved memory, edit it, and delete it.
4. Check the sidebar data controls: export data, clear chat history, and delete mood scores.
5. If you want to check account deletion, use only the disposable test account. Account deletion permanently deletes that account and its linked data.
6. Recheck the API `/health` URL.

The API returns 429 when a user exceeds a request limit: 30 chats per account per minute, 10 login attempts per IP/account per 15 minutes, and 5 registrations per IP per hour. Do not use real mental-health information during initial testing.

## Troubleshooting

| Symptom | What to check |
| --- | --- |
| API deploy fails before it starts | Check API logs and confirm `DATABASE_URL`, `GEMINI_API_KEY`, and generated `JWT_SECRET_KEY` exist. Confirm `UDAY_REQUIRE_DATABASE` is `1`. |
| `/health` fails with a database error | Re-copy the Neon pooled URI, verify its branch/database and credentials, and retain all query parameters. Avoid extra quotes or spaces. |
| Streamlit opens but cannot reach the API | Confirm the UI's `UDAY_API_URL` points to the API's public URL, not the UI URL or a private host. Then redeploy the UI service. |
| Chat says the AI service is unavailable | Check API logs; verify the Gemini key, model availability, API access, quota, and billing/usage limits for the Google project. |
| Registration returns HTTP 422 | Check valid email, age 18+, non-empty profile fields, password length of at least 12, and privacy consent. |
| Login returns HTTP 401 | Check the email and password. Profiles created before API password support may not have a password hash and cannot log in until a password-recovery/migration flow is provided. |
| Initial load is slow after inactivity | Render Free web services can sleep after 15 minutes without inbound traffic; waking may take about a minute. See the current [Free instance limits](https://render.com/docs/free). |

If deployment fails, inspect the first error in the relevant service's **Logs**. Never include a full database URI or API key in a public support request.

## Database setup and existing data

The API creates missing UDAY tables and adds the privacy-consent fields to an existing `users` table. It also creates tables for per-user screening state and rate-limit buckets. These schema upgrades are additive; they do not drop the existing UDAY tables. Do not delete your Neon project or branch to troubleshoot a failed deploy. Correct the connection/configuration issue and redeploy.

Sign-in uses OAuth2 password credentials and JWT bearer tokens. Each access token expires after 15 minutes, after which the user must sign in again. Changing `JWT_SECRET_KEY` invalidates all existing access tokens.

Render's filesystem is ephemeral, so hosted SQLite would lose data on restarts, redeploys, or sleep. This Blueprint requires PostgreSQL and uses Neon. Per account, UDAY retains at most the latest 500 chat messages; up to 80 messages may be included as Gemini context. New mood entries store a VADER score without a text excerpt. Older mood rows from a previous version may still contain their old excerpts. The app lets each user export data, clear their transcript, remove mood scores, edit/delete memories, or delete their account.

## Environment variables reference

| Variable | Service | Purpose |
| --- | --- | --- |
| `DATABASE_URL` | API | Neon PostgreSQL URI; required on Render |
| `GEMINI_API_KEY` | API | Authenticates Gemini generation calls |
| `GEMINI_MODEL` | API | Gemini model identifier |
| `JWT_SECRET_KEY` | API | Signs access tokens; private random value, minimum 32 characters |
| `UDAY_REQUIRE_DATABASE` | API | `1` on Render to require persistent PostgreSQL |
| `UDAY_API_URL` | UI | FastAPI base URL; linked automatically by the Blueprint |

For local development, create a `.env` file in the project folder. Never commit that file. The values below are placeholders; replace them with your own credentials and a newly generated JWT key:

```dotenv
GEMINI_API_KEY=your_gemini_key
GEMINI_MODEL=gemini-3.5-flash
JWT_SECRET_KEY=generate-a-random-secret-of-at-least-32-characters
DATABASE_URL=postgresql://user:password@host/database?sslmode=require
```

Generate a local JWT secret with:

```bash
python -c "import secrets; print(secrets.token_urlsafe(48))"
```

If `DATABASE_URL` is omitted locally, UDAY uses SQLite at `data/uday.db`. The hosted Blueprint requires Neon PostgreSQL.

## Local checks

Install project dependencies and the VADER lexicon:

```bash
python -m pip install -r requirements.txt
python -m nltk.downloader vader_lexicon
```

Run the deployment-focused checks. They use temporary SQLite databases and do not connect to Neon:

```bash
python -m unittest discover -s tests -v
```

To start the API and UI locally, use two terminals:

```bash
uvicorn api:app --reload
```

```bash
streamlit run streamlit_app.py
```

The local UI calls `http://127.0.0.1:8000` by default. Set `UDAY_API_URL` if your API runs elsewhere. FastAPI docs are at `http://127.0.0.1:8000/docs`.

## Privacy and safety

UDAY stores profile details, Argon2 password hashes, chat history, user-reviewed memory facts, and VADER sentiment scores in the configured database. The chat text and relevant reviewed memory facts are sent to Google Gemini to generate replies. Review the in-app data-use notice and Google's current data terms before using real personal information.

VADER scores are basic language heuristics, not clinical measurements. GAD-7 output is a screening result, not a diagnosis. The crisis phrase detector is a lightweight safeguard that can miss or misread context; it is not a risk assessment. Review crisis resources for each country and have qualified clinical, privacy, and security reviewers assess UDAY before making it publicly available for mental-health support. In an emergency, contact local emergency services rather than relying on this app.

## Project files

- `render.yaml` — Render Blueprint for the API and Streamlit services
- `api.py` — FastAPI routes, input validation, JWT authentication, screening, and data controls
- `streamlit_app.py` — Streamlit UI, sign-in, chat, memories, and privacy controls
- `database.py` — SQLAlchemy schema, SQLite/PostgreSQL connections, and additive upgrades
- `chatbot.py` — Gemini chat, VADER mood scoring, and conversational context
- `memory.py` — user-reviewed memories and local relevance ranking
- `crisis.py` — crisis phrase safeguard and response
- `screener.py` — GAD-7 screening flow
- `users.py` — profile persistence
- `config.py` — environment configuration and model selection
- `tests/test_deployment.py` — deployment-focused API tests
- `evaluate_personalization.py` — synthetic memory-personalization comparison
