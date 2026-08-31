from dataclasses import dataclass
from datetime import datetime
from io import BytesIO
from typing import Literal, Optional, Protocol

import av
import numpy as np
from sqlalchemy.orm import Session

from app.schemas import FeatureDict, SpeechTestResult
from app.services.baseline import BaselineCalculator, BaselineFeatures


@dataclass(frozen=True)
class PreparedAudio:
    """Decoded mono PCM samples ready for numerical analysis."""

    samples: np.ndarray
    sample_rate: int
    channel_count: int
    duration: float
    content_type: str


@dataclass(frozen=True)
class SpeechFeatures:
    """Prototype signal features; values are not clinically validated."""

    audio_duration: float
    estimated_speech_duration: float
    speech_rate: int
    average_pause_duration: float
    long_pause_count: int
    transcription_score: float


@dataclass(frozen=True)
class BaselineComparison:
    deviation_score: float
    status: Literal["stable", "attention", "significant_change"]


class AudioPreprocessor(Protocol):
    def prepare(self, audio_bytes: bytes, content_type: str) -> PreparedAudio: ...


class SpeechFeatureExtractor(Protocol):
    def extract(self, audio: PreparedAudio) -> SpeechFeatures: ...


class BaselineComparator(Protocol):
    def compare(self, patient_id: str, features: SpeechFeatures) -> BaselineComparison: ...


class MonitoringStatusClassifier(Protocol):
    def classify(self, comparison: BaselineComparison) -> Literal["stable", "attention", "significant_change"]: ...


class PyAVAudioPreprocessor:
    """Decode browser WebM/Opus or other PyAV-supported audio into mono float PCM."""

    def prepare(self, audio_bytes: bytes, content_type: str) -> PreparedAudio:
        if not audio_bytes:
            raise ValueError("Audio cannot be empty.")
        try:
            container = av.open(BytesIO(audio_bytes), mode="r")
            stream = next((candidate for candidate in container.streams.audio), None)
            if stream is None:
                container.close()
                raise ValueError("Audio contains no audio stream.")
            resampler = av.audio.resampler.AudioResampler(
                format="fltp",
                layout="mono",
                rate=stream.rate,
            )
            decoded_frames = []
            for frame in container.decode(stream):
                decoded_frames.extend(resampler.resample(frame))
            decoded_frames.extend(resampler.resample(None))
            frames = [frame.to_ndarray() for frame in decoded_frames]
            sample_rate = stream.rate or 0
            channel_count = stream.channels or 0
            container.close()
        except ValueError:
            raise
        except Exception as error:
            raise ValueError("Audio format could not be decoded by PyAV.") from error

        if not frames or sample_rate <= 0 or channel_count <= 0:
            raise ValueError("Audio decoded without usable samples.")

        samples = np.concatenate(frames, axis=1 if frames[0].ndim == 2 else 0)
        if samples.ndim == 2:
            samples = samples[0]
        samples = np.asarray(samples, dtype=np.float32).reshape(-1)
        if samples.size == 0:
            raise ValueError("Audio decoded without usable samples.")

        return PreparedAudio(
            samples=samples,
            sample_rate=sample_rate,
            channel_count=channel_count,
            duration=float(samples.size / sample_rate),
            content_type=content_type,
        )


