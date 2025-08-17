# DB_app/api/rest.py
from fastapi import APIRouter, HTTPException, Request
from pydantic import BaseModel
from sqlalchemy import select
import logging

from DB_app.db.session import async_session
from DB_app.db.models import UserORM, StageORM, UserStageProgressORM

rest_router = APIRouter()
logger = logging.getLogger("dalgona.rest")  # 원하는 이름

class CreateUserReq(BaseModel):
    user_id: str

@rest_router.post("/users")
async def create_user(req: CreateUserReq, request: Request):
    # --- 여기서 수신한 user_id 로그 출력 ---
    client_ip = request.client.host if request.client else "unknown"
    logger.info("REGISTER request: user_id=%s from=%s", req.user_id, client_ip)

    created = False
    async with async_session() as s, s.begin():
        user = await s.get(UserORM, req.user_id)
        if not user:
            s.add(UserORM(user_id=req.user_id))
            created = True  # users 트리거로 progress(A1만 unlock) 자동 생성

    logger.info("REGISTER done: user_id=%s created=%s", req.user_id, created)
    return {"user_id": req.user_id, "created": created}

@rest_router.get("/progress/{user_id}")
async def get_progress(user_id: str):
    async with async_session() as s:
        rows = (await s.execute(
            select(
                StageORM.code,
                UserStageProgressORM.unlocked,
                UserStageProgressORM.cleared,
                UserStageProgressORM.prompt_length,
                UserStageProgressORM.clear_time_ms,
                UserStageProgressORM.cleared_at,
            )
            .join(UserStageProgressORM, UserStageProgressORM.stage_id == StageORM.stage_id)
            .where(UserStageProgressORM.user_id == user_id)
            .order_by(StageORM.code)
        )).all()

    return {
        "user_id": user_id,
        "stages": [
            {
                "code": r[0],
                "unlocked": r[1],
                "cleared": r[2],
                "prompt_length": r[3],
                "clear_time_ms": r[4],
                "cleared_at": (r[5].isoformat() if r[5] else None),
            } for r in rows
        ],
    }