"""ORM models for every persistent entity.

Timestamps are timezone-aware UTC (`UTCDateTime`). Enumerations are short
strings guarded by CHECK constraints built from the tuples below, which the
service layer reuses. JSON payloads are stored as text produced by `json.dumps`.
"""

from datetime import date, datetime

from sqlalchemy import (
    Boolean,
    CheckConstraint,
    Date,
    Float,
    ForeignKey,
    Index,
    Integer,
    String,
    Text,
    UniqueConstraint,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.models.types import UTCDateTime, utcnow
from app.db.session import Base

USER_ROLES = ("patient", "staff")
SLOT_STATUSES = ("free", "booked", "blocked")
APPOINTMENT_STATUSES = ("pending", "confirmed", "rescheduled", "cancelled")
ACTIVE_APPOINTMENT_STATUSES = ("pending", "confirmed", "rescheduled")
APPLIES_TO = ("new", "follow_up", "any")
REMINDER_STATUSES = ("scheduled", "sent", "cancelled")
NOTIFICATION_CHANNELS = ("email", "sms", "in_app")
ESCALATION_CATEGORIES = (
    "emergency",
    "clinical_request",
    "sensitive",
    "low_confidence",
    "sensitive_action",
    "system_error",
)
ESCALATION_STATUSES = ("pending", "approved", "rejected")


def _one_of(column: str, values: tuple[str, ...]) -> CheckConstraint:
    allowed = ", ".join(f"'{v}'" for v in values)
    return CheckConstraint(f"{column} IN ({allowed})", name=column)


class User(Base):
    __tablename__ = "users"
    __table_args__ = (_one_of("role", USER_ROLES),)

    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(String(120))
    email: Mapped[str] = mapped_column(String(255), unique=True)
    password_hash: Mapped[str] = mapped_column(String(255))
    role: Mapped[str] = mapped_column(String(20))
    created_at: Mapped[datetime] = mapped_column(UTCDateTime, default=utcnow)

    profile: Mapped["PatientProfile | None"] = relationship(back_populates="user", uselist=False)


class PatientProfile(Base):
    __tablename__ = "patient_profiles"

    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"), unique=True)
    date_of_birth: Mapped[date | None] = mapped_column(Date)
    phone: Mapped[str | None] = mapped_column(String(40))
    preferred_language: Mapped[str] = mapped_column(String(20), default="en")
    emergency_contact: Mapped[str | None] = mapped_column(String(255))
    created_at: Mapped[datetime] = mapped_column(UTCDateTime, default=utcnow)
    updated_at: Mapped[datetime] = mapped_column(UTCDateTime, default=utcnow, onupdate=utcnow)

    user: Mapped[User] = relationship(back_populates="profile")


class Department(Base):
    __tablename__ = "departments"

    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(String(120), unique=True)
    description: Mapped[str] = mapped_column(Text, default="")
    active: Mapped[bool] = mapped_column(Boolean, default=True)

    doctors: Mapped[list["Doctor"]] = relationship(back_populates="department")
    required_documents: Mapped[list["RequiredDocument"]] = relationship(back_populates="department")


class Doctor(Base):
    __tablename__ = "doctors"

    id: Mapped[int] = mapped_column(primary_key=True)
    department_id: Mapped[int] = mapped_column(ForeignKey("departments.id"), index=True)
    name: Mapped[str] = mapped_column(String(120))
    active: Mapped[bool] = mapped_column(Boolean, default=True)

    department: Mapped[Department] = relationship(back_populates="doctors")
    slots: Mapped[list["AppointmentSlot"]] = relationship(back_populates="doctor")


class AppointmentSlot(Base):
    __tablename__ = "appointment_slots"
    __table_args__ = (
        _one_of("status", SLOT_STATUSES),
        Index(None, "doctor_id", "start_time", unique=True),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    doctor_id: Mapped[int] = mapped_column(ForeignKey("doctors.id"))
    start_time: Mapped[datetime] = mapped_column(UTCDateTime)
    end_time: Mapped[datetime] = mapped_column(UTCDateTime)
    status: Mapped[str] = mapped_column(String(20), default="free")

    doctor: Mapped[Doctor] = relationship(back_populates="slots")


class Appointment(Base):
    __tablename__ = "appointments"
    __table_args__ = (_one_of("status", APPOINTMENT_STATUSES),)

    id: Mapped[int] = mapped_column(primary_key=True)
    patient_id: Mapped[int] = mapped_column(ForeignKey("patient_profiles.id"), index=True)
    doctor_id: Mapped[int] = mapped_column(ForeignKey("doctors.id"))
    slot_id: Mapped[int] = mapped_column(ForeignKey("appointment_slots.id"), index=True)
    status: Mapped[str] = mapped_column(String(20), default="pending")
    reason: Mapped[str] = mapped_column(Text, default="")
    workflow_run_id: Mapped[int | None] = mapped_column(ForeignKey("workflow_runs.id"), index=True)
    created_at: Mapped[datetime] = mapped_column(UTCDateTime, default=utcnow)
    updated_at: Mapped[datetime] = mapped_column(UTCDateTime, default=utcnow, onupdate=utcnow)

    patient: Mapped[PatientProfile] = relationship()
    doctor: Mapped[Doctor] = relationship()
    slot: Mapped[AppointmentSlot] = relationship()


class RequiredDocument(Base):
    __tablename__ = "required_documents"
    __table_args__ = (_one_of("applies_to", APPLIES_TO),)

    id: Mapped[int] = mapped_column(primary_key=True)
    department_id: Mapped[int] = mapped_column(ForeignKey("departments.id"), index=True)
    document_type: Mapped[str] = mapped_column(String(50))
    applies_to: Mapped[str] = mapped_column(String(20), default="any")

    department: Mapped[Department] = relationship(back_populates="required_documents")


class PatientDocument(Base):
    __tablename__ = "patient_documents"
    __table_args__ = (UniqueConstraint("patient_id", "checksum"),)

    id: Mapped[int] = mapped_column(primary_key=True)
    patient_id: Mapped[int] = mapped_column(ForeignKey("patient_profiles.id"))
    document_type: Mapped[str] = mapped_column(String(50), default="unclassified")
    original_filename: Mapped[str] = mapped_column(String(255))
    storage_path: Mapped[str] = mapped_column(String(500))
    mime_type: Mapped[str] = mapped_column(String(100))
    size_bytes: Mapped[int] = mapped_column(Integer)
    checksum: Mapped[str] = mapped_column(String(64))
    document_date: Mapped[date | None] = mapped_column(Date)
    classification_confidence: Mapped[float | None] = mapped_column(Float)
    created_at: Mapped[datetime] = mapped_column(UTCDateTime, default=utcnow)


class WorkflowRun(Base):
    __tablename__ = "workflow_runs"

    id: Mapped[int] = mapped_column(primary_key=True)
    patient_id: Mapped[int] = mapped_column(ForeignKey("patient_profiles.id"), index=True)
    request_text: Mapped[str] = mapped_column(Text)
    # Equals str(id). The id exists only after flush, so the runner sets it then;
    # NULLs do not collide under UNIQUE.
    thread_id: Mapped[str | None] = mapped_column(String(64), unique=True)
    current_step: Mapped[str] = mapped_column(String(40), default="queued")
    status: Mapped[str] = mapped_column(String(30), default="running", index=True)
    state: Mapped[str] = mapped_column(Text, default="{}")
    error: Mapped[str | None] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(UTCDateTime, default=utcnow)
    updated_at: Mapped[datetime] = mapped_column(UTCDateTime, default=utcnow, onupdate=utcnow)

    patient: Mapped[PatientProfile] = relationship()


class Reminder(Base):
    __tablename__ = "reminders"
    __table_args__ = (
        _one_of("status", REMINDER_STATUSES),
        Index(None, "status", "scheduled_at"),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    patient_id: Mapped[int] = mapped_column(ForeignKey("patient_profiles.id"), index=True)
    appointment_id: Mapped[int | None] = mapped_column(ForeignKey("appointments.id"), index=True)
    workflow_run_id: Mapped[int | None] = mapped_column(ForeignKey("workflow_runs.id"))
    reminder_type: Mapped[str] = mapped_column(String(30))
    scheduled_at: Mapped[datetime] = mapped_column(UTCDateTime)
    status: Mapped[str] = mapped_column(String(20), default="scheduled")
    message: Mapped[str] = mapped_column(Text, default="")


class Notification(Base):
    __tablename__ = "notifications"
    __table_args__ = (_one_of("channel", NOTIFICATION_CHANNELS),)

    id: Mapped[int] = mapped_column(primary_key=True)
    patient_id: Mapped[int] = mapped_column(ForeignKey("patient_profiles.id"), index=True)
    channel: Mapped[str] = mapped_column(String(20))
    subject: Mapped[str] = mapped_column(String(255))
    body: Mapped[str] = mapped_column(Text)
    status: Mapped[str] = mapped_column(String(20), default="pending")
    created_at: Mapped[datetime] = mapped_column(UTCDateTime, default=utcnow)
    sent_at: Mapped[datetime | None] = mapped_column(UTCDateTime)


class Escalation(Base):
    __tablename__ = "escalations"
    __table_args__ = (
        _one_of("category", ESCALATION_CATEGORIES),
        _one_of("status", ESCALATION_STATUSES),
        Index(None, "workflow_run_id", "status"),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    workflow_run_id: Mapped[int] = mapped_column(ForeignKey("workflow_runs.id"))
    patient_id: Mapped[int] = mapped_column(ForeignKey("patient_profiles.id"))
    category: Mapped[str] = mapped_column(String(20))
    reason: Mapped[str] = mapped_column(Text)
    status: Mapped[str] = mapped_column(String(20), default="pending")
    reviewed_by: Mapped[int | None] = mapped_column(ForeignKey("users.id"))
    review_note: Mapped[str | None] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(UTCDateTime, default=utcnow)
    reviewed_at: Mapped[datetime | None] = mapped_column(UTCDateTime)

    workflow_run: Mapped[WorkflowRun] = relationship()
    reviewer: Mapped[User | None] = relationship()


class AuditEvent(Base):
    __tablename__ = "audit_events"
    __table_args__ = (Index(None, "entity_type", "entity_id"),)

    id: Mapped[int] = mapped_column(primary_key=True)
    actor_id: Mapped[int | None] = mapped_column(ForeignKey("users.id"))
    actor_role: Mapped[str] = mapped_column(String(20))
    action: Mapped[str] = mapped_column(String(100), index=True)
    entity_type: Mapped[str] = mapped_column(String(50))
    entity_id: Mapped[int | None] = mapped_column(Integer)
    # `metadata` is reserved on declarative classes; the column keeps that name.
    metadata_json: Mapped[str] = mapped_column("metadata", Text, default="{}")
    created_at: Mapped[datetime] = mapped_column(UTCDateTime, default=utcnow)
