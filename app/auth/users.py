"""Plain-SQL queries for user accounts and patient registration."""

from datetime import date

from sqlalchemy import RowMapping, text
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.auth.security import hash_password


class EmailTaken(Exception):
    """The email already belongs to an account."""


def get_user_by_email(db: Session, email: str) -> RowMapping | None:
    """The user with this email in any letter case, including the password hash."""
    return db.execute(
        text(
            "SELECT id, full_name, password_hash, role, is_active "
            "FROM users WHERE lower(email) = lower(:email)"
        ),
        {"email": email.strip()},
    ).mappings().one_or_none()


def get_user(db: Session, user_id: int) -> RowMapping | None:
    return db.execute(
        text("SELECT id, full_name, role, is_active FROM users WHERE id = :id"),
        {"id": user_id},
    ).mappings().one_or_none()


def register_patient(
    db: Session, *, full_name: str, email: str, password: str, date_of_birth: date, phone: str
) -> int:
    """Create a patient account and its profile in one transaction. Returns the user id."""
    try:
        user_id = db.execute(
            text(
                "INSERT INTO users (email, full_name, password_hash, role) "
                "VALUES (:email, :full_name, :password_hash, 'PATIENT') RETURNING id"
            ),
            {"email": email.strip().lower(), "full_name": full_name, "password_hash": hash_password(password)},
        ).scalar_one()
        db.execute(
            text(
                "INSERT INTO patient_profiles (user_id, full_name, date_of_birth, phone) "
                "VALUES (:user_id, :full_name, :date_of_birth, :phone)"
            ),
            {"user_id": user_id, "full_name": full_name, "date_of_birth": date_of_birth, "phone": phone},
        )
        db.commit()
    except IntegrityError:
        # The only constraint a new account can break is the unique email (users_email_uq).
        db.rollback()
        raise EmailTaken from None
    return user_id
