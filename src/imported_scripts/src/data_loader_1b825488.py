import asyncio

import pandas as pd
from database import get_db, init_db
from models import Company, SecurityCategory
from sqlalchemy import select
from sqlalchemy.dialects.postgresql import insert


async def load_initial_data() -> None:
    """Load initial data from CSV files into the database."""
    try:
        # Read universe data
        df = pd.read_csv("universe.csv")

        async with get_db() as session:
            # Convert DataFrame rows to Company objects
            for _, row in df.iterrows():
                # Create upsert statement
                stmt = (
                    insert(Company)
                    .values(
                        ticker=row["Ticker"],
                        isin=row["ISIN"],
                        name=row["Security Name"],
                        category=(
                            SecurityCategory(row["Category"])
                            if "Category" in row
                            else None
                        ),
                        sector=row.get("Sector", None),
                        current_tick=row.get("Tick", None),
                        rss_feed=row.get("RSS_Feed"),
                    )
                    .on_conflict_do_update(
                        index_elements=["ticker"],
                        set_={
                            "isin": row["ISIN"],
                            "name": row["Security Name"],
                            "category": (
                                SecurityCategory(row["Category"])
                                if "Category" in row
                                else None
                            ),
                            "sector": row.get("Sector", None),
                            "current_tick": row.get("Tick", None),
                            "rss_feed": row.get("RSS_Feed"),
                        },
                    )
                )

                await session.execute(stmt)

            # Verify data was loaded
            result = await session.execute(select(Company))
            result.scalars().all()

    except Exception:
        raise


async def main() -> None:
    """Initialize database and load initial data."""
    await init_db()

    await load_initial_data()


if __name__ == "__main__":
    asyncio.run(main())
