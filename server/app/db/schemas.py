from pydantic import BaseModel, Field

class RunLog(BaseModel):
    id: str          = Field(..., max_length=64)
    stage: int       = Field(..., ge=0)
    tokens: int      = Field(..., ge=0)
    clear_time: int  = Field(..., ge=0)