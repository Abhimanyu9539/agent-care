"""Synthetic demo data. Every name, email, and phone number here is fictional."""

from datetime import date, datetime, time, timedelta, timezone

from sqlalchemy import Engine, select
from sqlalchemy.orm import Session

from app.auth.security import hash_password
from app.db.models import (
    Appointment,
    AppointmentSlot,
    Department,
    Doctor,
    PatientProfile,
    RequiredDocument,
    User,
)
from app.db.models.types import utcnow
from app.db.session import Base

SEED_PASSWORD = "password123"
SLOT_DAYS = 21
SLOT_MINUTES = 30
SLOT_DAY_START = time(9, 0)
SLOT_DAY_END = time(17, 0)

DEPARTMENTS = {
    "Cardiology": "Heart and circulation appointments.",
    "Orthopaedics": "Bone, joint, and fracture appointments.",
    "Dermatology": "Skin, hair, and nail appointments.",
    "General Medicine": "General appointments and first visits.",
}
DOCTOR_SUFFIXES = ("One", "Two")

# (department, document_type, applies_to)
REQUIRED_DOCUMENTS = [
    ("Cardiology", "ecg", "follow_up"),
    ("Cardiology", "blood_report", "follow_up"),
    ("Orthopaedics", "imaging", "new"),
    ("General Medicine", "id_proof", "new"),
]

# (name, email, age in years at seed time, phone). Patient two is under 18.
PATIENTS = [
    ("Test Patient One", "patient1@example.com", 40, "+1-555-0101"),
    ("Test Patient Two", "patient2@example.com", 15, "+1-555-0102"),
    ("Test Patient Three", "patient3@example.com", 72, "+1-555-0103"),
]
STAFF = [("Test Staff One", "staff@example.com")]

# On the first two seeded weekdays these slots are pre-booked; on the first, this one is blocked.
BOOKED_TIMES = (time(10, 0), time(10, 30))
BLOCKED_TIME = time(13, 0)


def _weekdays(start: date, days: int) -> list[date]:
    return [d for d in (start + timedelta(n) for n in range(days)) if d.weekday() < 5]


def _day_slot_starts(day: date) -> list[datetime]:
    start = datetime.combine(day, SLOT_DAY_START, tzinfo=timezone.utc)
    end = datetime.combine(day, SLOT_DAY_END, tzinfo=timezone.utc)
    step = timedelta(minutes=SLOT_MINUTES)
    starts = []
    while start + step <= end:
        starts.append(start)
        start += step
    return starts


def seed(session: Session, now: datetime | None = None) -> bool:
    """Insert the demo data. Returns False without writing if already seeded."""
    if session.scalar(select(Department.id).limit(1)) is not None:
        return False

    now = now or utcnow()

    departments = {name: Department(name=name, description=desc) for name, desc in DEPARTMENTS.items()}
    session.add_all(departments.values())

    doctors = {
        name: [Doctor(department=dept, name=f"Dr. {name} {suffix}") for suffix in DOCTOR_SUFFIXES]
        for name, dept in departments.items()
    }
    session.add_all(doc for group in doctors.values() for doc in group)

    session.add_all(
        RequiredDocument(department=departments[dept], document_type=doc_type, applies_to=applies_to)
        for dept, doc_type, applies_to in REQUIRED_DOCUMENTS
    )

    # Slots: weekdays in [today, today + SLOT_DAYS), future start times only.
    seeded_days: list[date] = []
    slots_by_doctor: dict[Doctor, list[AppointmentSlot]] = {}
    for day in _weekdays(now.date(), SLOT_DAYS):
        starts = [s for s in _day_slot_starts(day) if s > now]
        if not starts:
            continue
        seeded_days.append(day)
        for group in doctors.values():
            for doctor in group:
                for start in starts:
                    status = "free"
                    if day in seeded_days[:2] and start.time() in BOOKED_TIMES:
                        status = "booked"
                    elif day == seeded_days[0] and start.time() == BLOCKED_TIME:
                        status = "blocked"
                    slot = AppointmentSlot(
                        doctor=doctor,
                        start_time=start,
                        end_time=start + timedelta(minutes=SLOT_MINUTES),
                        status=status,
                    )
                    slots_by_doctor.setdefault(doctor, []).append(slot)
    session.add_all(slot for slots in slots_by_doctor.values() for slot in slots)

    password_hash = hash_password(SEED_PASSWORD)
    profiles = []
    for name, email, age, phone in PATIENTS:
        user = User(name=name, email=email, password_hash=password_hash, role="patient")
        profile = PatientProfile(
            user=user,
            date_of_birth=date(now.year - age, 1, 15),
            phone=phone,
            preferred_language="en",
            emergency_contact="Test Contact, +1-555-0199",
        )
        session.add_all([user, profile])
        profiles.append(profile)
    session.add_all(
        User(name=name, email=email, password_hash=password_hash, role="staff") for name, email in STAFF
    )

    # Patient one's existing appointment takes Cardiology doctor one's earliest free slot,
    # so conflict checks and the sensitive-cancel window have something to hit.
    cardiologist = doctors["Cardiology"][0]
    first_free = next(s for s in slots_by_doctor[cardiologist] if s.status == "free")
    first_free.status = "booked"
    session.add(
        Appointment(
            patient=profiles[0],
            doctor=cardiologist,
            slot=first_free,
            status="confirmed",
            reason="Routine cardiology review",
        )
    )

    session.commit()
    return True


def init_db(engine: Engine, now: datetime | None = None) -> bool:
    """Create all application tables, then seed. Returns whether data was inserted."""
    Base.metadata.create_all(engine)
    with Session(engine) as session:
        return seed(session, now)
