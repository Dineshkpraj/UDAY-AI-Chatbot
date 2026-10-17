"""Streamlit web interface for the UDAY FastAPI service."""

import os
import base64
from pathlib import Path

import requests
import streamlit as st


LOGO_PATH = Path(__file__).resolve().parent / "assets" / "uday-wordmark.svg"
LOGO_DATA_URI = "data:image/svg+xml;base64," + base64.b64encode(LOGO_PATH.read_bytes()).decode("ascii")


st.set_page_config(
    page_title="UDAY | Your wellness companion",
    page_icon=str(LOGO_PATH),
    layout="wide",
)
st.markdown(
    """
    <style>
    :root {
        --uday-bg: #0d0f17;
        --uday-panel: #171923;
        --uday-panel-soft: #1d202c;
        --uday-border: rgba(183, 174, 255, .14);
        --uday-text: #f4f2fb;
        --uday-muted: #a7a7b8;
        --uday-purple: #7957ee;
        --uday-pink: #ec78ad;
    }
    html, body, [class*="css"] {
        font-family: Inter, "Segoe UI", system-ui, -apple-system, sans-serif;
    }
    .stApp {
        color: var(--uday-text);
        background:
            radial-gradient(ellipse at 50% 0%, rgba(104, 69, 180, .20), transparent 38rem),
            radial-gradient(ellipse at 100% 55%, rgba(94, 65, 170, .09), transparent 30rem),
            var(--uday-bg);
    }
    [data-testid="stHeader"] { background: rgba(13, 15, 23, .72); }
    [data-testid="stAppViewContainer"] > .main .block-container {
        max-width: 1120px;
        padding: 3.2rem 2.2rem 4rem;
    }
    [data-testid="stSidebar"] {
        background: linear-gradient(180deg, #151722, #11131b);
        border-right: 1px solid var(--uday-border);
    }
    [data-testid="stSidebar"] > div:first-child { padding-top: 1.6rem; }
    .uday-brand {
        margin: 0 0 1.35rem;
        max-width: 25rem;
    }
    .uday-brand img {
        display: block;
        height: auto;
        width: min(100%, 25rem);
    }
    .uday-brand-note {
        color: #a7a7b8;
        font-size: .75rem;
        font-weight: 500;
        letter-spacing: .14em;
        margin: .2rem 0 0;
        text-transform: uppercase;
    }
    p.uday-title {
        color: var(--uday-text);
        font-size: clamp(2.1rem, 5vw, 3.8rem) !important;
        font-weight: 760 !important;
        letter-spacing: -.045em !important;
        line-height: 1.08 !important;
        margin: 0 !important;
    }
    .uday-title span {
        color: #c59dff;
        background: linear-gradient(90deg, #ed7cb2 0%, #a77bff 68%, #7f8cff 100%);
        -webkit-background-clip: text;
        background-clip: text;
        -webkit-text-fill-color: transparent;
    }
    .uday-subtitle {
        color: var(--uday-muted);
        font-size: 1rem;
        line-height: 1.7;
        margin: .8rem 0 1.8rem;
        max-width: 44rem;
    }
    .uday-kicker {
        color: #c1aaff;
        display: inline-block;
        border: 1px solid rgba(165, 132, 255, .24);
        background: rgba(125, 87, 238, .10);
        border-radius: 999px;
        font-size: .72rem;
        font-weight: 650;
        letter-spacing: .09em;
        margin-bottom: .9rem;
        padding: .38rem .75rem;
        text-transform: uppercase;
    }
    [data-testid="stForm"] {
        background: linear-gradient(145deg, rgba(29, 31, 44, .96), rgba(20, 22, 32, .96));
        border: 1px solid var(--uday-border);
        border-radius: 22px;
        padding: 1.5rem 1.5rem 1.15rem;
        box-shadow: 0 24px 70px rgba(0, 0, 0, .24);
    }
    [data-testid="stTabs"] [role="tablist"] {
        border-bottom: 1px solid var(--uday-border);
        gap: .65rem;
    }
    [data-testid="stTabs"] [role="tab"] {
        color: var(--uday-muted);
        font-weight: 600;
    }
    [data-testid="stTabs"] [role="tab"][aria-selected="true"] {
        color: #d5c6ff !important;
    }
    [data-testid="stTabs"] .react-aria-SelectionIndicator { background: var(--uday-purple) !important; }
    [data-testid="stNumberInputStepUp"] { background-color: var(--uday-purple) !important; }
    [data-testid="stWidgetLabel"] p, [data-testid="stCaptionContainer"] p {
        color: #c5c4d2;
    }
    [data-baseweb="input"], [data-baseweb="textarea"], [data-baseweb="select"] > div {
        background-color: #11131c !important;
        border-color: rgba(187, 180, 220, .20) !important;
        border-radius: 11px !important;
        color: var(--uday-text) !important;
    }
    [data-baseweb="input"] input, [data-baseweb="textarea"] textarea,
    [data-baseweb="select"] *, [data-baseweb="input"] svg {
        color: var(--uday-text) !important;
        -webkit-text-fill-color: var(--uday-text);
    }
    [data-baseweb="input"]:focus-within, [data-baseweb="textarea"]:focus-within,
    [data-baseweb="select"]:focus-within {
        border-color: #8d70fa !important;
        box-shadow: 0 0 0 1px rgba(141, 112, 250, .45) !important;
    }
    div.stButton > button, [data-testid="stFormSubmitButton"] button {
        border: 1px solid rgba(182, 162, 255, .25);
        border-radius: 11px;
        color: #fff;
        font-weight: 650;
        transition: transform .16s ease, filter .16s ease, border-color .16s ease;
    }
    div.stButton > button[kind="primary"], [data-testid="stFormSubmitButton"] button[kind="primary"] {
        background: linear-gradient(105deg, #6445d8, #8357ed) !important;
        color: #fff !important;
        box-shadow: 0 8px 24px rgba(106, 75, 218, .24);
    }
    [data-testid="stFormSubmitButton"] button {
        background: linear-gradient(105deg, #6445d8, #8357ed) !important;
        color: #fff !important;
    }
    div.stButton > button:hover, [data-testid="stFormSubmitButton"] button:hover {
        border-color: #ac95ff;
        filter: brightness(1.12);
        transform: translateY(-1px);
    }
    [data-testid="stChatMessage"] {
        background: linear-gradient(145deg, rgba(28, 30, 43, .92), rgba(21, 23, 34, .92));
        border: 1px solid var(--uday-border);
        border-radius: 18px;
        padding: 1rem 1.1rem;
    }
    [data-testid="stChatInput"] textarea {
        background: #151722;
        color: var(--uday-text);
    }
    [data-testid="stChatInput"] {
        border-color: rgba(183, 174, 255, .22);
        border-radius: 15px;
    }
    [data-testid="stChatInput"] button { color: #c3afff; }
    [data-testid="stAlert"] { border-radius: 13px; }
    hr { border-color: var(--uday-border); }
    @media (max-width: 640px) {
        [data-testid="stAppViewContainer"] > .main .block-container {
            padding: 2.1rem 1rem 3rem;
        }
        [data-testid="stForm"] { padding: 1.1rem .9rem .9rem; }
    }
    </style>
    """,
    unsafe_allow_html=True,
)

