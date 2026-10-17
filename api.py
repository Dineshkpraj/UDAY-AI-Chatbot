"""FastAPI interface for UDAY with validated request bodies."""

from enum import Enum
from functools import lru_cache
from typing import Annotated
from datetime import datetime, timedelta, timezone
import hashlib
import os

import jwt
from fastapi import Depends, FastAPI, HTTPException, Request, status
from fastapi.security import OAuth2PasswordBearer, OAuth2PasswordRequestForm
from pwdlib import PasswordHash
from pydantic import BaseModel, ConfigDict, EmailStr, Field

from chatbot import Chatbot
from config import get_gemini_api_key, load_dotenv_file, validate_deployment_environment
from database import (initialize_database, load_chat_history, get_screening_state,
                      save_screening_state, bump_rate_limit, delete_user_data,
                      get_mood_logs, delete_mood_logs, get_session_factory, ChatHistory, ScreeningState)
from memory import MemoryManager
from crisis import CrisisManager
from users import UserManager
from screener import Screener


class Gender(str, Enum):
    male = "Male"
    female = "Female"
    other = "Other"


class Profession(str, Enum):
    student = "Student"
    corporate = "Corporate"
    worker = "Worker"
    homemaker = "Homemaker"
    other = "Other"


class RegistrationRequest(BaseModel):
    model_config = ConfigDict(str_strip_whitespace=True)

    email: EmailStr
    name: Annotated[str, Field(min_length=1, max_length=100)]
    age: int = Field(ge=18, le=120)
    gender: Gender
    profession: Profession
    focus_area: Annotated[str, Field(min_length=1, max_length=300)]
    password: Annotated[str, Field(min_length=12, max_length=128)]
    privacy_consent: bool


class ChatRequest(BaseModel):
    message: Annotated[str, Field(min_length=1, max_length=4000)]


class ChatResponse(BaseModel):
    response: str


class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"


class MemoryUpdateRequest(BaseModel):
    facts: Annotated[list[Annotated[str, Field(strip_whitespace=True, min_length=1, max_length=500)]], Field(max_length=100)]


class MemoryResponse(BaseModel):
    facts: list[str]


app = FastAPI(title="UDAY API", version="1.0.0")
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/token")
password_hash = PasswordHash.recommended()
JWT_ALGORITHM = "HS256"
ACCESS_TOKEN_MINUTES = 15
PRIVACY_NOTICE_VERSION = "1.0"


@lru_cache(maxsize=1)
def get_user_manager() -> UserManager:
    return UserManager()


@lru_cache(maxsize=1)
def get_api_key() -> str:
    return get_gemini_api_key()


def get_memory_manager(email: str) -> MemoryManager:
    return MemoryManager(model=None, user_email=email)


def get_jwt_secret() -> str:
    load_dotenv_file()
    secret = os.getenv("JWT_SECRET_KEY")
    if not secret or len(secret) < 32 or secret.lower() in {"changeme", "secret", "your-secret-key"}:
        raise RuntimeError("Set JWT_SECRET_KEY to a random secret of at least 32 characters.")
    return secret


def create_access_token(email: str) -> str:
    issued_at = int(datetime.now(timezone.utc).timestamp())
    return jwt.encode(
        {"sub": email, "iat": issued_at, "exp": issued_at + ACCESS_TOKEN_MINUTES * 60},
        get_jwt_secret(),
        algorithm=JWT_ALGORITHM,
    )


def get_current_user(token: Annotated[str, Depends(oauth2_scheme)]):
    credentials_error = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Invalid or expired access token.",
        headers={"WWW-Authenticate": "Bearer"},
    )
    try:
        payload = jwt.decode(token, get_jwt_secret(), algorithms=[JWT_ALGORITHM])
        email = payload.get("sub")
        if not isinstance(email, str):
            raise credentials_error
    except (jwt.PyJWTError, RuntimeError) as error:
        raise credentials_error from error

    profile = get_user_manager().get_user(email)
    if not profile:
        raise credentials_error
    return email, profile


def enforce_rate_limit(request: Request, scope: str, limit: int, window_seconds: int, *, include_ip=True):
    now = datetime.now(timezone.utc)
    window = int(now.timestamp()) // window_seconds
    client_ip = request.client.host if request.client else "unknown"
    ip_hash = hashlib.sha256(client_ip.encode("utf-8")).hexdigest()[:32]
    bucket = f"{scope}:{ip_hash}:{window}" if include_ip else f"{scope}:{window}"
    if bump_rate_limit(bucket, now) > limit:
        raise HTTPException(status_code=429, detail="Too many requests. Please wait and try again.",
                            headers={"Retry-After": str(window_seconds)})


@app.get("/health")
def health_check():
    validate_deployment_environment()
    initialize_database()
    return {"status": "ok"}


@app.post("/users", status_code=201)
def register_user(request: RegistrationRequest, http_request: Request):
    """Create a profile after FastAPI/Pydantic has validated every field."""
    manager = get_user_manager()
    enforce_rate_limit(http_request, "register", 5, 3600)
    if not request.privacy_consent:
        raise HTTPException(status_code=422, detail="Privacy notice consent is required to create an account.")
    email = str(request.email).lower()
    if manager.get_user(email):
        raise HTTPException(status_code=409, detail="An account with this email already exists.")

    profile = manager.register_user(
        email=email,
        name=request.name,
        age=request.age,
        gender=request.gender.value,
        profession=request.profession.value,
        focus=request.focus_area,
        password_hash=password_hash.hash(request.password),
        privacy_consent_at=datetime.now(timezone.utc),
        privacy_notice_version=PRIVACY_NOTICE_VERSION,
    )
    # Avoid returning email or other identifying data unnecessarily.
    return {"name": profile["name"], "message": "Registration complete."}


