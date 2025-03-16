import enum
from datetime import datetime

from sqlalchemy import (
    JSON,
    Boolean,
    Column,
    DateTime,
    Enum,
    Float,
    ForeignKey,
    Integer,
    String,
    Table,
    Text,
)
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import relationship

Base = declarative_base()

# Association tables for many-to-many relationships
entity_relationships = Table(
    "entity_relationships",
    Base.metadata,
    Column("source_id", Integer, ForeignKey("entities.id"), primary_key=True),
    Column("target_id", Integer, ForeignKey("entities.id"), primary_key=True),
    Column(
        "relationship_type_id",
        Integer,
        ForeignKey("relationship_types.id"),
        primary_key=True,
    ),
    Column("strength", Float),  # Optional: relationship strength/weight
    Column("start_date", DateTime),
    Column("end_date", DateTime),
    Column("meta_data", JSON),  # Changed from metadata to meta_data
)


class SecurityCategory(enum.Enum):
    CORE = "CORE"
    SATELLITE = "SATELLITE"
    TRANSITION = "TRANSITION"
    WATCHLIST = "WATCHLIST"


class EntityType(enum.Enum):
    COMPANY = "COMPANY"
    PERSON = "PERSON"
    ORGANIZATION = "ORGANIZATION"
    PRODUCT = "PRODUCT"
    LOCATION = "LOCATION"
    EVENT = "EVENT"
    DATA_SOURCE = "DATA_SOURCE"  # For tracking different data sources
    EXCLUSION_CRITERIA = (
        "EXCLUSION_CRITERIA"  # For tracking different types of exclusions
    )


class DataSourceType(enum.Enum):
    ESG_PROVIDER = "ESG_PROVIDER"
    RESEARCH_FIRM = "RESEARCH_FIRM"
    NEWS_OUTLET = "NEWS_OUTLET"
    REGULATORY_BODY = "REGULATORY_BODY"
    NGO = "NGO"
    INTERNAL = "INTERNAL"
    OTHER = "OTHER"


class Entity(Base):
    __tablename__ = "entities"

    id = Column(Integer, primary_key=True)
    type = Column(Enum(EntityType), nullable=False)
    name = Column(String(255), nullable=False)
    identifier = Column(String(50), unique=True)  # Could be ticker, SSN, UUID, etc.
    meta_data = Column(JSON)  # Changed from metadata to meta_data
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # Relationships
    outgoing_relationships = relationship(
        "Entity",
        secondary=entity_relationships,
        primaryjoin=id == entity_relationships.c.source_id,
        secondaryjoin=id == entity_relationships.c.target_id,
        backref="incoming_relationships",
    )
    attributes = relationship("EntityAttribute", back_populates="entity")
    events = relationship("Event", back_populates="entity")
    assessments = relationship("Assessment", back_populates="entity")


class RelationshipType(Base):
    __tablename__ = "relationship_types"

    id = Column(Integer, primary_key=True)
    name = Column(String(100), nullable=False, unique=True)
    description = Column(Text)
    bidirectional = Column(Boolean, default=False)
    metadata_schema = Column(JSON)  # JSON Schema for relationship metadata validation


class EntityAttribute(Base):
    __tablename__ = "entity_attributes"

    id = Column(Integer, primary_key=True)
    entity_id = Column(Integer, ForeignKey("entities.id"), nullable=False)
    name = Column(String(100), nullable=False)
    value = Column(Text)
    value_type = Column(String(50))  # e.g., 'string', 'number', 'date', etc.
    timestamp = Column(DateTime, default=datetime.utcnow)

    entity = relationship("Entity", back_populates="attributes")


class Event(Base):
    __tablename__ = "events"

    id = Column(Integer, primary_key=True)
    entity_id = Column(Integer, ForeignKey("entities.id"), nullable=False)
    event_type = Column(String(100), nullable=False)
    timestamp = Column(DateTime, nullable=False)
    description = Column(Text)
    meta_data = Column(JSON)  # Changed from metadata to meta_data
    source_id = Column(Integer, ForeignKey("entities.id"))  # Link to the data source
    confidence = Column(Float)  # Confidence score for the event (0-1)

    entity = relationship("Entity", back_populates="events", foreign_keys=[entity_id])
    source = relationship("Entity", foreign_keys=[source_id])


class Assessment(Base):
    __tablename__ = "assessments"

    id = Column(Integer, primary_key=True)
    entity_id = Column(Integer, ForeignKey("entities.id"), nullable=False)
    source_id = Column(
        Integer,
        ForeignKey("entities.id"),
        nullable=False,
    )  # The data source making the assessment
    assessment_type = Column(
        String(100),
        nullable=False,
    )  # e.g., 'EXCLUSION', 'ESG_SCORE', etc.
    timestamp = Column(DateTime, nullable=False, default=datetime.utcnow)
    value = Column(Text)  # The actual assessment value
    meta_data = Column(JSON)  # Changed from metadata to meta_data
    confidence = Column(Float)  # Confidence score (0-1)
    valid_from = Column(DateTime)
    valid_until = Column(DateTime)
    superseded_by_id = Column(
        Integer,
        ForeignKey("assessments.id"),
    )  # Link to newer assessment if updated

    entity = relationship(
        "Entity",
        foreign_keys=[entity_id],
        back_populates="assessments",
    )
    source = relationship("Entity", foreign_keys=[source_id])
    superseded_by = relationship("Assessment", remote_side=[id])


# Legacy models adapted to work with new schema
class Company(Entity):
    __mapper_args__ = {"polymorphic_identity": EntityType.COMPANY}

    def __init__(self, **kwargs) -> None:
        kwargs["type"] = EntityType.COMPANY
        super().__init__(**kwargs)


class DataSource(Entity):
    __mapper_args__ = {"polymorphic_identity": EntityType.DATA_SOURCE}

    def __init__(self, **kwargs) -> None:
        kwargs["type"] = EntityType.DATA_SOURCE
        super().__init__(**kwargs)


class ExclusionCriteria(Entity):
    __mapper_args__ = {"polymorphic_identity": EntityType.EXCLUSION_CRITERIA}

    def __init__(self, **kwargs) -> None:
        kwargs["type"] = EntityType.EXCLUSION_CRITERIA
        super().__init__(**kwargs)


class TickHistory(Event):
    def __init__(self, **kwargs) -> None:
        kwargs["event_type"] = "TICK"
        super().__init__(**kwargs)


class SECFiling(Event):
    def __init__(self, **kwargs) -> None:
        kwargs["event_type"] = "SEC_FILING"
        super().__init__(**kwargs)


class NewsItem(Event):
    def __init__(self, **kwargs) -> None:
        kwargs["event_type"] = "NEWS"
        super().__init__(**kwargs)
