# initialize_db.py
from sqlalchemy import create_engine

from database.models import Base

# Database URL (replace with your actual database URL)
DATABASE_URL = "postgresql://srvo:Junius@localhost:5432/email_processing"


def initialize_database():
    # Create the database engine
    engine = create_engine(DATABASE_URL)

    # Create all tables defined in the models
    Base.metadata.create_all(engine)
    print("Database schema created successfully!")


if __name__ == "__main__":
    initialize_database()
