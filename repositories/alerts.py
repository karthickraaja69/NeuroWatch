"""Repository for SOS emergency alerts."""

from datetime import datetime, timezone
from typing import Optional

from sqlalchemy.orm import Session

from app.database import PatientModel, SOSAlertModel
from app.repositories.mock_data import PATIENTS


class AlertRepository:
    """Repository operations for SOS emergency alerts."""

    @staticmethod
    def get_patient_name(db: Session, patient_id: str) -> str:
        """Resolve patient display name from database or seed data."""
        db_patient = db.query(PatientModel).filter(PatientModel.patient_id == patient_id).first()
        if db_patient and db_patient.name and db_patient.name != f"Patient {patient_id}":
            return db_patient.name
        
        seed_match = next((p for p in PATIENTS if p.patient_id == patient_id), None)
        if seed_match:
            return seed_match.name
        
        return db_patient.name if db_patient else f"Patient {patient_id}"

    @staticmethod
    def create_sos_alert(db: Session, patient_id: str, message: Optional[str] = None) -> tuple[SOSAlertModel, str]:
        """Create and persist an active SOS alert for a patient."""
        alert_msg = message or "Emergency assistance requested."
        alert = SOSAlertModel(
            patient_id=patient_id,
            timestamp=datetime.now(timezone.utc),
            status="active",
            message=alert_msg,
        )
        db.add(alert)
        db.commit()
        db.refresh(alert)
        
        patient_name = AlertRepository.get_patient_name(db, patient_id)
        return alert, patient_name

    @staticmethod
    def list_active_alerts(db: Session) -> list[tuple[SOSAlertModel, str]]:
        """Retrieve all active (unresolved) SOS alerts ordered newest first."""
        alerts = (
            db.query(SOSAlertModel)
            .filter(SOSAlertModel.status == "active")
            .order_by(SOSAlertModel.timestamp.desc())
            .all()
        )
        results = []
        for alert in alerts:
            patient_name = AlertRepository.get_patient_name(db, alert.patient_id)
            results.append((alert, patient_name))
        return results

    @staticmethod
    def resolve_alert(db: Session, alert_id: int) -> Optional[tuple[SOSAlertModel, str]]:
        """Mark an SOS alert as resolved."""
        alert = db.query(SOSAlertModel).filter(SOSAlertModel.id == alert_id).first()
        if alert is None:
            return None
        
        alert.status = "resolved"
        alert.resolved_at = datetime.now(timezone.utc)
        db.commit()
        db.refresh(alert)
        
        patient_name = AlertRepository.get_patient_name(db, alert.patient_id)
        return alert, patient_name
