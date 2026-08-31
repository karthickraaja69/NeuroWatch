from datetime import datetime, timezone
from typing import Optional
from sqlalchemy.orm import Session

from app.database import PatientModel, SpeechTestModel
from app.repositories.mock_data import HISTORY, PATIENTS
from app.schemas import AssessmentHistoryItem, Patient


def list_patients(db: Optional[Session] = None) -> list[Patient]:
    """List patients, updating statuses with live SQLite database records when available."""
    patient_dict: dict[str, Patient] = {p.patient_id: p for p in PATIENTS}
    
    if db is not None:
        db_patients = db.query(PatientModel).all()
        for db_patient in db_patients:
            latest_test = (
                db.query(SpeechTestModel)
                .filter(SpeechTestModel.patient_id == db_patient.patient_id)
                .order_by(SpeechTestModel.timestamp.desc())
                .first()
            )
            
            existing_seed = patient_dict.get(db_patient.patient_id)
            name = db_patient.name if db_patient.name and db_patient.name != f"Patient {db_patient.patient_id}" else (existing_seed.name if existing_seed else db_patient.name)
            
            if latest_test:
                raw_status = latest_test.status
                mapped_status = "alert" if raw_status == "significant_change" else ("attention" if raw_status == "attention" else "stable")
                speech_trend = "Stable" if mapped_status == "stable" else ("Slight change" if mapped_status == "attention" else "Significant change")
                alerts = 1 if mapped_status in ("attention", "alert") else 0
                
                patient_dict[db_patient.patient_id] = Patient(
                    patient_id=db_patient.patient_id,
                    name=name,
                    status=mapped_status,
                    last_check_in=latest_test.timestamp,
                    speech_trend=speech_trend,
                    cognitive_trend=existing_seed.cognitive_trend if existing_seed else "Stable",
                    alerts=alerts,
                )
            elif db_patient.patient_id not in patient_dict:
                patient_dict[db_patient.patient_id] = Patient(
                    patient_id=db_patient.patient_id,
                    name=db_patient.name,
                    status="stable",
                    last_check_in=db_patient.created_at,
                    speech_trend="Stable",
                    cognitive_trend="Stable",
                    alerts=0,
                )
                
    return list(patient_dict.values())


def get_patient_history(db: Optional[Session] = None, patient_id: str = "") -> list[AssessmentHistoryItem]:
    """Retrieve patient assessment history from SQLite database, combining live and seed items."""
    db_items: list[AssessmentHistoryItem] = []
    
    if db is not None and patient_id:
        db_tests = (
            db.query(SpeechTestModel)
            .filter(SpeechTestModel.patient_id == patient_id)
            .order_by(SpeechTestModel.timestamp.desc())
            .all()
        )
        for test in db_tests:
            mapped_status = "attention" if test.status in ("attention", "significant_change") else "stable"
            msg = (
                "Significant change from personal baseline."
                if test.status == "significant_change"
                else ("Slight change from personal baseline." if test.status == "attention" else "Speech pattern within recent personal range.")
            )
            db_items.append(
                AssessmentHistoryItem(
                    patient_id=test.patient_id,
                    test_id=test.test_id,
                    timestamp=test.timestamp,
                    status=mapped_status,
                    deviation_score=round(test.deviation_score, 2),
                    speech_rate=int(test.speech_activity_rate),
                    pause_score=round(test.average_pause_duration, 2),
                    message=msg,
                )
            )
            
    seed_items = HISTORY.get(patient_id, [])
    # Filter out seed items if matching test_id already exists in db_items
    db_test_ids = {item.test_id for item in db_items}
    combined = db_items + [item for item in seed_items if item.test_id not in db_test_ids]
    
    def sort_key(item: AssessmentHistoryItem) -> datetime:
        dt = item.timestamp
        return dt if dt.tzinfo is not None else dt.replace(tzinfo=timezone.utc)
        
    combined.sort(key=sort_key, reverse=True)
    return combined
