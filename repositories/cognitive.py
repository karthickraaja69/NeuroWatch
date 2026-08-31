"""Repository for cognitive test data access and baseline calculations."""

from datetime import datetime
from statistics import mean
from typing import Optional, List

from sqlalchemy.orm import Session

from app.database import CognitiveTestModel, PatientModel

class CognitiveTestRepository:
    """Repository for cognitive test operations and baseline calculations."""

    @staticmethod
    def create_patient(db: Session, patient_id: str, name: str) -> PatientModel:
        patient = PatientModel(patient_id=patient_id, name=name)
        db.add(patient)
        db.commit()
        db.refresh(patient)
        return patient

    @staticmethod
    def get_patient(db: Session, patient_id: str) -> Optional[PatientModel]:
        return db.query(PatientModel).filter(PatientModel.patient_id == patient_id).first()

    @staticmethod
    def get_or_create_patient(db: Session, patient_id: str, default_name: str = "Unknown") -> PatientModel:
        patient = CognitiveTestRepository.get_patient(db, patient_id)
        if patient is None:
            patient = CognitiveTestRepository.create_patient(db, patient_id, default_name)
        return patient

    @staticmethod
    def save_cognitive_test(
        db: Session,
        patient_id: str,
        test_id: str,
        timestamp: datetime,
        orientation_score: float,
        memory_score: float,
        attention_score: float,
        reasoning_score: float,
        overall_score: float,
        status: str,
    ) -> CognitiveTestModel:
        test = CognitiveTestModel(
            patient_id=patient_id,
            test_id=test_id,
            timestamp=timestamp,
            orientation_score=orientation_score,
            memory_score=memory_score,
            attention_score=attention_score,
            reasoning_score=reasoning_score,
            overall_score=overall_score,
            status=status,
        )
        db.add(test)
        db.commit()
        db.refresh(test)
        return test

    @staticmethod
    def get_previous_tests(db: Session, patient_id: str, limit: int = 5) -> List[CognitiveTestModel]:
        return (
            db.query(CognitiveTestModel)
            .filter(CognitiveTestModel.patient_id == patient_id)
            .order_by(CognitiveTestModel.timestamp.desc())
            .limit(limit)
            .all()
        )

    @staticmethod
    def calculate_baseline(
        db: Session,
        patient_id: str,
        include_current: Optional[dict] = None,
    ) -> Optional[dict]:
        """Calculate baseline of overall_score from previous valid tests.
        Returns None if fewer than 3 valid tests exist.
        """
        previous = CognitiveTestRepository.get_previous_tests(db, patient_id, limit=5)
        # Exclude baseline_establishing tests
        valid = [t for t in previous if t.status != "baseline_establishing"]
        scores = [t.overall_score for t in valid]
        if include_current:
            scores.append(include_current["overall_score"])
        if len(scores) < 3:
            return None
        return {
            "count": len(scores),
            "mean": mean(scores),
        }

    @staticmethod
    def determine_status(
        db: Session,
        patient_id: str,
        overall_score: float,
    ) -> str:
        """Determine status based on baseline logic.
        Returns one of the four statuses.
        """
        baseline = CognitiveTestRepository.calculate_baseline(db, patient_id)
        if baseline is None:
            return "baseline_establishing"
        deviation = abs(overall_score - baseline["mean"])
        if deviation < 0.1:
            return "stable"
        if deviation < 0.2:
            return "attention"
        return "significant_change"
