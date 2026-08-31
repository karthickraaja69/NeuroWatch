"""Baseline calculation and deviation score logic."""

from dataclasses import dataclass


@dataclass(frozen=True)
class BaselineFeatures:
    """Baseline features calculated from previous tests."""

    test_count: int
    speech_activity_rate: float
    average_pause_duration: float
    long_pause_count: float


@dataclass(frozen=True)
class DeviationResult:
    """Result of deviation calculation."""

    deviation_score: float  # 0.0 to 1.0
    status: str  # "stable", "attention", "significant_change", "baseline_establishing"
    monitoring_message: str


class BaselineCalculator:
    """Calculate patient's speech baseline from previous tests."""

    MIN_TESTS_FOR_BASELINE = 3

    @staticmethod
    def calculate_deviation(
        current_speech_activity_rate: float,
        current_average_pause_duration: float,
        current_long_pause_count: int,
        baseline: BaselineFeatures,
    ) -> DeviationResult:
        """
        Calculate normalized deviation between current test and baseline.

        Formula:
        1. Normalize each feature difference by the baseline value (or 1.0 if baseline is 0).
        2. Cap absolute differences at 1.0.
        3. Average the three normalized differences.
        4. Classify based on thresholds.

        Thresholds (prototype, not clinical):
        - 0.00 - 0.30 → stable
        - 0.30 - 0.60 → attention
        - 0.60 - 1.00 → significant_change
        """
        # Calculate normalized differences for each feature
        # Speech activity rate: higher is better, so deviation is (baseline - current) / baseline
        sar_diff = (baseline.speech_activity_rate - current_speech_activity_rate) / max(baseline.speech_activity_rate, 1.0)
        sar_deviation = min(abs(sar_diff), 1.0)

        # Average pause duration: lower is better, so deviation is (current - baseline) / baseline
        apd_diff = (current_average_pause_duration - baseline.average_pause_duration) / max(baseline.average_pause_duration, 0.1)
        apd_deviation = min(abs(apd_diff), 1.0)

        # Long pause count: lower is better
        lpc_diff = (current_long_pause_count - baseline.long_pause_count) / max(baseline.long_pause_count, 1.0)
        lpc_deviation = min(abs(lpc_diff), 1.0)

        # Combine into single deviation score (average of the three normalized deviations)
        deviation_score = (sar_deviation + apd_deviation + lpc_deviation) / 3.0
        deviation_score = min(deviation_score, 1.0)

        # Classify status based on thresholds
        if deviation_score < 0.30:
            status = "stable"
            monitoring_message = "Your speech patterns are stable. Continue regular monitoring."
        elif deviation_score < 0.60:
            status = "attention"
            monitoring_message = "A change in your speech patterns has been detected. Please continue regular monitoring."
        else:
            status = "significant_change"
            monitoring_message = "A significant change in your speech patterns has been detected. Please consult with your healthcare provider."

        return DeviationResult(
            deviation_score=deviation_score,
            status=status,
            monitoring_message=monitoring_message,
        )

    @staticmethod
    def create_baseline_unavailable_result() -> DeviationResult:
        """Create result when baseline is not yet available."""
        return DeviationResult(
            deviation_score=0.0,
            status="baseline_establishing",
            monitoring_message="Continue regular speech tests to establish your personal baseline.",
        )
