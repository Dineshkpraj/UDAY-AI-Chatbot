from datetime import datetime, timezone

from sqlalchemy import select

from database import UserProfile, get_session_factory, initialize_database


class UserManager:
    """Handles user profiles in the configured SQL database."""

    def load_db(self):
        """Compatibility helper returning all profiles keyed by email."""
        initialize_database()
        with get_session_factory()() as session:
            users = session.scalars(select(UserProfile)).all()
            return {user.email: self._to_dict(user) for user in users}

    def save_db(self, db_data):
        """Persist a profile mapping (used by the API when storing password hashes)."""
        initialize_database()
        with get_session_factory()() as session, session.begin():
            for email, data in db_data.items():
                user = session.get(UserProfile, email)
                if user is None:
                    continue
                user.password_hash = data.get("password_hash")

    def get_user(self, email):
        initialize_database()
        with get_session_factory()() as session:
            user = session.get(UserProfile, email.lower())
            return self._to_dict(user) if user else None

    def register_user(self, email, name, age, gender, profession, focus, password_hash=None, privacy_consent_at=None, privacy_notice_version=None):
        initialize_database()
        email = email.lower()
        with get_session_factory()() as session, session.begin():
            if session.get(UserProfile, email):
                raise ValueError("An account with this email already exists.")
            user = UserProfile(
                email=email,
                name=name,
                age=int(age),
                gender=gender,
                profession=profession,
                focus_area=focus,
                joined_at=datetime.now(timezone.utc),
                password_hash=password_hash,
                privacy_consent_at=privacy_consent_at,
                privacy_notice_version=privacy_notice_version,
            )
            session.add(user)
            session.flush()
            return self._to_dict(user)

    @staticmethod
    def _to_dict(user):
        return {
            "name": user.name,
            "age": user.age,
            "gender": user.gender,
            "profession": user.profession,
            "focus_area": user.focus_area,
            "joined_at": user.joined_at.isoformat(),
            "password_hash": user.password_hash,
            "privacy_consent_at": user.privacy_consent_at.isoformat() if user.privacy_consent_at else None,
            "privacy_notice_version": user.privacy_notice_version,
        }
