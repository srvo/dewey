```python
from contextlib import contextmanager
from typing import Union

from sqlalchemy import create_engine
from sqlalchemy.engine import Connection
from sqlalchemy.orm import Session

from ethifinx.config import get_config

engine = create_engine(get_config().database_url)


@contextmanager
def get_connection(use_raw_cursor: bool = False) -> Union[Session, Connection]:
    """Get a database connection.

    Args:
        use_raw_cursor: If True, returns a raw database connection with cursor,
            otherwise returns a SQLAlchemy Session.

    Returns:
        Either a SQLAlchemy Session or raw database Connection based on
        use_raw_cursor.
    """
    if use_raw_cursor:
        with engine.raw_connection() as conn:
            yield conn
    else:
        session = Session(engine)
        try:
            yield session
        finally:
            session.close()
```
