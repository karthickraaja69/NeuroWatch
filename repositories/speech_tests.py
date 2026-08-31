"""Repository for speech test data access and baseline calculations."""

from datetime import datetime
from statistics import mean
from typing import Optional

from sqlalchemy.orm import Session

from app.database import PatientModel, SpeechTestModel


class SpeechTestRepository:
    """Repository for speech test operations and baseline calculations."""

    @staticmethod
    def create_patient(db: Session, patient_id: str, name: str) -> PatientModel:
        """Create a new patient."""
        patient = PatientModel(patient_id=patient_id, name=name)
        db.add(patient)
        db.commit()
        db.refresh(patient)
        return patient

    @staticmethod
    def get_patient(db: Session, patient_id: str) -> Optional[PatientModel]:
        """Get a patient by patient_id."""
        return db.query(PatientModel).filter(PatientModel.patient_id == patient_id).first()

    @staticmethod
    def get_or_create_patient(db: Session, patient_id: str, default_name: str = "Unknown") -> PatientModel:
        """Get a patient or create if not exists."""
        patient = SpeechTestRepository.get_patient(db, patient_id)
        if patient is None:
            patient = SpeechTestRepository.create_patient(db, patient_id, default_name)
        return patient

    @staticmethod
    def save_speech_test(
        db: Session,
        patient_id: str,
        test_id: str,
        timestamp: datetime,
        audio_duration: float,
        estimated_speech_duration: float,
        average_pause_duration: float,
        long_pause_count: int,
        speech_activity_rate: float,
        deviation_score: float,
        status: str,
    ) -> SpeechTestModel:
        """Save a speech test result to the database."""
        test = SpeechTestModel(
            patient_id=patient_id,
            test_id=test_id,
            timestamp=timestamp,
            audio_duration=audio_duration,
            estimated_speech_duration=estimated_speech_duration,
            average_pause_duration=average_pause_duration,
            long_pause_count=long_pause_count,
            speech_activity_rate=speech_activity_rate,
            deviation_score=deviation_score,
            status=status,
        )
        db.add(test)
        db.commit()
        db.refresh(test)
        return test

    @staticmethod
    def get_previous_tests(db: Session, patient_id: str, limit: int = 5) -> list[SpeechTestModel]:
        """Get previous speech tests for a patient, ordered by timestamp (newest first)."""
        return (
            db.query(SpeechTestModel)
            .filter(SpeechTestModel.patient_id == patient_id)
            .order_by(SpeechTestModel.timestamp.desc())
            .limit(limit)
            .all()
        )

    @staticmethod
    def calculate_baseline(
        db: Session,
        patient_id: str,
        include_current: Optional[dict] = None,
    ) -> Optional[dict]:
        """
        Calculate baseline from previous 5 tests and optional current test features.
        
        Returns None if fewer than 3 valid tests exist.
        Otherwise returns dict with:
        - test_count: number of tests used
        - speech_activity_rate: mean
        - average_pause_duration: mean
        - long_pause_count: mean
        """
        previous_tests = SpeechTestRepository.get_previous_tests(db, patient_id, limit=5)
        
        # Filter for stable/valid tests (exclude baseline_establishing status)
        valid_tests = [t for t in previous_tests if t.status != "baseline_establishing"]
        
        rates = [t.speech_activity_rate for t in valid_tests]
        pauses = [t.average_pause_duration for t in valid_tests]
        long_pauses = [t.long_pause_count for t in valid_tests]

        if include_current:
            rates.append(include_current["speech_activity_rate"])
            pauses.append(include_current["average_pause_duration"])
            long_pauses.append(include_current["long_pause_count"])

        if len(rates) < 3:
            return None

        return {
            "test_count": len(rates),
            "speech_activity_rate": mean(rates),
            "average_pause_duration": mean(pauses),
            "long_pause_count": mean(long_pauses),
        }

    @staticmethod
    def get_previous_valid_tests_count(db: Session, patient_id: str) -> int:
        """Get count of valid (non-baseline_establishing) tests for a patient."""
        count = (
            db.query(SpeechTestModel)
            .filter(SpeechTestModel.patient_id == patient_id)
            .filter(SpeechTestModel.status != "baseline_establishing")
            .count()
        )
        return count
