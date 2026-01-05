"""UserSettings model for strategy parameters."""

from datetime import datetime

from sqlalchemy import Column, Integer, Numeric, DateTime, ForeignKey, String
from sqlalchemy.orm import relationship

from src.models.base import BaseModel


class UserSettings(BaseModel):
    """User strategy settings with Constitution III defaults."""

    __tablename__ = "user_settings"

    # Foreign key to User
    user_id = Column(String(36), ForeignKey("users.id"), unique=True, nullable=False)

    # Strategy parameters with Constitution III defaults
    max_positions = Column(Integer, nullable=False, default=15)
    max_position_pct = Column(Numeric(5, 2), nullable=False, default=10.00)
    stop_loss_pct = Column(Numeric(5, 2), nullable=False, default=5.00)
    confidence_threshold = Column(Integer, nullable=False, default=60)

    # Timestamps
    updated_at = Column(DateTime, nullable=False, default=datetime.utcnow, onupdate=datetime.utcnow)

    # Relationships
    user = relationship("User", back_populates="settings")

    def check_constitution_compliance(self) -> list[dict]:
        """Check if settings comply with Constitution III and return warnings."""
        warnings = []

        if float(self.stop_loss_pct) < 5.0:
            warnings.append({
                "field": "stop_loss_pct",
                "message": "Constitution III recommends stop_loss_pct >= 5%",
                "recommended_value": 5.0,
            })

        if float(self.max_position_pct) > 10.0:
            warnings.append({
                "field": "max_position_pct",
                "message": "Constitution III recommends max_position_pct <= 10%",
                "recommended_value": 10.0,
            })

        if self.max_positions > 15:
            warnings.append({
                "field": "max_positions",
                "message": "Constitution III recommends max_positions <= 15",
                "recommended_value": 15,
            })

        return warnings

    def __repr__(self):
        return f"<UserSettings(max_positions={self.max_positions}, stop_loss_pct={self.stop_loss_pct})>"
