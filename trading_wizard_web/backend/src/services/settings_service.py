"""User settings service."""

from __future__ import annotations

from decimal import Decimal
from typing import Optional

from sqlalchemy.orm import Session

from src.models.user_settings import UserSettings
from src.core.exceptions import NotFoundError
from src.core.logging import logger


class SettingsService:
    """Service for managing user settings."""

    def __init__(self, db: Session):
        self.db = db

    def get_settings(self, user_id: str) -> UserSettings:
        """
        Get user settings. Creates default settings if not exists.

        Args:
            user_id: User ID

        Returns:
            UserSettings model
        """
        settings = (
            self.db.query(UserSettings)
            .filter(UserSettings.user_id == user_id)
            .first()
        )

        if not settings:
            # Create default settings
            settings = UserSettings(
                user_id=user_id,
                max_positions=15,
                max_position_pct=Decimal("10.00"),
                stop_loss_pct=Decimal("5.00"),
                confidence_threshold=60,
            )
            self.db.add(settings)
            self.db.commit()
            logger.info(f"Created default settings for user {user_id}")

        return settings

    def update_settings(
        self,
        user_id: str,
        max_positions: Optional[int] = None,
        max_position_pct: Optional[float] = None,
        stop_loss_pct: Optional[float] = None,
        confidence_threshold: Optional[int] = None,
    ) -> tuple[UserSettings, list[dict]]:
        """
        Update user settings.

        Args:
            user_id: User ID
            max_positions: Max number of positions (1-50)
            max_position_pct: Max position percentage (1-100)
            stop_loss_pct: Stop loss percentage (1-50)
            confidence_threshold: Confidence threshold (0-100)

        Returns:
            Tuple of (updated settings, constitution warnings)
        """
        settings = self.get_settings(user_id)

        if max_positions is not None:
            if max_positions < 1 or max_positions > 50:
                raise ValueError("max_positions must be between 1 and 50")
            settings.max_positions = max_positions

        if max_position_pct is not None:
            if max_position_pct < 1 or max_position_pct > 100:
                raise ValueError("max_position_pct must be between 1 and 100")
            settings.max_position_pct = Decimal(str(max_position_pct))

        if stop_loss_pct is not None:
            if stop_loss_pct < 1 or stop_loss_pct > 50:
                raise ValueError("stop_loss_pct must be between 1 and 50")
            settings.stop_loss_pct = Decimal(str(stop_loss_pct))

        if confidence_threshold is not None:
            if confidence_threshold < 0 or confidence_threshold > 100:
                raise ValueError("confidence_threshold must be between 0 and 100")
            settings.confidence_threshold = confidence_threshold

        self.db.commit()

        # Check Constitution III compliance
        warnings = settings.check_constitution_compliance()
        if warnings:
            logger.warning(f"Constitution III warnings for user {user_id}: {warnings}")

        return settings, warnings
