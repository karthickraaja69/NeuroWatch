"""SQLAlchemy database configuration and models."""

from datetime import datetime, timezone
from typing import Optional

from sqlalchemy import Column, DateTime, Float, Integer, String, create_engine, text
from sqlalchemy.orm import DeclarativeBase, Session, sessionmaker


from pathlib import Path

def _run_migrations() -> None:
    """Add missing columns to existing tables without data loss.

    - Ensure `patients.created_at` exists.
    - Ensure `sos_alerts.created_at` exists and backfill from `timestamp`.
    """
    with engine.begin() as conn:
        # Patients table migration
        patient_info = conn.execute(text("PRAGMA table_info(patients)")).fetchall()
        patient_cols = {row[1] for row in patient_info}
        if "created_at" not in patient_cols:
            conn.execute(text(
                "ALTER TABLE patients ADD COLUMN created_at DATETIME"
            ))
            # Backfill existing rows with current UTC timestamp
            conn.execute(text(
                "UPDATE patients SET created_at = datetime('now') WHERE created_at IS NULL"
            ))
        # SOS alerts table migration
        sos_info = conn.execute(text("PRAGMA table_info(sos_alerts)")).fetchall()
        sos_cols = {row[1] for row in sos_info}
        if "created_at" not in sos_cols:
            conn.execute(text(
                "ALTER TABLE sos_alerts ADD COLUMN created_at DATETIME"
            ))
            # Backfill existing alerts with their original timestamp
            conn.execute(text(
                "UPDATE sos_alerts SET created_at = timestamp WHERE created_at IS NULL"
            ))

# Resolve the backend directory (two levels up from this file) and construct a portable path for the SQLite DB.
BASE_DIR = Path(__file__).resolve().parents[1]
# Ensure the path uses forward slashes for the SQLite URL on Windows.
DATABASE_URL = f"sqlite:///{(BASE_DIR / 'neurowatch.db').as_posix()}"
engine = create_engine(DATABASE_URL, connect_args={"check_same_thread": False})
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


class Base(DeclarativeBase):
    """Base class for all ORM models."""

    pass


class PatientModel(Base):
    """ORM model for Patient."""

    __tablename__ = "patients"

    id = Column(Integer, primary_key=True, index=True)
    patient_id = Column(String, unique=True, index=True, nullable=False)
    name = Column(String, nullable=False)
    created_at = Column(DateTime(timezone=True), nullable=False, default=datetime.now(timezone.utc))



class SpeechTestModel(Base):
    """ORM model for SpeechTest results."""

    __tablename__ = "speech_tests"

    id = Column(Integer, primary_key=True, index=True)
    patient_id = Column(String, nullable=False, index=True)
    test_id = Column(String, nullable=False)
    timestamp = Column(DateTime(timezone=True), nullable=False)
    audio_duration = Column(Float, nullable=False)
    estimated_speech_duration = Column(Float, nullable=False)
    average_pause_duration = Column(Float, nullable=False)
    long_pause_count = Column(Integer, nullable=False)
    speech_activity_rate = Column(Float, nullable=False)
    deviation_score = Column(Float, nullable=False)
    status = Column(String, nullable=False)  # stable, attention, significant_change, baseline_establishing


class SOSAlertModel(Base):
    """ORM model for Patient SOS Emergency Alerts."""

    __tablename__ = "sos_alerts"

    id = Column(Integer, primary_key=True, index=True)
    patient_id = Column(String, nullable=False, index=True)
    timestamp = Column(DateTime(timezone=True), nullable=False, default=datetime.now(timezone.utc))
    status = Column(String, nullable=False)  # active, resolved
    created_at = Column(DateTime(timezone=True), nullable=False, default=datetime.now(timezone.utc))  # active, resolved
    message = Column(String, nullable=False, default="Emergency assistance requested.")
    resolved_at = Column(DateTime(timezone=True), nullable=True)


class CognitiveTestModel(Base):
    """ORM model for Cognitive Test results."""

    __tablename__ = "cognitive_tests"

    id = Column(Integer, primary_key=True, index=True)
    patient_id = Column(String, nullable=False, index=True)
    test_id = Column(String, nullable=False)
    timestamp = Column(DateTime(timezone=True), nullable=False, default=datetime.now(timezone.utc))
    orientation_score = Column(Float, nullable=False)
    memory_score = Column(Float, nullable=False)
    attention_score = Column(Float, nullable=False)
    reasoning_score = Column(Float, nullable=False)
    overall_score = Column(Float, nullable=False)
    status = Column(String, nullable=False)  # stable, attention, significant_change, baseline_establishing

def init_db() -> None:
    """Initialize database tables and run schema migrations."""
    Base.metadata.create_all(bind=engine)
    _run_migrations()


def get_db() -> Session:
    """Get database session for dependency injection."""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