API_URL = os.getenv("UDAY_API_URL", "http://127.0.0.1:8000").rstrip("/")


def render_brand():
    st.markdown(
        f'<div class="uday-brand"><img src="{LOGO_DATA_URI}" alt="UDAY — a wellness companion" /></div>',
        unsafe_allow_html=True,
    )


def api_request(method, path, *, token=None, **kwargs):
    headers = kwargs.pop("headers", {})
    if token:
        headers["Authorization"] = f"Bearer {token}"
    try:
        response = requests.request(
            method, f"{API_URL}{path}", headers=headers, timeout=45, **kwargs
        )
    except requests.RequestException as error:
        st.error(f"Could not reach UDAY's API at {API_URL}. Check that the API is running. ({error})")
        return None
    if not response.ok:
        try:
            detail = response.json().get("detail", response.text)
        except (ValueError, AttributeError):
            detail = response.text
        if response.status_code == 401 and token:
            for key in ("token", "email", "messages", "memories"):
                st.session_state.pop(key, None)
            st.warning("Your sign-in session expired. Please sign in again.")
            st.rerun()
        st.error(f"{detail} (HTTP {response.status_code})")
        return None
    return response


def login(email, password):
    response = api_request("POST", "/token", data={"username": email, "password": password})
    if response is not None:
        st.session_state.token = response.json()["access_token"]
        st.session_state.email = email.strip().lower()
        history = api_request("GET", "/history", token=st.session_state.token)
        st.session_state.messages = history.json().get("messages", []) if history is not None else []
        st.session_state.pop("memories", None)
        st.rerun()


