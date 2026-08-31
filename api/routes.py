from datetime import datetime

from fastapi import APIRouter, Depends, File, Form, HTTPException, UploadFile
from sqlalchemy.orm import Session

from app.database import get_db
from app.repositories.alerts import AlertRepository
from app.repositories.patients import get_patient_history, list_patients
from app.repositories.speech_tests import SpeechTestRepository
from app.repositories.cognitive import CognitiveTestRepository
from app.schemas import AssessmentHistoryItem, Patient, SOSAlertResponse, SOSCreateRequest, SpeechTestResult, CognitiveTestRequest, CognitiveTestResponse
from app.services.speech_analysis import analyze_speech_test

router = APIRouter(prefix="/api")


@router.post("/speech-test", response_model=SpeechTestResult)
async def create_speech_test(
    audio: UploadFile = File(...),
    patient_id: str = Form(..., min_length=1),
    test_id: str = Form(..., min_length=1),
    timestamp: datetime = Form(...),
    db: Session = Depends(get_db),
) -> SpeechTestResult:
    audio_bytes = await audio.read()
    if not audio_bytes:
        raise HTTPException(status_code=400, detail="Uploaded audio file is empty.")

    try:
        return analyze_speech_test(
            patient_id=patient_id,
            test_id=test_id,
            audio_filename=audio.filename or "recording",
            audio_content_type=audio.content_type or "application/octet-stream",
            audio_size_bytes=len(audio_bytes),
            audio_bytes=audio_bytes,
            timestamp=timestamp,
            db=db,
        )
    except ValueError as error:
        raise HTTPException(status_code=400, detail=str(error)) from error


@router.get("/patients", response_model=list[Patient])
def get_patients(db: Session = Depends(get_db)) -> list[Patient]:
    return list_patients(db)


@router.get("/patients/{patient_id}/history", response_model=list[AssessmentHistoryItem])
def get_patient_assessments(patient_id: str, db: Session = Depends(get_db)) -> list[AssessmentHistoryItem]:
    return get_patient_history(db, patient_id)


@router.post("/patients/{patient_id}/sos", response_model=SOSAlertResponse)
def create_patient_sos(
    patient_id: str,
    payload: SOSCreateRequest = None,
    db: Session = Depends(get_db),
) -> SOSAlertResponse:
    if not patient_id or patient_id.strip() == "":
        raise HTTPException(status_code=400, detail="Invalid patient ID.")
    
    # Check if patient exists or registered in system
    existing_patient = SpeechTestRepository.get_patient(db, patient_id)
    known_seed = any(p.patient_id == patient_id for p in list_patients(db))
    if not existing_patient and not known_seed:
        raise HTTPException(status_code=404, detail=f"Patient '{patient_id}' not found.")
    
    # Ensure patient is recorded in PatientModel
    SpeechTestRepository.get_or_create_patient(db, patient_id, f"Patient {patient_id}")
    
    msg = payload.message if payload and payload.message else "Emergency assistance requested."
    alert, patient_name = AlertRepository.create_sos_alert(db, patient_id, msg)
    
    return SOSAlertResponse(
        id=alert.id,
        patient_id=alert.patient_id,
        patient_name=patient_name,
        timestamp=alert.timestamp,
        status=alert.status,
        message=alert.message,
        resolved_at=alert.resolved_at,
    )


@router.get("/alerts", response_model=list[SOSAlertResponse])
def get_active_alerts(db: Session = Depends(get_db)) -> list[SOSAlertResponse]:
    alerts_data = AlertRepository.list_active_alerts(db)
    return [
        SOSAlertResponse(
            id=alert.id,
            patient_id=alert.patient_id,
            patient_name=patient_name,
            timestamp=alert.timestamp,
            status=alert.status,
            message=alert.message,
            resolved_at=alert.resolved_at,
        )
        for alert, patient_name in alerts_data
    ]


@router.patch("/alerts/{alert_id}/resolve", response_model=SOSAlertResponse)
def resolve_alert(alert_id: int, db: Session = Depends(get_db)) -> SOSAlertResponse:
    result = AlertRepository.resolve_alert(db, alert_id)
    if result is None:
        raise HTTPException(status_code=404, detail=f"Alert with ID {alert_id} not found.")
    
    alert, patient_name = result
    return SOSAlertResponse(
        id=alert.id,
        patient_id=alert.patient_id,
        patient_name=patient_name,
        timestamp=alert.timestamp,
        status=alert.status,
        message=alert.message,
        resolved_at=alert.resolved_at,
    )
@router.post("/cognitive-test", response_model=CognitiveTestResponse)
async def create_cognitive_test(
    payload: CognitiveTestRequest,
    db: Session = Depends(get_db),
) -> CognitiveTestResponse:
    # Ensure patient exists
    patient = SpeechTestRepository.get_patient(db, payload.patient_id)
    if not patient:
        raise HTTPException(status_code=404, detail=f"Patient '{payload.patient_id}' not found.")
    # Ensure patient record exists
    SpeechTestRepository.get_or_create_patient(db, payload.patient_id, f"Patient {payload.patient_id}")
    # Determine status via repository logic
    status = CognitiveTestRepository.determine_status(db, payload.patient_id, payload.overall_score)
    test = CognitiveTestRepository.save_cognitive_test(
        db=db,
        patient_id=payload.patient_id,
        test_id=payload.test_id,
        timestamp=payload.timestamp,
        orientation_score=payload.orientation_score,
        memory_score=payload.memory_score,
        attention_score=payload.attention_score,
        reasoning_score=payload.reasoning_score,
        overall_score=payload.overall_score,
        status=status,
    )
    return CognitiveTestResponse(
        id=test.id,
        patient_id=test.patient_id,
        test_id=test.test_id,
        timestamp=test.timestamp,
        orientation_score=test.orientation_score,
        memory_score=test.memory_score,
        attention_score=test.attention_score,
        reasoning_score=test.reasoning_score,
        overall_score=test.overall_score,
        status=test.status,
        message=f"Cognitive assessment recorded with status '{test.status}'.",
    )

@router.get("/patients/{patient_id}/cognitive-history", response_model=list[CognitiveTestResponse])
def get_cognitive_history(patient_id: str, db: Session = Depends(get_db)) -> list[CognitiveTestResponse]:
    tests = CognitiveTestRepository.get_previous_tests(db, patient_id)
    return [
        CognitiveTestResponse(
            id=t.id,
            patient_id=t.patient_id,
            test_id=t.test_id,
            timestamp=t.timestamp,
            orientation_score=t.orientation_score,
            memory_score=t.memory_score,
            attention_score=t.attention_score,
            reasoning_score=t.reasoning_score,
            overall_score=t.overall_score,
            status=t.status,
            message="",
        )
        for t in tests
    ]
