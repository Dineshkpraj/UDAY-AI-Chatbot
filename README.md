# UDAY

**A personal wellness companion for reflection, supportive conversation, and guided self-check-ins.**

UDAY combines a Streamlit web interface with a FastAPI service. It uses Google Gemini to generate conversational responses, PostgreSQL or SQLite for user data, VADER for lightweight mood signals, and a guided GAD-7 screening flow.

> **Wellness and safety notice:** UDAY is an educational prototype. It is not medical care, a diagnosis, treatment, or an emergency service. The GAD-7 flow is a screening aid, not a diagnosis. The keyword-based crisis safeguard can miss context and must not be relied on for risk assessment. If someone is in immediate danger, contact local emergency services or a qualified crisis service.

## Contents

- [Features](#features)
- [How the application is structured](#how-the-application-is-structured)
- [Technology](#technology)
- [Run locally](#run-locally)
- [Configuration](#configuration)
- [Deploy to Render](#deploy-to-render)
- [Data and privacy](#data-and-privacy)
- [Verification](#verification)
- [Project layout](#project-layout)
- [Known limitations](#known-limitations)

## Features

- **Supportive chat:** Streamlit chat interface backed by a FastAPI API and Gemini text generation.
- **Accounts and sessions:** Validated registration, Argon2 password hashing, OAuth2 password flow, and JWT access tokens that expire after 15 minutes.
- **Screening when wanted:** Users can start or restart the optional GAD-7 screening from the sidebar at any time. UDAY can also offer it after messages containing selected anxiety or stress terms. New users may receive a one-time invitation.
- **User-controlled memories:** Users can review, edit, add, and delete saved memory facts used for personalization.
- **Mood signals:** VADER creates heuristic sentiment scores. Scores are not clinical measurements.
- **Privacy controls:** Users can export account data, clear chat history, delete mood scores, manage memories, or delete their account and linked records.
- **Persistent storage:** Neon PostgreSQL is intended for hosted deployments; SQLite is available for local development.
- **API documentation:** FastAPI interactive documentation is available at `/docs`.

## How the application is structured

```text
Browser
  └── Streamlit UI (streamlit_app.py)
        └── FastAPI API (api.py)
              ├── Google Gemini (chat generation)
              ├── SQLAlchemy → Neon PostgreSQL / local SQLite
              ├── VADER (heuristic sentiment scoring)
              └── GAD-7 screening and crisis phrase safeguard
```

The Render Blueprint provisions two web services: `uday-ui` and `uday-api`. The UI reaches the API through `UDAY_API_URL`. User accounts, screening state, chat history, memories, and mood scores are stored by the API in the configured database.

## Technology

| Area | Technology |
| --- | --- |
| Web interface | Streamlit |
| API and input validation | FastAPI, Pydantic |
| Authentication | OAuth2 password flow, JWT, Argon2 password hashing |
| Database access | SQLAlchemy |
| Hosted database | Neon PostgreSQL |
| Local database option | SQLite |
| Generative responses | Google Gemini API (`google-genai`) |
| Sentiment heuristic | NLTK VADER |
| Hosting configuration | Render Blueprint (`render.yaml`) |

## Run locally

### 1. Prerequisites

- Python 3.11 or newer
- A Gemini API key
- A PostgreSQL database URL for persistent local data, or use SQLite for a local-only run

### 2. Create an environment and install dependencies

PowerShell:

```powershell
py -3 -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install --upgrade pip
python -m pip install -r requirements.txt
python -m nltk.downloader vader_lexicon
```

If PowerShell blocks virtual-environment activation, use the Python executable directly at `.venv\Scripts\python.exe` and `.venv\Scripts\streamlit.exe`.

### 3. Configure environment variables

Create a `.env` file in the project root. Keep it private and never commit it.

```dotenv
GEMINI_API_KEY=replace-with-your-gemini-key
GEMINI_MODEL=gemini-3.6-flash
JWT_SECRET_KEY=replace-with-a-random-secret-of-at-least-32-characters
# Optional for local development. If omitted, UDAY uses data/uday.db.
DATABASE_URL=postgresql://USER:PASSWORD@HOST/DATABASE?sslmode=require
```

Generate a strong local JWT secret with:

```powershell
python -c "import secrets; print(secrets.token_urlsafe(48))"
```

Do not copy production credentials into source files, screenshots, or public issues. The model name above is the configured default; confirm that the model is available to the Google account associated with your API key.

### 4. Start the services

Open two PowerShell terminals from the project directory and activate `.venv` in each.

Terminal 1 — API:

```powershell
uvicorn api:app --reload
```

Terminal 2 — UI:

```powershell
streamlit run streamlit_app.py
```

Open the Streamlit URL printed in the terminal (usually `http://localhost:8501`). The API health check is at `http://127.0.0.1:8000/health`; interactive API documentation is at `http://127.0.0.1:8000/docs`.

If the API runs at a different address, set `UDAY_API_URL` for the Streamlit process, for example:

```powershell
$env:UDAY_API_URL = "http://127.0.0.1:8000"
```

## Configuration

| Variable | Required | Used by | Description |
| --- | --- | --- | --- |
| `GEMINI_API_KEY` | Yes for chat | API | Credential for Gemini generation. |
| `GEMINI_MODEL` | No | API | Gemini model identifier; defaults to the value in `config.py`. |
| `JWT_SECRET_KEY` | Yes for deployment | API | Secret used to sign JWT access tokens; use a private random value of at least 32 characters. |
| `DATABASE_URL` | Yes on Render | API | SQLAlchemy connection URL for PostgreSQL. When omitted locally, SQLite is used at `data/uday.db`. |
| `UDAY_REQUIRE_DATABASE` | Set to `1` on Render | API | Makes startup require a database URL, Gemini key, and strong JWT secret. |
| `UDAY_API_URL` | Yes for hosted UI | UI | Public base URL of the FastAPI service. Render wires this automatically in the Blueprint. |

For PostgreSQL, use the connection URI supplied by Neon and retain its SSL and connection parameters. Use a separate database or Neon branch for development and testing. UDAY initializes its tables at startup and applies additive schema updates; still back up data before changing a production database.

## Deploy to Render

The repository includes a `render.yaml` Blueprint defining the `uday-api` and `uday-ui` web services.

### Before deploying

1. Push the project, including `render.yaml`, to the GitHub repository and branch Render should deploy.
2. Create a Neon PostgreSQL project and copy its connection URI. Use the pooled connection for the hosted application when available.
3. Create a Gemini API key and confirm the configured model is available to that key.
4. Check that `.env`, database files, virtual environments, and API keys are not tracked by Git.

### Create the Render services

1. In the Render Dashboard, choose **New** → **Blueprint**.
2. Connect the GitHub repository containing UDAY and select the deployment branch.
3. Confirm Render detects the root `render.yaml`.
4. Provide the prompted `DATABASE_URL` and `GEMINI_API_KEY` values. The Blueprint generates `JWT_SECRET_KEY`.
5. Review the two services and deploy the Blueprint.
6. Wait for both services to finish building. Open the `uday-api` service and check `/health`, then open the public URL for `uday-ui`.

### Required service settings

The API service needs:

- `DATABASE_URL` — Neon PostgreSQL connection URI
- `GEMINI_API_KEY` — Gemini credential
- `JWT_SECRET_KEY` — private generated secret (at least 32 characters)
- `UDAY_REQUIRE_DATABASE=1`
- `GEMINI_MODEL` — model enabled for the configured Gemini key

The UI service needs `UDAY_API_URL` set to the API service’s public Render URL. The Blueprint configures this service reference. Keep the database URI and Gemini key on the API service only.

After a successful deployment, verify:

```text
https://<your-api-service>.onrender.com/health
https://<your-api-service>.onrender.com/docs
```

The health endpoint should return `{"status":"ok"}`. Then create a disposable account through the UI and test chat, screening, memory controls, and data export. Avoid real personal or health information while evaluating the prototype.

### Update an existing deployment

Commit and push changes to the branch connected to Render. Render will start a deployment automatically if auto-deploy is enabled. Review the build and runtime logs in the Render Dashboard. Do not use `git push --force` to work around a rejected push; reconcile the branch histories or push to the repository and branch that Render actually tracks.

### Render Free plan notes

The included Blueprint uses Render Free services. Free services may sleep after inactivity, can take time to wake, and have ephemeral local filesystems. UDAY therefore requires PostgreSQL for hosted data. Review Render’s current [Free instance limits](https://render.com/docs/free) before relying on this configuration. The free setup is for demos and evaluation, not a production mental-health service.

## Data and privacy

- UDAY stores user profile details, password hashes, chat history, screening state, user-managed memory facts, and VADER mood scores in its database.
- Chat text and relevant saved memory facts are sent to Gemini to produce a reply. Profile fields such as name and age are not included in the Gemini prompt by the current implementation.
- UDAY retains at most 500 recent chat messages per account. A smaller, recent portion may be included as model context.
- New mood records store the sentiment score without the message text excerpt.
- Users can export data, clear chat history, delete mood scores, edit or delete saved memories, and permanently delete their account and linked records.
- Access tokens expire after 15 minutes. Rotating `JWT_SECRET_KEY` invalidates existing tokens.

Review Google’s current API terms and data practices before sending personal information. Do not use UDAY for urgent support or sensitive clinical decision-making.

## Verification

Run the deployment-focused API tests from the project root:

```powershell
python -m unittest discover -s tests -v
```

The tests use temporary SQLite databases and do not require a Neon connection. They still require the packages listed in `requirements.txt` to be installed in the active Python environment. To check Python syntax without starting the services:

```powershell
python -m compileall -q api.py streamlit_app.py tests
```

## Project layout

```text
api.py                     FastAPI routes, validation, authentication, chat, and data controls
streamlit_app.py           Streamlit interface
chatbot.py                 Gemini chat generation and VADER mood scoring
database.py                SQLAlchemy models, connections, and schema initialization
memory.py                  User-managed memory facts and relevance selection
screener.py                GAD-7 screening conversation
crisis.py                  Lightweight urgent-language phrase safeguard
users.py                   User profile operations
config.py                  Environment loading and deployment configuration
render.yaml                Render Blueprint for the API and UI services
tests/test_deployment.py   Deployment-focused API tests
evaluate_personalization.py Synthetic personalization evaluation utility
```

## Known limitations

- Anxiety/stress screening suggestions use a small keyword list. They can miss relevant messages or trigger on terms used casually; they are not an assessment of a person’s mental state.
- The crisis safeguard also uses phrase matching and is not a substitute for trained review or emergency services.
- VADER is a general-purpose sentiment heuristic and does not reliably interpret clinical context, sarcasm, or every language.
- Gemini availability, model identifiers, quotas, and pricing can change. Check Google’s current Gemini documentation and account settings before deployment.
- Render Free services may sleep and have resource limits. Use a properly secured, monitored hosting and data-protection setup before serving real users.
