"""Investment models."""

from __future__ import annotations

from datetime import datetime
from enum import Enum

from sqlalchemy import (
    Column,
    DateTime,
    Float,
    ForeignKey,
    Integer,
    String,
)
from sqlalchemy import (
    Enum as SQLEnum,
)
from sqlalchemy.orm import Mapped, Relationship, declarative_base, relationship

Base = declarative_base()


class AssetType(Enum):
    """Types of investment assets."""

    STOCK = "stock"
    BOND = "bond"
    ETF = "etf"
    CRYPTO = "crypto"
    COMMODITY = "commodity"


class ESGRating(Enum):
    """ESG ratings for investments."""

    A = "A"
    B = "B"
    C = "C"
    D = "D"
    F = "F"


class Investment(Base):
    """Investment model for tracking positions."""

    __tablename__ = "investments"

    id: Mapped[int] = Column(Integer, primary_key=True)
    symbol: Mapped[str] = Column(String, nullable=False, index=True)
    asset_type: Mapped[AssetType] = Column(SQLEnum(AssetType), nullable=False)
    quantity: Mapped[float] = Column(Float, nullable=False)
    entry_price: Mapped[float] = Column(Float, nullable=False)
    current_price: Mapped[float | None] = Column(Float)
    esg_rating: Mapped[ESGRating | None] = Column(SQLEnum(ESGRating))
    last_updated: Mapped[datetime] = Column(DateTime, default=datetime.utcnow)

    # Relationships
    ticks: Relationship[PriceTick] = relationship(
        "PriceTick",
        back_populates="investment",
    )

    @property
    def market_value(self) -> float:
        """Calculate current market value.

        Returns:
            float: The current market value.

        """
        if self.current_price is None:
            return 0.0
        return self.quantity * self.current_price

    @property
    def profit_loss(self) -> float:
        """Calculate profit/loss.

        Returns:
            float: The profit or loss.

        """
        if self.current_price is None:
            return 0.0
        return (self.current_price - self.entry_price) * self.quantity


class PriceTick(Base):
    """Price tick history."""

    __tablename__ = "price_ticks"

    id: Mapped[int] = Column(Integer, primary_key=True)
    investment_id: Mapped[int] = Column(Integer, ForeignKey("investments.id"))
    price: Mapped[float] = Column(Float, nullable=False)
    volume: Mapped[int | None] = Column(Integer)
    timestamp: Mapped[datetime] = Column(DateTime, default=datetime.utcnow)

    # Relationships
    investment: Relationship[Investment] = relationship(
        "Investment",
        back_populates="ticks",
    )
