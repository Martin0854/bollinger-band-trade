"""
Unit tests for confidence scoring system.
Tests MUST be written FIRST and FAIL before implementation (TDD).
User Story: US4 - Multi-Level Signal Confidence Scoring System

Test Coverage:
- T043-T046: Confidence scoring calculation and validation
"""

import pytest
from hypothesis import given, strategies as st

# These imports will fail initially until implementation (TDD)
try:
    from src.signals.confidence import SignalConfidence
except ImportError:
    SignalConfidence = None


# ========================================================================
# T043: Unit test for SignalConfidence.calculate_score()
# ========================================================================

@pytest.mark.skipif(SignalConfidence is None, reason="SignalConfidence not yet implemented")
class TestSignalConfidenceCalculation:
    """Test confidence score calculation with different filter combinations."""

    def test_all_filters_pass_100_points(self):
        """T043: Test all filters pass → 100 points (25+25+20+30)."""
        # Given: SignalConfidence with default scoring
        confidence = SignalConfidence(
            threshold=60,
            scoring={
                'base_score': 25,
                'volume_score': 25,
                'rsi_score': 20,
                'macd_score': 30
            }
        )

        # When: All filters pass
        score = confidence.calculate_score(
            volume_pass=True,
            rsi_pass=True,
            macd_pass=True
        )

        # Then: Score should be 100
        assert score == 100

    def test_only_volume_and_rsi_pass_70_points(self):
        """T043: Test only volume + RSI pass → 70 points (25+25+20)."""
        # Given: SignalConfidence with default scoring
        confidence = SignalConfidence(threshold=60)

        # When: Only volume and RSI pass
        score = confidence.calculate_score(
            volume_pass=True,
            rsi_pass=True,
            macd_pass=False
        )

        # Then: Score should be 70 (base + volume + rsi)
        assert score == 70

    def test_only_base_bollinger_25_points(self):
        """T043: Test only base (Bollinger) → 25 points."""
        # Given: SignalConfidence
        confidence = SignalConfidence(threshold=60)

        # When: No filters pass
        score = confidence.calculate_score(
            volume_pass=False,
            rsi_pass=False,
            macd_pass=False
        )

        # Then: Score should be 25 (base only)
        assert score == 25

    def test_custom_scoring_weights(self):
        """T043: Test custom scoring weights."""
        # Given: SignalConfidence with custom weights
        confidence = SignalConfidence(
            threshold=50,
            scoring={
                'base_score': 30,
                'volume_score': 20,
                'rsi_score': 25,
                'macd_score': 25
            }
        )

        # When: Volume and MACD pass
        score = confidence.calculate_score(
            volume_pass=True,
            rsi_pass=False,
            macd_pass=True
        )

        # Then: Score should be custom (30 + 20 + 25 = 75)
        assert score == 75


# ========================================================================
# T044: Unit test for SignalConfidence.meets_threshold()
# ========================================================================

@pytest.mark.skipif(SignalConfidence is None, reason="SignalConfidence not yet implemented")
class TestSignalConfidenceThreshold:
    """Test confidence threshold validation."""

    def test_score_above_threshold_returns_true(self):
        """T044: Test score=70, threshold=60 → True."""
        # Given: SignalConfidence with threshold=60
        confidence = SignalConfidence(threshold=60)

        # When: Score is 70
        meets = confidence.meets_threshold(70)

        # Then: Should meet threshold
        assert meets is True

    def test_score_below_threshold_returns_false(self):
        """T044: Test score=50, threshold=60 → False."""
        # Given: SignalConfidence with threshold=60
        confidence = SignalConfidence(threshold=60)

        # When: Score is 50
        meets = confidence.meets_threshold(50)

        # Then: Should not meet threshold
        assert meets is False

    def test_score_equal_threshold_returns_true(self):
        """T044: Test score=60, threshold=60 → True (boundary)."""
        # Given: SignalConfidence with threshold=60
        confidence = SignalConfidence(threshold=60)

        # When: Score equals threshold
        meets = confidence.meets_threshold(60)

        # Then: Should meet threshold (>= comparison)
        assert meets is True


# ========================================================================
# T045: Unit test for confidence score validation
# ========================================================================