@app.post("/token", response_model=TokenResponse)
def login(form: Annotated[OAuth2PasswordRequestForm, Depends()], request: Request):
    """Validate OAuth2 password credentials and issue a short-lived JWT."""
    email = form.username.strip().lower()
    email_key = hashlib.sha256(email.encode("utf-8")).hexdigest()[:24]
    enforce_rate_limit(request, f"login:{email_key}", 10, 900)
    profile = get_user_manager().get_user(email)
    stored_hash = profile.get("password_hash") if profile else None
    if not stored_hash or not password_hash.verify(form.password, stored_hash):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect email or password.",
            headers={"WWW-Authenticate": "Bearer"},
        )
    return TokenResponse(access_token=create_access_token(email))


@app.post("/chat", response_model=ChatResponse)
def chat(
    request: ChatRequest,
    http_request: Request,
    current_user: Annotated[tuple[str, dict], Depends(get_current_user)],
):
    """Send a validated message for the user authenticated by the bearer token."""
    email, profile = current_user
    user_key = hashlib.sha256(email.encode("utf-8")).hexdigest()[:32]
    enforce_rate_limit(http_request, f"chat:{user_key}", 30, 60, include_ip=False)

    try:
        crisis_response = CrisisManager().check_for_crisis(request.message)
        if crisis_response:
            save_screening_state(email, {})
            return ChatResponse(response=crisis_response)
        state = get_screening_state(email)
        screener = Screener()
        if state.get("active"):
            screener.is_active = True
            screener.question_index = int(state.get("question_index", 0))
            screener.total_score = int(state.get("total_score", 0))
            answer = screener.process_input(request.message)
            if screener.is_active:
                save_screening_state(email, {"active": True, "question_index": screener.question_index,
                                             "total_score": screener.total_score})
            else:
                save_screening_state(email, {})
            return ChatResponse(response=answer)
        if "screening" in request.message.lower():
            answer = screener.start_screening()
            save_screening_state(email, {"active": True, "question_index": 0, "total_score": 0})
            return ChatResponse(response=answer)
        bot = Chatbot(get_api_key(), email, profile)
        return ChatResponse(response=bot.get_response(request.message))
    except RuntimeError as error:
        raise HTTPException(status_code=503,
                            detail="The AI service is temporarily unavailable. Please try again shortly.") from error


@app.get("/history")
def chat_history(current_user: Annotated[tuple[str, dict], Depends(get_current_user)]):
    """Return the authenticated user's persisted chat transcript."""
    email, _ = current_user
    messages = []
    for message in load_chat_history(email):
        role = "assistant" if message.get("role") == "model" else message.get("role")
        if role not in {"user", "assistant"}:
            continue
        content = "\n".join(
            part for part in message.get("parts", []) if isinstance(part, str)
        )
        if content:
            messages.append({"role": role, "content": content})
    return {"messages": messages}


@app.get("/memory", response_model=MemoryResponse)
def review_memory(current_user: Annotated[tuple[str, dict], Depends(get_current_user)]):
    """List the authenticated user's saved long-term memory facts."""
    email, _ = current_user
    return MemoryResponse(facts=get_memory_manager(email).get_facts())


@app.put("/memory", response_model=MemoryResponse)
def edit_memory(
    request: MemoryUpdateRequest,
    current_user: Annotated[tuple[str, dict], Depends(get_current_user)],
):
    """Replace all memory facts with the user's reviewed and edited list."""
    email, _ = current_user
    manager = get_memory_manager(email)
    manager.replace_facts(request.facts)
    return MemoryResponse(facts=manager.get_facts())


@app.delete("/memory/{fact_index}", response_model=MemoryResponse)
def delete_memory_fact(
    fact_index: int,
    current_user: Annotated[tuple[str, dict], Depends(get_current_user)],
):
    """Delete one memory fact by its zero-based index."""
    email, _ = current_user
    manager = get_memory_manager(email)
    if not manager.delete_fact(fact_index):
        raise HTTPException(status_code=404, detail="Memory fact not found.")
    return MemoryResponse(facts=manager.get_facts())


@app.delete("/memory", status_code=204)
def delete_all_memory(current_user: Annotated[tuple[str, dict], Depends(get_current_user)]):
    """Delete all saved long-term memory facts for the authenticated user."""
    email, _ = current_user
    get_memory_manager(email).clear()


@app.get("/export")
def export_user_data(current_user: Annotated[tuple[str, dict], Depends(get_current_user)]):
    email, profile = current_user
    return {"profile": {key: value for key, value in profile.items() if key != "password_hash"},
            "messages": load_chat_history(email), "memories": get_memory_manager(email).get_facts(),
            "mood_scores": get_mood_logs(email)}


@app.delete("/history", status_code=204)
def clear_history(current_user: Annotated[tuple[str, dict], Depends(get_current_user)]):
    email, _ = current_user
    initialize_database()
    with get_session_factory()() as session, session.begin():
        session.query(ChatHistory).filter(ChatHistory.email == email).delete()
        session.query(ScreeningState).filter(ScreeningState.email == email).delete()


@app.get("/mood")
def mood_history(current_user: Annotated[tuple[str, dict], Depends(get_current_user)]):
    return {"scores": get_mood_logs(current_user[0]),
            "method": "VADER sentiment heuristic; not a clinical assessment."}


@app.delete("/mood", status_code=204)
def clear_mood_history(current_user: Annotated[tuple[str, dict], Depends(get_current_user)]):
    delete_mood_logs(current_user[0])


@app.delete("/account", status_code=204)
def delete_account(current_user: Annotated[tuple[str, dict], Depends(get_current_user)]):
    delete_user_data(current_user[0])
