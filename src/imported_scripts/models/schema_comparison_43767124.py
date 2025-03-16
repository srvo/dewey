def model(dbt, session):
    dbt.config(materialized="table", packages=["sqlalchemy"])

    from sqlalchemy import inspect

    def get_model_columns(base) -> dict[str, dict[str, str]]:
        """Get column information from SQLAlchemy models."""
        models = {}
        for class_ in base._decl_class_registry.values():
            if hasattr(class_, "__tablename__"):
                models[class_.__tablename__] = {
                    column.name: str(column.type) for column in class_.__table__.columns
                }
        return models

    def get_db_columns(engine) -> dict[str, dict[str, str]]:
        """Get column information from the database."""
        inspector = inspect(engine)
        tables = {}
        for table_name in inspector.get_table_names():
            tables[table_name] = {
                column["name"]: str(column["type"])
                for column in inspector.get_columns(table_name)
            }
        return tables

    def compare_schemas(model_columns, db_columns) -> list[str]:
        """Compare model schemas with database schemas."""
        differences = []

        # Check for missing tables
        for table in model_columns:
            if table not in db_columns:
                differences.append(
                    f"Table '{table}' exists in models but not in database",
                )
                continue

            # Check columns
            model_cols = model_columns[table]
            db_cols = db_columns[table]

            for col, type_ in model_cols.items():
                if col not in db_cols:
                    differences.append(
                        f"Column '{col}' of table '{table}' exists in model but not in database",
                    )
                elif db_cols[col] != type_:
                    differences.append(
                        f"Column '{col}' of table '{table}' has type '{db_cols[col]}' "
                        f"in database but '{type_}' in model",
                    )

            for col in db_cols:
                if col not in model_cols:
                    differences.append(
                        f"Column '{col}' of table '{table}' exists in database but not in model",
                    )

        # Check for extra tables
        for table in db_columns:
            if table not in model_columns:
                differences.append(
                    f"Table '{table}' exists in database but not in models",
                )

        return differences

    # Get model columns from stock and tick_history models
    from .stock import Base as StockBase
    from .tick_history import Base as TickBase

    stock_columns = get_model_columns(StockBase)
    tick_columns = get_model_columns(TickBase)
    model_columns = {**stock_columns, **tick_columns}

    # Get database columns
    db_columns = get_db_columns(session.bind)

    # Compare schemas
    differences = compare_schemas(model_columns, db_columns)

    # Return results as a DataFrame
    import pandas as pd

    return pd.DataFrame(
        {
            "timestamp": [pd.Timestamp.now()],
            "differences_found": [len(differences)],
            "differences": [
                "\n".join(differences) if differences else "No differences found",
            ],
        },
    )
