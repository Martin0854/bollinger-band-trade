"""Stock list model for user-uploaded stock lists."""

from datetime import datetime
from sqlalchemy import Column, DateTime, ForeignKey, String, Text
from sqlalchemy.orm import relationship

from src.models.base import Base, generate_uuid


class StockList(Base):
    """User's custom stock list."""

    __tablename__ = "stock_lists"

    id = Column(String(36), primary_key=True, default=generate_uuid)
    user_id = Column(String(36), ForeignKey("users.id"), nullable=False)
    name = Column(String(100), nullable=False)
    description = Column(String(255), nullable=True)
    stock_codes = Column(Text, nullable=False)  # Newline-separated stock codes
    stock_count = Column(String(10), nullable=False, default="0")
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # Relationship
    user = relationship("User", back_populates="stock_lists")

    def get_stock_codes_list(self) -> list[str]:
        """Return stock codes as a list."""
        return [code.strip() for code in self.stock_codes.strip().split("\n") if code.strip()]

    def __repr__(self):
        return f"<StockList {self.name} ({self.stock_count} stocks)>"