def authentication_view():
    render_brand()
    st.markdown('<p class="uday-kicker">Your personal wellness companion</p>', unsafe_allow_html=True)
    st.markdown('<p class="uday-title">Your path to <span>mental wellness</span>,<br>powered by AI</p>', unsafe_allow_html=True)
    st.markdown('<p class="uday-subtitle">A calm, private space to reflect, find support, and take your next step at your own pace.</p>', unsafe_allow_html=True)
    sign_in, sign_up = st.tabs(["Sign in", "Create account"])
    with sign_in:
        with st.form("login_form"):
            email = st.text_input("Email", autocomplete="email")
            password = st.text_input("Password", type="password", autocomplete="current-password")
            submitted = st.form_submit_button("Sign in", type="primary", use_container_width=True)
        if submitted:
            login(email, password)
    with sign_up:
        with st.form("registration_form"):
            name = st.text_input("Name", max_chars=100)
            email = st.text_input("Email address", key="register_email")
            age = st.number_input("Age", min_value=18, max_value=120, value=18)
            gender = st.selectbox("Gender", ["Male", "Female", "Other"])
            profession = st.selectbox("Profession", ["Student", "Corporate", "Worker", "Homemaker", "Other"])
            focus_area = st.text_input("What would you like support with?", max_chars=300)
            password = st.text_input("Password (at least 12 characters)", type="password", key="register_password")
            confirm = st.text_input("Confirm password", type="password")
            st.caption("UDAY stores your profile, chat transcript, saved memories, and sentiment scores in its database. Your chat text and relevant saved memories are sent to Google Gemini to generate replies. UDAY is not medical or emergency care. Accounts are for adults (18+).")
            with st.expander("What UDAY stores and how to remove it"):
                st.markdown(
                    """
                    - Your profile and password hash, chat transcript, reviewed memory facts, and VADER sentiment scores are stored in the configured database.
                    - Chat text and relevant reviewed memory facts are sent to Google Gemini. Profile details such as your name, age, gender, and focus area are not included in the Gemini prompt.
                    - UDAY keeps up to 500 recent transcript messages per account. VADER saves a score without a message excerpt.
                    - From the signed-in app, you can export your data, clear chat history, delete mood scores, edit/delete memories, or permanently delete your account and linked data.
                    - UDAY is a prototype, not a diagnosis, treatment, or emergency service. Do not use it for urgent help.
                    """
                )
            consent = st.checkbox("I understand and agree to this data use.")
            submitted = st.form_submit_button("Create account", type="primary", use_container_width=True)
        if submitted:
            if not consent:
                st.error("Please review and accept the data-use notice to create an account.")
            elif password != confirm:
                st.error("The passwords do not match.")
            else:
                response = api_request(
                    "POST", "/users",
                    json={
                        "name": name, "email": email, "age": int(age),
                        "gender": gender, "profession": profession,
                        "focus_area": focus_area, "password": password,
                        "privacy_consent": consent,
                    },
                )
                if response is not None:
                    st.success("Account created. Sign in to start chatting.")


