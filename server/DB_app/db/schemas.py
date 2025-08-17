from pydantic import BaseModel, Field
from typing import Optional, List

class RunLog(BaseModel):
    id: str          = Field(..., max_length=64)
    stage: str       = Field(..., max_length=4)
    tokens: int      = Field(..., ge=0)
    clear_time: int  = Field(..., ge=0)

# 요청 스키마
class CreateUserReq(BaseModel):
    user_id: str = Field(min_length=1, max_length=64)

class ClearStageReq(BaseModel):
    user_id: str
    stage_code: str
    prompt_length: int = Field(ge=0)
    clear_time_ms: int = Field(ge=0)

# 응답 스키마
class StageProgressOut(BaseModel):
    code: str
    unlocked: bool
    cleared: bool
    prompt_length: Optional[int] = None
    clear_time_ms: Optional[int] = None
    cleared_at: Optional[str] = None

class ProgressResp(BaseModel):
    user_id: str
    stages: List[StageProgressOut]