@pytest.mark.skipif(SignalConfidence is None, reason="SignalConfidence not yet implemented")
class TestSignalConfidenceValidation:
    """Test validation rules for confidence scoring configuration."""

    def test_total_scoring_exceeds_100_raises_error(self):
        """T045: Test total scoring exceeds 100 → ValidationError."""
        from pydantic import ValidationError

        # When/Then: Creating with total > 100 should raise error
        with pytest.raises(ValueError) as exc_info:
            SignalConfidence(
                threshold=60,
                scoring={
                    'base_score': 30,
                    'volume_score': 30,
                    'rsi_score': 30,
                    'macd_score': 30  # Total = 120
                }
            )

        assert "total scoring" in str(exc_info.value).lower()

    def test_negative_scores_raise_error(self):
        """T045: Test negative scores → ValidationError."""
        # When/Then: Negative score should raise error
        with pytest.raises(ValueError) as exc_info:
            SignalConfidence(
                threshold=60,
                scoring={
                    'base_score': 25,
                    'volume_score': -10,  # Negative!
                    'rsi_score': 20,
                    'macd_score': 30
                }
            )

        assert "negative" in str(exc_info.value).lower() or "greater than" in str(exc_info.value).lower()

    def test_threshold_exceeds_max_achievable_score_raises_error(self):
        """T045: Test threshold > max_achievable_score → ValidationError."""
        # When/Then: Threshold > 100 should raise error
        with pytest.raises(ValueError) as exc_info:
            SignalConfidence(
                threshold=110,  # > max possible score of 100
                scoring={
                    'base_score': 25,
                    'volume_score': 25,
                    'rsi_score': 20,
                    'macd_score': 30
                }
            )

        assert "threshold" in str(exc_info.value).lower()

    def test_threshold_zero_is_valid(self):
        """T045: Test threshold=0 is valid (accept all signals)."""
        # When: Creating with threshold=0
        confidence = SignalConfidence(threshold=0)

        # Then: Should be valid
        assert confidence.threshold == 0


# ========================================================================
# T046: Property-based test for confidence scoring using hypothesis
# ========================================================================

@pytest.mark.skipif(SignalConfidence is None, reason="SignalConfidence not yet implemented")
class TestSignalConfidenceProperties:
    """Property-based tests for confidence scoring invariants."""

    @given(
        volume_pass=st.booleans(),
        rsi_pass=st.booleans(),
        macd_pass=st.booleans()
    )
    def test_property_score_always_between_0_and_100(self, volume_pass, rsi_pass, macd_pass):
        """T046: Property - Score always between 0-100."""
        # Given: SignalConfidence with default scoring
        confidence = SignalConfidence(threshold=60)

        # When: Calculate score with any combination of filters
        score = confidence.calculate_score(volume_pass, rsi_pass, macd_pass)

        # Property: Score must be between 0 and 100
        assert 0 <= score <= 100

    @given(
        base=st.integers(min_value=1, max_value=25),
        volume=st.integers(min_value=1, max_value=25),
        rsi=st.integers(min_value=1, max_value=25),
        macd=st.integers(min_value=1, max_value=25)
    )
    def test_property_more_filters_passed_higher_score(self, base, volume, rsi, macd):
        """T046: Property - More filters passed → higher score."""
        # Given: Valid scoring configuration
        total = base + volume + rsi + macd
        if total > 100:
            # Skip invalid combinations
            return

        # Set threshold to be achievable (at most total/2 to ensure meaningful test)
        threshold = min(total // 2, total)

        confidence = SignalConfidence(
            threshold=threshold,
            scoring={
                'base_score': base,
                'volume_score': volume,
                'rsi_score': rsi,
                'macd_score': macd
            }
        )

        # When: Calculate scores with increasing filter passes
        score_none = confidence.calculate_score(False, False, False)
        score_one = confidence.calculate_score(True, False, False)
        score_two = confidence.calculate_score(True, True, False)
        score_all = confidence.calculate_score(True, True, True)

        # Property: More filters → higher or equal score
        assert score_none <= score_one <= score_two <= score_all

    def test_property_score_deterministic(self):
        """T046: Property - Same inputs → same score (deterministic)."""
        # Given: SignalConfidence
        confidence = SignalConfidence(threshold=60)

        # When: Calculate score multiple times with same inputs
        score1 = confidence.calculate_score(True, True, False)
        score2 = confidence.calculate_score(True, True, False)
        score3 = confidence.calculate_score(True, True, False)

        # Property: Should always return same score
        assert score1 == score2 == score3