class EnergySpeechFeatureExtractor:
    """Estimate activity and pauses from short-window RMS energy."""

    def __init__(self, *, window_seconds: float = 0.02, long_pause_seconds: float = 0.5) -> None:
        self.window_seconds = window_seconds
        self.long_pause_seconds = long_pause_seconds

    def extract(self, audio: PreparedAudio) -> SpeechFeatures:
        window_size = max(1, int(audio.sample_rate * self.window_seconds))
        window_count = int(np.ceil(audio.samples.size / window_size))
        padded = np.pad(audio.samples, (0, window_count * window_size - audio.samples.size))
        rms = np.sqrt(np.mean(padded.reshape(window_count, window_size) ** 2, axis=1))
        peak = float(rms.max())
        threshold = max(0.01, peak * 0.1)
        active = rms > threshold
        active_samples = int(active.sum() * window_size)
        estimated_speech_duration = min(audio.duration, active_samples / audio.sample_rate)

        pause_lengths: list[int] = []
        index = 0
        while index < active.size:
            if active[index]:
                index += 1
                continue
            start = index
            while index < active.size and not active[index]:
                index += 1
            if start > 0 and index < active.size:
                pause_lengths.append(index - start)

        pause_durations = [length * self.window_seconds for length in pause_lengths]
        average_pause_duration = float(np.mean(pause_durations)) if pause_durations else 0.0
        long_pause_count = sum(duration >= self.long_pause_seconds for duration in pause_durations)
        activity_ratio = estimated_speech_duration / audio.duration if audio.duration else 0.0
        speech_rate = int(round(120 * activity_ratio))
        return SpeechFeatures(
            audio_duration=audio.duration,
            estimated_speech_duration=estimated_speech_duration,
            speech_rate=speech_rate,
            average_pause_duration=average_pause_duration,
            long_pause_count=long_pause_count,
            transcription_score=0.0,
        )


class PrototypeAudioPreprocessor:
    """Deterministic fallback preprocessor for environments without a decoder."""

    def prepare(self, audio_bytes: bytes, content_type: str) -> PreparedAudio:
        if not audio_bytes:
            raise ValueError("Audio cannot be empty.")
        return PreparedAudio(np.zeros(1, dtype=np.float32), 1, 1, 1.0, content_type)


class PrototypeFeatureExtractor:
    """Deterministic fallback retained for decoder-unavailable development."""

    def extract(self, audio: PreparedAudio) -> SpeechFeatures:
        return SpeechFeatures(1.0, 0.75, 105, 0.42, 1, 0.0)


class PrototypeBaselineComparator:
    def compare(self, patient_id: str, features: SpeechFeatures) -> BaselineComparison:
        return BaselineComparison(deviation_score=0.18, status="stable")


class PrototypeMonitoringStatusClassifier:
    def classify(self, comparison: BaselineComparison) -> Literal["stable", "attention", "significant_change"]:
        return comparison.status


def analyze_speech(
    audio_bytes: bytes,
    content_type: str,
    patient_id: str,
    *,
    preprocessor: AudioPreprocessor | None = None,
    feature_extractor: SpeechFeatureExtractor | None = None,
    baseline_comparator: BaselineComparator | None = None,
    status_classifier: MonitoringStatusClassifier | None = None,
) -> tuple[SpeechFeatures, BaselineComparison]:
    """Run decoding, prototype features, baseline comparison, and status classification."""
    preprocessor = preprocessor or PyAVAudioPreprocessor()
    feature_extractor = feature_extractor or EnergySpeechFeatureExtractor()
    baseline_comparator = baseline_comparator or PrototypeBaselineComparator()
    status_classifier = status_classifier or PrototypeMonitoringStatusClassifier()
    prepared_audio = preprocessor.prepare(audio_bytes, content_type)
    features = feature_extractor.extract(prepared_audio)
    comparison = baseline_comparator.compare(patient_id, features)
    status_classifier.classify(comparison)
    return features, comparison


