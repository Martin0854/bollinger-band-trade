"""Settings API endpoints."""

from __future__ import annotations

from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from src.db.database import get_db
from src.auth.middleware import get_current_user
from src.models.user import User
from src.services.settings_service import SettingsService
from src.core.logging import logger

router = APIRouter(prefix="/settings", tags=["Settings"])


class SettingsResponse(BaseModel):
    """User settings response."""

    max_positions: int
    max_position_pct: float
    stop_loss_pct: float
    confidence_threshold: int

    class Config:
        from_attributes = True


class SettingsUpdateRequest(BaseModel):
    """Request to update settings."""

    max_positions: Optional[int] = Field(None, ge=1, le=50, description="Max positions (1-50)")
    max_position_pct: Optional[float] = Field(None, ge=1, le=100, description="Max position % (1-100)")
    stop_loss_pct: Optional[float] = Field(None, ge=1, le=50, description="Stop loss % (1-50)")
    confidence_threshold: Optional[int] = Field(None, ge=0, le=100, description="Confidence threshold (0-100)")


class ConstitutionWarning(BaseModel):
    """Constitution III warning."""

    field: str
    message: str
    recommended_value: float


class SettingsUpdateResponse(BaseModel):
    """Response for settings update with warnings."""

    settings: SettingsResponse
    warnings: list[ConstitutionWarning]


@router.get("", response_model=SettingsResponse)
async def get_settings(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Get user settings."""
    settings_service = SettingsService(db)
    settings = settings_service.get_settings(current_user.id)

    return SettingsResponse(
        max_positions=settings.max_positions,
        max_position_pct=float(settings.max_position_pct),
        stop_loss_pct=float(settings.stop_loss_pct),
        confidence_threshold=settings.confidence_threshold,
    )


@router.put("", response_model=SettingsUpdateResponse)
async def update_settings(
    request: SettingsUpdateRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """
    Update user settings.

    Returns updated settings along with any Constitution III warnings.
    """
    try:
        settings_service = SettingsService(db)
        settings, warnings = settings_service.update_settings(
            user_id=current_user.id,
            max_positions=request.max_positions,
            max_position_pct=request.max_position_pct,
            stop_loss_pct=request.stop_loss_pct,
            confidence_threshold=request.confidence_threshold,
        )

        return SettingsUpdateResponse(
            settings=SettingsResponse(
                max_positions=settings.max_positions,
                max_position_pct=float(settings.max_position_pct),
                stop_loss_pct=float(settings.stop_loss_pct),
                confidence_threshold=settings.confidence_threshold,
            ),
            warnings=[
                ConstitutionWarning(
                    field=w["field"],
                    message=w["message"],
                    recommended_value=w["recommended_value"],
                )
                for w in warnings
            ],
        )

    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e),
        )
