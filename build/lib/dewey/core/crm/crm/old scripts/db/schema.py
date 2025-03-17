from sqlalchemy import JSON, Column, Integer, String, Text
from sqlalchemy.ext.declarative import declarative_base

# This file was moved to db/schema.py

Base = declarative_base()

class AttioContact(Base):
    __tablename__ = 'attio_contacts'
    id = Column(Integer, primary_key=True)
    contact_id = Column(String(255), unique=True)
    record_id = Column(String(36), nullable=False)
    record = Column(String(48), nullable=False)
    connection_strength = Column(String(11))
    last_email_interaction_when = Column(String(20), nullable=False)
    last_calendar_interaction_when = Column(String(20))
    name = Column(String(48))
    email_addresses = Column(String(73), nullable=False)
    description = Column(Text)
    company = Column(String(60))
    job_title = Column(String(255))
    phone_numbers = Column(String(255))
    primary_location_state = Column(String(255))
    facebook = Column(String(255))
    instagram = Column(String(255))
    linkedin = Column(String(255))
    twitter = Column(String(255))
    number_of_accounts = Column(String(255))
    cash = Column(String(255))
    balance = Column(String(255))
    raw_data = Column(JSON)

class OnyxEnrichment(Base):
    __tablename__ = 'onyx_enrichments'
    id = Column(Integer, primary_key=True)
    contact_id = Column(String(255), index=True)
    search_results = Column(JSON)
    timestamp = Column(String(255))
