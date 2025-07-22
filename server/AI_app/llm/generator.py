from pydantic import BaseModel


# ── 요청/응답 스키마 ───────────────────────────────────
class PromptRequest(BaseModel):
    userId: str
    stageId: str | None = None
    prompt: str


class ActionResponse(BaseModel):
    actionType: str                       # 동작 이름
    param: dict[str, str] | None = None   # 파라미터(예: 속도)
    promptLen: int                        # 프롬프트 길이
    error: str | None = None              # 오류(없으면 None)


# ── 고정값 생성기 ───────────────────────────────────
async def generate_action(req: PromptRequest) -> ActionResponse:
    """
    어떤 프롬프트가 오더라도 같은 응답을 비동기로 돌려준다.
    (FastAPI에서 await 호출 흐름을 유지하기 위해 async 함수로 둠)
    """
    return ActionResponse(
        actionType="WalkForward",         # 항상 전진 걷기
        param={"speed": "5"},             # 속도 5
        promptLen=len(req.prompt),        # 프롬프트 글자 수 계산만 반영
        error=None,
    )