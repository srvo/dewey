```python
from pydantic import BaseModel, field_validator


class Company(BaseModel):
    """Represents a company with a ticker symbol."""

    ticker: str

    @field_validator("ticker")
    def validate_ticker(cls, v: str) -> str:
        """Validates the ticker symbol.

        Args:
            v: The ticker symbol to validate.

        Returns:
            The validated ticker symbol.
        """
        # existing validation logic...
        return v
```
