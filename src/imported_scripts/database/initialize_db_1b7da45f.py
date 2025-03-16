# initialize_db.py
from database.models import Base
from sqlalchemy import create_engine

# Database URL (replace with your actual database URL)
DATABASE_URL = "postgresql://srvo:Junius@localhost:5432/email_processing"


def initialize_database() -> None:
    # Create the database engine
    engine = create_engine(DATABASE_URL)

    # Create all tables defined in the models
    Base.metadata.create_all(engine)


if __name__ == "__main__":
    initialize_database()
