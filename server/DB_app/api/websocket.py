from fastapi import APIRouter, WebSocket
from starlette.websockets import WebSocketDisconnect
from pydantic import BaseModel, ValidationError, field_validator, conint
from sqlalchemy import select
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.sql import func

from DB_app.db.session import async_session
from DB_app.db.models import (
    RunLogORM, StageORM, UserStageProgressORM, UserORM
)

# 선택: 실시간 브로드캐스트 사용 중이면 유지, 아니면 주석 처리
try:
    from DB_app.realtime import broadcaster
except Exception:
    broadcaster = None

ws_router = APIRouter()

# ---------------- Pydantic 입력 모델 ----------------
class RunLogIn(BaseModel):
    """Unity가 보내는 웹소켓 페이로드 (필드명 반드시 일치)"""
    user_id: str
    stage_code: str                 # 예: "A1" ~ "E5"
    prompt_length: conint(ge=0)     # 사용한 단어 수
    clear_time_ms: conint(ge=0)     # ms

    @field_validator("user_id", "stage_code")
    @classmethod
    def not_empty(cls, v: str) -> str:
        v = v.strip()
        if not v:
            raise ValueError("must not be empty")
        return v

    @field_validator("stage_code")
    @classmethod
    def valid_code(cls, v: str) -> str:
        import re
        if not re.fullmatch(r"[A-E][1-5]", v):
            raise ValueError("stage_code must be A1..E5")
        return v


@ws_router.websocket("/ws")
async def ws_handler(ws: WebSocket):
    await ws.accept()
    try:
        async for raw in ws.iter_text():
            # 1) 유효성 검사/파싱
            try:
                data = RunLogIn.model_validate_json(raw)
                print(f"[WS<=] {data.user_id=} {data.stage_code=} {data.prompt_length=} {data.clear_time_ms=}")
            except ValidationError as e:
                await ws.send_json({"ack": False, "error": f"invalid payload: {e.errors()}"})
                continue
            except ValueError as e:
                await ws.send_json({"ack": False, "error": str(e)})
                continue

            # 2) DB 처리: 진행 업데이트 + 로그 적재 + 퍼센트/랭크 계산
            try:
                rank_clear_pct = 100.0
                rank_tokens_pct = 100.0
                rank_clear = 1
                rank_tokens = 1
                total = 1

                async with async_session() as session, session.begin():
                    # 유저 보장(REST로 이미 만들었다면 get만 통과)
                    user = await session.get(UserORM, data.user_id)
                    if not user:
                        session.add(UserORM(user_id=data.user_id))
                        await session.flush()  # users 트리거로 progress 초기화

                    # 스테이지 조회
                    stage = (await session.execute(
                        select(StageORM).where(StageORM.code == data.stage_code)
                    )).scalars().first()
                    if not stage:
                        await ws.send_json({"ack": False, "error": "unknown stage_code"})
                        continue

                    # 진행행 조회(없으면 생성)
                    prog = await session.get(
                        UserStageProgressORM, (data.user_id, stage.stage_id)
                    )
                    if not prog:
                        prog = UserStageProgressORM(
                            user_id=data.user_id, stage_id=stage.stage_id, unlocked=True
                        )
                        session.add(prog)

                    # 클리어 기록(트리거가 다음 스테이지 해금)
                    prog.unlocked = True
                    prog.cleared = True
                    prog.prompt_length = int(data.prompt_length)
                    prog.clear_time_ms = int(data.clear_time_ms)
                    prog.cleared_at = func.now()

                    # 러닝 로그 적재
                    new_log = RunLogORM(
                        user_id=data.user_id,
                        stage_code=data.stage_code,
                        prompt_length=int(data.prompt_length),
                        clear_time_ms=int(data.clear_time_ms),
                    )
                    session.add(new_log)

                    # flush로 INSERT를 DB에 반영시켜 집계에 포함되도록 함
                    await session.flush()

                    # === 집계 ===
                    total = await session.scalar(
                        select(func.count()).select_from(RunLogORM).where(
                            RunLogORM.stage_code == data.stage_code
                        )
                    ) or 0

                    faster = await session.scalar(
                        select(func.count()).select_from(RunLogORM).where(
                            RunLogORM.stage_code == data.stage_code,
                            RunLogORM.clear_time_ms < int(data.clear_time_ms)
                        )
                    ) or 0

                    shorter = await session.scalar(
                        select(func.count()).select_from(RunLogORM).where(
                            RunLogORM.stage_code == data.stage_code,
                            RunLogORM.prompt_length < int(data.prompt_length)
                        )
                    ) or 0

                    # 랭크(competition rank: 동률은 같은 순위)
                    rank_clear = int(faster) + 1
                    rank_tokens = int(shorter) + 1

                    # 퍼센트(자신보다 더 좋은 기록 비율)
                    if total > 0:
                        rank_clear_pct = round((int(faster) / total) * 100.0, 2)
                        rank_tokens_pct = round((int(shorter) / total) * 100.0, 2)
                    else:
                        rank_clear_pct = 0.0
                        rank_tokens_pct = 0.0

                # (선택) 브로드캐스트
                if broadcaster:
                    try:
                        await broadcaster.publish(data.model_dump())
                    except Exception:
                        pass

                # 게임 결과창에서 바로 사용할 응답
                await ws.send_json({
                    "ack": True,
                    "used_id":data.user_id,
                    "stage": data.stage_code,
                    "rank_clear_time_percent": rank_clear_pct,
                    "rank_tokens_percent": rank_tokens_pct,
                    "rank_clear_time": rank_clear,     # ⬅️ 추가: 등수
                    "rank_tokens": rank_tokens,         # ⬅️ 추가: 등수
                    "total_records": total,             # ⬅️ 추가: 총 기록 수
                    "received_text": "ok"
                })
                print("[WS] saved:", data.model_dump(),
                      f" ranks -> time:{rank_clear}/{total} ({rank_clear_pct}%), "
                      f"tokens:{rank_tokens}/{total} ({rank_tokens_pct}%)")

            except SQLAlchemyError as e:
                print("[WS][DB] error:", e)
                await ws.send_json({"ack": False, "db_error": e.__class__.__name__})
            except Exception as e:
                print("[WS] unexpected:", e)
                await ws.send_json({"ack": False, "error": str(e)})

    except WebSocketDisconnect as e:
        print(f"[WS] client disconnected: code={e.code}")
    finally:
        try:
            await ws.close()
        except Exception:
            pass
