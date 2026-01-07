"""UserSettings model for strategy parameters."""

from datetime import datetime
from decimal import Decimal
from typing import TYPE_CHECKING

from sqlalchemy import ForeignKey, Numeric, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from src.models.base import BaseModel

if TYPE_CHECKING:
    from src.models.user import User


class UserSettings(BaseModel):
    """User strategy settings."""

    __tablename__ = "user_settings"

    user_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("users.id"), unique=True, nullable=False
    )

    max_positions: Mapped[int] = mapped_column(default=15)
    max_position_pct: Mapped[Decimal] = mapped_column(Numeric(5, 2), default=Decimal("10.00"))
    stop_loss_pct: Mapped[Decimal] = mapped_column(Numeric(5, 2), default=Decimal("4.50"))
    confidence_threshold: Mapped[int] = mapped_column(default=50)

    take_profit_enabled: Mapped[bool] = mapped_column(default=True)
    take_profit_pct: Mapped[Decimal] = mapped_column(Numeric(5, 2), default=Decimal("9.00"))
    take_profit_ratio: Mapped[Decimal] = mapped_column(Numeric(3, 2), default=Decimal("0.50"))

    bollinger_period: Mapped[int] = mapped_column(default=12)
    bollinger_std_dev: Mapped[Decimal] = mapped_column(Numeric(3, 1), default=Decimal("1.3"))

    squeeze_threshold_pct: Mapped[int] = mapped_column(default=55)
    squeeze_lookback_days: Mapped[int] = mapped_column(default=10)

    expansion_threshold_pct: Mapped[Decimal] = mapped_column(
        Numeric(5, 2), default=Decimal("20.00")
    )
    band_touch_tolerance: Mapped[Decimal] = mapped_column(Numeric(5, 4), default=Decimal("0.0010"))

    trading_days_per_year: Mapped[int] = mapped_column(default=252)
    days_per_year: Mapped[int] = mapped_column(default=365)

    updated_at: Mapped[datetime] = mapped_column(default=datetime.utcnow, onupdate=datetime.utcnow)

    user: Mapped["User"] = relationship(back_populates="settings")

    def check_constitution_compliance(self) -> list[dict]:
        """Check if settings comply with Constitution III and return warnings."""
        warnings = []

        if float(self.stop_loss_pct) < 5.0:
            warnings.append(
                {
                    "field": "stop_loss_pct",
                    "message": "Constitution III recommends stop_loss_pct >= 5%",
                    "recommended_value": 5.0,
                }
            )

        if float(self.max_position_pct) > 10.0:
            warnings.append(
                {
                    "field": "max_position_pct",
                    "message": "Constitution III recommends max_position_pct <= 10%",
                    "recommended_value": 10.0,
                }
            )

        if self.max_positions > 15:
            warnings.append(
                {
                    "field": "max_positions",
                    "message": "Constitution III recommends max_positions <= 15",
                    "recommended_value": 15,
                }
            )

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
