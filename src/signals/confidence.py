"""
Signal Confidence Scoring (Entity 5: SignalConfidence)
Multi-indicator confidence evaluation system (0-100 points).
Implements Phase 3: 다단계 신호 신뢰도 평가 시스템

User Story 4: 다단계 신호 신뢰도 평가 시스템
- Calculate confidence score (0-100) based on indicator pass/fail
- Allow flexible strategy tuning via threshold adjustment
- Enable trade-off between frequency and quality
"""

import logging
from typing import Dict

logger = logging.getLogger(__name__)


class SignalConfidence:
    """
    Calculate and validate signal confidence scores.

    Attributes:
        threshold: Minimum confidence score (0-100) to accept signal
        scoring: Dict with score weights for each component
            - base_score: Bollinger breakout base score
            - volume_score: Volume filter pass score
            - rsi_score: RSI filter pass score
            - macd_score: MACD filter pass score

    Example:
        >>> confidence = SignalConfidence(
        ...     threshold=60,
        ...     scoring={
        ...         'base_score': 25,
        ...         'volume_score': 25,
        ...         'rsi_score': 20,
        ...         'macd_score': 30
        ...     }
        ... )
        >>> score = confidence.calculate_score(
        ...     volume_pass=True,
        ...     rsi_pass=True,
        ...     macd_pass=False
        ... )
        >>> score  # 25 + 25 + 20 = 70
        70
        >>> confidence.meets_threshold(score)
        True
    """

    def __init__(
        self,
        threshold: int = 60,
        scoring: Dict[str, int] = None
    ):
        """
        Initialize confidence scoring system.

        Args:
            threshold: Minimum score (0-100) to accept signal
            scoring: Score weights for each component

        Raises:
            ValueError: If validation fails
        """
        # Validate threshold bounds
        if not (0 <= threshold <= 100):
            raise ValueError(f"Threshold must be between 0-100, got {threshold}")

        # Set default scoring if not provided
        if scoring is None:
            scoring = {
                'base_score': 25,
                'volume_score': 25,
                'rsi_score': 20,
                'macd_score': 30
            }

        # Validate scoring keys
        required_keys = {'base_score', 'volume_score', 'rsi_score', 'macd_score'}
        if set(scoring.keys()) != required_keys:
            raise ValueError(
                f"Scoring must contain exactly these keys: {required_keys}, "
                f"got: {set(scoring.keys())}"
            )

        # Validate all scores are non-negative
        for key, value in scoring.items():
            if value < 0:
                raise ValueError(
                    f"All scores must be non-negative, "
                    f"got {key}={value}"
                )

        # Validate total scoring <= 100
        total_score = sum(scoring.values())
        if total_score > 100:
            raise ValueError(
                f"Total scoring cannot exceed 100 points, "
                f"got {total_score} "
                f"(base={scoring['base_score']}, "
                f"volume={scoring['volume_score']}, "
                f"rsi={scoring['rsi_score']}, "
                f"macd={scoring['macd_score']})"
            )

        # Validate threshold is achievable
        if threshold > total_score:
            raise ValueError(
                f"Threshold ({threshold}) cannot exceed maximum achievable score ({total_score})"
            )

        self.threshold = threshold
        self.scoring = scoring

        logger.debug(
            f"SignalConfidence initialized: threshold={threshold}, "
            f"max_score={total_score}"
        )

    def calculate_score(
        self,
        volume_pass: bool,
        rsi_pass: bool,
        macd_pass: bool
    ) -> int:
        """
        Calculate confidence score based on filter results.

        Scoring logic:
        - Always add base_score (Bollinger breakout confirmed)
        - Add volume_score if volume filter passed
        - Add rsi_score if RSI filter passed
        - Add macd_score if MACD filter passed

        Args:
            volume_pass: Volume filter result
            rsi_pass: RSI filter result
            macd_pass: MACD filter result

        Returns:
            int: Confidence score (0-100)

        Example:
            >>> conf = SignalConfidence()
            >>> conf.calculate_score(True, True, True)  # All pass
            100
            >>> conf.calculate_score(True, False, False)  # Only volume
            50
        """
        score = self.scoring['base_score']  # Base score always included

        if volume_pass:
            score += self.scoring['volume_score']

        if rsi_pass:
            score += self.scoring['rsi_score']

        if macd_pass:
            score += self.scoring['macd_score']

        logger.debug(
            f"Confidence score calculated: {score} "
            f"(volume={volume_pass}, rsi={rsi_pass}, macd={macd_pass})"
        )

        return score

    def meets_threshold(self, score: int) -> bool:
        """
        Check if score meets minimum threshold.

        Args:
            score: Calculated confidence score

        Returns:
            bool: True if score >= threshold

        Example:
            >>> conf = SignalConfidence(threshold=60)
            >>> conf.meets_threshold(70)
            True
            >>> conf.meets_threshold(50)
            False
            >>> conf.meets_threshold(60)  # Boundary case
            True
        """
        return score >= self.threshold

    def get_max_score(self) -> int:
        """
        Get maximum achievable score with current scoring configuration.

        Returns:
            int: Sum of all scoring components
        """
        return sum(self.scoring.values())
