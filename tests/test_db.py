"""Step 2: schema, constraints, and seed data."""

from collections.abc import Iterator
from datetime import date, datetime, timezone
from pathlib import Path

import pytest
from sqlalchemy import Engine, func, inspect, select
from sqlalchemy.exc import IntegrityError, StatementError
from sqlalchemy.orm import Session

from app.auth.security import verify_password
from app.config import Settings
from app.db.session import make_engine, make_session_factory
from app.db.models import (
    Appointment,
    AppointmentSlot,
    Department,
    Doctor,
    PatientDocument,
    PatientProfile,
    RequiredDocument,
    User,
    WorkflowRun,
)
from app.main import create_app
from scripts.seed import SEED_PASSWORD, init_db

# A Monday before 09:00: the 21-day window holds 15 full weekdays.
NOW = datetime(2026, 9, 14, 7, 0, tzinfo=timezone.utc)

EXPECTED_TABLES = {
    "users",
    "patient_profiles",
    "departments",
    "doctors",
    "appointment_slots",
    "appointments",
    "required_documents",
    "patient_documents",
    "workflow_runs",
    "reminders",
    "notifications",
    "escalations",
    "audit_events",
}


def _count(session: Session, model: type) -> int:
    return session.scalar(select(func.count()).select_from(model))


def _counts(session: Session) -> dict[str, int]:
    models = (Department, Doctor, AppointmentSlot, RequiredDocument, User, PatientProfile, Appointment)
    return {m.__tablename__: _count(session, m) for m in models}


@pytest.fixture(scope="module")
def seeded(tmp_path_factory: pytest.TempPathFactory) -> Iterator[Session]:
    """One seeded database shared by the read-only assertions (bcrypt is slow)."""
    engine = make_engine(f"sqlite:///{tmp_path_factory.mktemp('seeded') / 'seed.db'}")
    assert init_db(engine, NOW) is True
    with make_session_factory(engine)() as session:
        yield session
    engine.dispose()


def _age_at(dob: date, on: date) -> int:
    return on.year - dob.year - ((on.month, on.day) < (dob.month, dob.day))


def test_create_all_creates_every_table(engine: Engine) -> None:
    assert set(inspect(engine).get_table_names()) == EXPECTED_TABLES


def test_seed_counts(seeded: Session) -> None:
    assert _counts(seeded) == {
        "departments": 4,
        "doctors": 8,
        "appointment_slots": 15 * 16 * 8,
        "required_documents": 4,
        "users": 4,
        "patient_profiles": 3,
        "appointments": 1,
    }
    assert seeded.scalars(select(Department.name).order_by(Department.name)).all() == [
        "Cardiology",
        "Dermatology",
        "General Medicine",
        "Orthopaedics",
    ]
    roles = dict(seeded.execute(select(User.role, func.count()).group_by(User.role)).all())
    assert roles == {"patient": 3, "staff": 1}


def test_seed_required_documents(seeded: Session) -> None:
    rows = seeded.execute(
        select(Department.name, RequiredDocument.document_type, RequiredDocument.applies_to).join(
            RequiredDocument.department
        )
    ).all()
    assert set(rows) == {
        ("Cardiology", "ecg", "follow_up"),
        ("Cardiology", "blood_report", "follow_up"),
        ("Orthopaedics", "imaging", "new"),
        ("General Medicine", "id_proof", "new"),
    }


def test_seed_slots_are_weekday_business_hours_in_the_future(seeded: Session) -> None:
    for slot in seeded.scalars(select(AppointmentSlot)):
        assert slot.start_time > NOW
        assert slot.start_time.weekday() < 5
        assert 9 <= slot.start_time.hour < 17
        assert (slot.end_time - slot.start_time).total_seconds() == 30 * 60
        assert slot.start_time.tzinfo == timezone.utc


def test_seed_existing_appointment_and_slot_statuses(seeded: Session) -> None:
    patient_one = seeded.scalars(select(User).where(User.email == "patient1@example.com")).one()
    appointment = seeded.scalars(select(Appointment)).one()

    assert appointment.patient_id == patient_one.profile.id
    assert appointment.status == "confirmed"
    assert appointment.slot.status == "booked"
    assert appointment.doctor.department.name == "Cardiology"

    statuses = dict(
        seeded.execute(select(AppointmentSlot.status, func.count()).group_by(AppointmentSlot.status)).all()
    )
    assert statuses["booked"] > 1  # pre-booked slots besides patient one's
    assert statuses["blocked"] >= 1


def test_seed_users_are_synthetic_with_one_minor(seeded: Session) -> None:
    users = seeded.scalars(select(User)).all()
    assert all(u.email.endswith("@example.com") for u in users)
    assert all(verify_password(SEED_PASSWORD, u.password_hash) for u in users)

    ages = [_age_at(p.date_of_birth, NOW.date()) for p in seeded.scalars(select(PatientProfile))]
    assert sum(age < 18 for age in ages) == 1
    assert any(age >= 65 for age in ages)


def test_init_db_is_idempotent(tmp_path: Path) -> None:
    engine = make_engine(f"sqlite:///{tmp_path / 'twice.db'}")
    try:
        assert init_db(engine, NOW) is True
        with Session(engine) as session:
            before = _counts(session)

        assert init_db(engine, NOW) is False
        with Session(engine) as session:
            assert _counts(session) == before
    finally:
        engine.dispose()


def _patient(session: Session) -> PatientProfile:
    user = User(name="Test Patient", email="p@example.com", password_hash="x", role="patient")
    profile = PatientProfile(user=user)
    session.add_all([user, profile])
    session.flush()
    return profile


def test_utc_datetime_round_trips_aware_and_rejects_naive(session: Session) -> None:
    profile = _patient(session)
    session.commit()
    session.expire_all()

    assert session.get(PatientProfile, profile.id).created_at.tzinfo == timezone.utc

    session.add(WorkflowRun(patient_id=profile.id, request_text="x", created_at=datetime(2026, 1, 1)))
    with pytest.raises(StatementError, match="naive datetime"):
        session.flush()


def test_duplicate_document_checksum_rejected(session: Session) -> None:
    profile = _patient(session)
    for _ in range(2):
        session.add(
            PatientDocument(
                patient_id=profile.id,
                original_filename="ecg.pdf",
                storage_path="uploads/ecg.pdf",
                mime_type="application/pdf",
                size_bytes=10,
                checksum="a" * 64,
            )
        )
    with pytest.raises(IntegrityError):
        session.flush()


def test_sqlite_foreign_keys_enforced(session: Session) -> None:
    session.add(Doctor(department_id=999, name="Dr. Nobody"))
    with pytest.raises(IntegrityError):
        session.flush()


def test_enum_check_constraint_enforced(session: Session) -> None:
    session.add(User(name="Test", email="bad@example.com", password_hash="x", role="admin"))
    with pytest.raises(IntegrityError):
        session.flush()


def test_app_exposes_session_factory(tmp_path: Path) -> None:
    url = f"sqlite:///{tmp_path / 'app.db'}"
    app = create_app(Settings(_env_file=None, secret_key="test-secret", database_url=url))
    try:
        init_db(app.state.engine, NOW)
        with app.state.session_factory() as session:
            assert _count(session, Department) == 4
    finally:
        app.state.engine.dispose()