def analyze_speech_test(
    *,
    patient_id: str,
    test_id: str,
    audio_filename: str,
    audio_content_type: str,
    audio_size_bytes: int,
    audio_bytes: bytes,
    timestamp: datetime,
    db: Optional[Session] = None,
) -> SpeechTestResult:
    features, comparison = analyze_speech(audio_bytes, audio_content_type, patient_id)
    
    # Calculate baseline and deviation if database is available
    baseline_available = False
    baseline_test_count = 0
    deviation_score = comparison.deviation_score
    status = comparison.status
    monitoring_message = comparison.status
    current_features_dict: Optional[FeatureDict] = None
    baseline_features_dict: Optional[FeatureDict] = None
    
    if db is not None:
        from app.repositories.speech_tests import SpeechTestRepository
        
        # Ensure patient exists
        SpeechTestRepository.get_or_create_patient(db, patient_id, f"Patient {patient_id}")
        
        # Convert speech_rate (activity-based percentage estimate) to speech_activity_rate
        speech_activity_rate = features.speech_rate  # Already a percentage (0-100)
        
        current_features_dict = FeatureDict(
            speech_activity_rate=speech_activity_rate,
            average_pause_duration=features.average_pause_duration,
            long_pause_count=features.long_pause_count,
            estimated_speech_duration=features.estimated_speech_duration,
        )
        
        current_raw_dict = {
            "speech_activity_rate": float(speech_activity_rate),
            "average_pause_duration": float(features.average_pause_duration),
            "long_pause_count": float(features.long_pause_count),
        }

        # Get baseline from previous tests + current test
        baseline_data = SpeechTestRepository.calculate_baseline(db, patient_id, include_current=current_raw_dict)
        
        if baseline_data is not None and baseline_data["test_count"] >= 3:
            # Baseline available
            baseline_available = True
            baseline_test_count = baseline_data["test_count"]
            
            baseline_features = BaselineFeatures(
                test_count=baseline_data["test_count"],
                speech_activity_rate=baseline_data["speech_activity_rate"],
                average_pause_duration=baseline_data["average_pause_duration"],
                long_pause_count=baseline_data["long_pause_count"],
            )
            
            baseline_features_dict = FeatureDict(
                speech_activity_rate=baseline_features.speech_activity_rate,
                average_pause_duration=baseline_features.average_pause_duration,
                long_pause_count=int(baseline_features.long_pause_count),
                estimated_speech_duration=0.0,  # Not applicable for baseline
            )
            
            # Calculate deviation
            deviation_result = BaselineCalculator.calculate_deviation(
                current_speech_activity_rate=speech_activity_rate,
                current_average_pause_duration=features.average_pause_duration,
                current_long_pause_count=features.long_pause_count,
                baseline=baseline_features,
            )
            
            deviation_score = deviation_result.deviation_score
            status = deviation_result.status
            monitoring_message = deviation_result.monitoring_message
        else:
            # Not enough baseline data yet
            deviation_result = BaselineCalculator.create_baseline_unavailable_result()
            deviation_score = deviation_result.deviation_score
            status = deviation_result.status
            monitoring_message = deviation_result.monitoring_message
        
        # Save test result to database (persisting stable status for baseline establishing tests)
        SpeechTestRepository.save_speech_test(
            db=db,
            patient_id=patient_id,
            test_id=test_id,
            timestamp=timestamp,
            audio_duration=features.audio_duration,
            estimated_speech_duration=features.estimated_speech_duration,
            average_pause_duration=features.average_pause_duration,
            long_pause_count=features.long_pause_count,
            speech_activity_rate=speech_activity_rate,
            deviation_score=deviation_score,
            status="stable" if status == "baseline_establishing" else status,
        )
    
    return SpeechTestResult(
        patient_id=patient_id,
        test_id=test_id,
        status=status,
        deviation_score=deviation_score,
        audio_duration=features.audio_duration,
        estimated_speech_duration=features.estimated_speech_duration,
        speech_rate=features.speech_rate,
        pause_score=features.average_pause_duration,
        average_pause_duration=features.average_pause_duration,
        long_pause_count=features.long_pause_count,
        transcription_score=features.transcription_score,
        message="Audio decoded successfully. Prototype speech-monitoring features are not clinically validated.",
        monitoring_message=monitoring_message,
        audio_received=True,
        audio_filename=audio_filename,
        audio_content_type=audio_content_type,
        audio_size_bytes=audio_size_bytes,
        baseline_available=baseline_available,
        baseline_test_count=baseline_test_count,
        current_features=current_features_dict,
        baseline_features=baseline_features_dict,
    )
