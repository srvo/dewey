from pydantic import validator

class Company(BaseModel):
    ticker: str

    @field_validator("ticker")
    def validate_ticker(cls, v):
        # existing validation logic...
        return v 