def render_chat():
    render_brand()
    st.markdown('<p class="uday-kicker">A moment for you</p>', unsafe_allow_html=True)
    st.markdown('<p class="uday-title">One step at a time.</p>', unsafe_allow_html=True)
    st.markdown('<p class="uday-subtitle">Share what is on your mind. We can work through it together.</p>', unsafe_allow_html=True)
    with st.sidebar:
        st.caption(f"Signed in as {st.session_state.email}")
        st.caption("Your access session expires after 15 minutes. Sign in again when needed.")
        if st.button("Sign out", use_container_width=True):
            for key in ("token", "email", "messages", "memories"):
                st.session_state.pop(key, None)
            st.rerun()
        st.divider()
        st.subheader("Your data")
        export_response = api_request("GET", "/export", token=st.session_state.token)
        if export_response is not None:
            st.download_button("Download my data", data=export_response.content,
                               file_name="uday-data-export.json", mime="application/json",
                               use_container_width=True)
        if st.button("Clear chat history", use_container_width=True):
            cleared = api_request("DELETE", "/history", token=st.session_state.token)
            if cleared is not None:
                st.session_state.messages = []
                st.success("Chat history cleared.")
                st.rerun()
        if st.button("Delete account and all data", use_container_width=True):
            st.session_state.confirm_delete_account = True
        if st.session_state.get("confirm_delete_account"):
            st.warning("This permanently deletes your profile, chats, memories, screening state, and mood scores.")
            if st.button("Confirm permanent deletion", type="primary"):
                deleted = api_request("DELETE", "/account", token=st.session_state.token)
                if deleted is not None:
                    for key in ("token", "email", "messages", "memories", "confirm_delete_account"):
                        st.session_state.pop(key, None)
                    st.rerun()
        st.caption("VADER mood scores are rough language heuristics, not a clinical assessment.")
        mood_response = api_request("GET", "/mood", token=st.session_state.token)
        if mood_response is not None and mood_response.json().get("scores"):
            with st.expander("Recent mood scores (heuristic)"):
                st.caption(mood_response.json()["method"])
                for item in mood_response.json()["scores"][:10]:
                    st.caption(f"{item['created_at'][:10]} · {item['sentiment_score']:+.2f}")
                if st.button("Delete mood scores"):
                    deleted = api_request("DELETE", "/mood", token=st.session_state.token)
                    if deleted is not None:
                        st.success("Mood scores deleted.")
                        st.rerun()
        st.divider()
        st.subheader("Saved memories")
        if st.button("Refresh memories", use_container_width=True):
            st.session_state.pop("memories", None)
        if "memories" not in st.session_state:
            response = api_request("GET", "/memory", token=st.session_state.token)
            if response is not None:
                st.session_state.memories = response.json().get("facts", [])
        facts = st.session_state.get("memories", [])
        if facts:
            st.caption("Review and update the facts UDAY uses for personalization.")
            revised = st.text_area(
                "One fact per line", value="\n".join(facts), height=180,
                max_chars=50000,
                help="Saving replaces your current saved facts. Remove a line to delete it.",
            )
            if st.button("Save memory changes", type="primary", use_container_width=True):
                updated = [line.strip() for line in revised.splitlines() if line.strip()]
                response = api_request("PUT", "/memory", token=st.session_state.token, json={"facts": updated})
                if response is not None:
                    st.session_state.memories = response.json().get("facts", [])
                    st.success("Memories updated.")
                    st.rerun()
            if st.button("Delete all memories", use_container_width=True):
                response = api_request("DELETE", "/memory", token=st.session_state.token)
                if response is not None:
                    st.session_state.memories = []
                    st.success("All saved memories deleted.")
                    st.rerun()
        else:
            st.caption("No saved memories yet.")
            if st.button("Add a memory", use_container_width=True):
                st.session_state.show_add_memory = True
            if st.session_state.get("show_add_memory", False):
                new_fact = st.text_input("Memory to save", max_chars=500)
                if st.button("Save memory") and new_fact.strip():
                    response = api_request(
                        "PUT", "/memory", token=st.session_state.token,
                        json={"facts": [new_fact.strip()]},
                    )
                    if response is not None:
                        st.session_state.memories = response.json().get("facts", [])
                        st.session_state.show_add_memory = False
                        st.rerun()

    for message in st.session_state.messages:
        with st.chat_message(message["role"]):
            st.markdown(message["content"])
    prompt = st.chat_input("What’s on your mind?")
    if prompt:
        st.session_state.messages.append({"role": "user", "content": prompt})
        with st.chat_message("user"):
            st.markdown(prompt)
        with st.chat_message("assistant"):
            with st.spinner("UDAY is listening…"):
                response = api_request(
                    "POST", "/chat", token=st.session_state.token, json={"message": prompt}
                )
            if response is not None:
                answer = response.json().get("response", "")
                st.markdown(answer)
                st.session_state.messages.append({"role": "assistant", "content": answer})
            else:
                st.session_state.messages.pop()
    st.caption("UDAY is a supportive companion, not a substitute for professional or emergency care.")


if "token" not in st.session_state:
    authentication_view()
else:
    render_chat()
