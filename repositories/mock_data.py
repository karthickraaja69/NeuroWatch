from datetime import datetime, timezone

from app.schemas import AssessmentHistoryItem, Patient


def utc_time(hour: int, minute: int) -> datetime:
    return datetime(2026, 8, 21, hour, minute, tzinfo=timezone.utc)


PATIENTS = [
    Patient(patient_id="NW-1024", name="Ravi Kumar", status="stable", last_check_in=utc_time(20, 42), speech_trend="Stable", cognitive_trend="Stable", alerts=0),
    Patient(patient_id="NW-1031", name="Arjun Menon", status="attention", last_check_in=utc_time(19, 15), speech_trend="Slight change", cognitive_trend="Stable", alerts=1),
    Patient(patient_id="NW-1008", name="Priya Shah", status="alert", last_check_in=utc_time(18, 52), speech_trend="Significant change", cognitive_trend="Slight change", alerts=2),
    Patient(patient_id="NW-1017", name="Nikhil Rao", status="stable", last_check_in=utc_time(18, 35), speech_trend="Stable", cognitive_trend="Stable", alerts=0),
    Patient(patient_id="NW-1028", name="Meena Iyer", status="stable", last_check_in=utc_time(17, 48), speech_trend="Stable", cognitive_trend="Stable", alerts=0),
    Patient(patient_id="NW-1012", name="Sanjay Das", status="attention", last_check_in=datetime(2026, 8, 20, 20, 10, tzinfo=timezone.utc), speech_trend="Slight change", cognitive_trend="Stable", alerts=1),
]

HISTORY = {
    "NW-1024": [
        AssessmentHistoryItem(patient_id="NW-1024", test_id="speech-aug21-001", timestamp=utc_time(20, 42), status="stable", deviation_score=0.18, speech_rate=105, pause_score=0.12, message="No significant change from personal baseline."),
        AssessmentHistoryItem(patient_id="NW-1024", test_id="speech-aug20-001", timestamp=datetime(2026, 8, 20, 20, 37, tzinfo=timezone.utc), status="stable", deviation_score=0.16, speech_rate=107, pause_score=0.11, message="Speech pattern within recent personal range."),
        AssessmentHistoryItem(patient_id="NW-1024", test_id="speech-aug19-001", timestamp=datetime(2026, 8, 19, 20, 51, tzinfo=timezone.utc), status="attention", deviation_score=0.34, speech_rate=98, pause_score=0.21, message="Slight change from personal baseline; review recommended."),
    ],
}
