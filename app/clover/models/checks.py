from pydantic import Field, BaseModel

class BankCodeCheck(BaseModel):
    """
    Response model for bank code lookup.
    Takes a bank name as input and returns the corresponding bank code.
    """

    bank_code: str = Field(description="The bank code corresponding to the provided bank name, it returns the bank code in number string format")