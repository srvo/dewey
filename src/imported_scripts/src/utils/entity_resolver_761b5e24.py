import pandas as pd


class EntityResolver:
    def __init__(self, mappings: dict[str, str]) -> None:
        self.mappings = mappings

    async def resolve_entities(self, data: pd.DataFrame, column: str) -> pd.DataFrame:
        """Resolve entities in specified column using mapping dictionary."""
        # Map variations to canonical forms
        data[f"{column}_resolved"] = data[column].map(self.mappings)
        return data
