"""UserSettings model for strategy parameters."""

from datetime import datetime

from sqlalchemy import Column, Integer, Numeric, DateTime, ForeignKey, String, Boolean
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

    # Take Profit Settings (익절 설정)
    take_profit_enabled = Column(Boolean, nullable=False, default=True)
    take_profit_pct = Column(Numeric(5, 2), nullable=False, default=10.00)
    take_profit_ratio = Column(Numeric(3, 2), nullable=False, default=0.50)

    # Bollinger Band Parameters
    bollinger_period = Column(Integer, nullable=False, default=20)
    bollinger_std_dev = Column(Numeric(3, 1), nullable=False, default=2.0)

    # Squeeze Detection
    squeeze_threshold_pct = Column(Integer, nullable=False, default=30)
    squeeze_lookback_days = Column(Integer, nullable=False, default=10)

    # Advanced Squeeze Settings
    expansion_threshold_pct = Column(Numeric(5, 2), nullable=False, default=20.00)
    band_touch_tolerance = Column(Numeric(5, 4), nullable=False, default=0.0010)

    # Metrics Configuration
    trading_days_per_year = Column(Integer, nullable=False, default=252)
    days_per_year = Column(Integer, nullable=False, default=365)

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

    def to_backtest_config_dict(self) -> dict:
        """Convert settings to backtest configuration dictionary."""
        return {
            # Risk Management
            "max_positions": self.max_positions,
            "max_position_percent": float(self.max_position_pct),
            "stop_loss_percent": float(self.stop_loss_pct),
            # Bollinger Band Parameters
            "bollinger_period": self.bollinger_period,
            "bollinger_std_dev": float(self.bollinger_std_dev),
            # Squeeze Detection
            "squeeze_threshold_percent": self.squeeze_threshold_pct,
            "squeeze_lookback_days": self.squeeze_lookback_days,
            # Take Profit
            "take_profit": {
                "enabled": self.take_profit_enabled,
                "target_pct": float(self.take_profit_pct),
                "ratio": float(self.take_profit_ratio),
            },
            # Squeeze Advanced
            "squeeze_advanced": {
                "expansion_threshold_percent": float(self.expansion_threshold_pct),
                "band_touch_tolerance": float(self.band_touch_tolerance),
            },
            # Metrics
            "metrics": {
                "trading_days_per_year": self.trading_days_per_year,
                "days_per_year": self.days_per_year,
            },
        }
