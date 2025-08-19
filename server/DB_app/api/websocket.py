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
                rank_length_pct = 100.0
                rank_clear = 1
                rank_length = 1
                total_time = 1
                total_length = 1
                
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

                    new_time = int(data.clear_time_ms)
                    new_length = int(data.prompt_length)

                    improved_time = (prog.clear_time_ms is None) or (new_time < prog.clear_time_ms)
                    improved_length = (prog.prompt_length is None) or (new_length < prog.prompt_length)

                    if improved_time:
                        prog.clear_time_ms = new_time
                    if improved_length:
                        prog.prompt_length = new_length

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

                    my_best_time = prog.clear_time_ms
                    my_best_length = prog.prompt_length

                    # 1) clear_time 기준
                    others_total_time = await session.scalar(
                        select(func.count()).select_from(UserStageProgressORM).where(
                            UserStageProgressORM.stage_id == stage.stage_id,
                            UserStageProgressORM.cleared.is_(True),
                            UserStageProgressORM.clear_time_ms.isnot(None),
                            UserStageProgressORM.user_id != data.user_id
                        )
                    ) or 0

                    total_time = others_total_time + (1 if my_best_time is not None else 0)

                    faster_time = 0
                    if my_best_time is not None and total_time > 0:
                        faster_time = await session.scalar(
                            select(func.count()).select_from(UserStageProgressORM).where(
                                UserStageProgressORM.stage_id == stage.stage_id,
                                UserStageProgressORM.cleared.is_(True),
                                UserStageProgressORM.clear_time_ms.isnot(None),
                                UserStageProgressORM.user_id != data.user_id,
                                UserStageProgressORM.clear_time_ms < my_best_time
                            )
                        ) or 0
                        rank_clear = int(faster_time) + 1
                        if total_time > 0:
                            rank_clear_pct = round((rank_clear / total_time) * 100.0, 2)
                        else:
                            rank_clear_pct = 0.0

                    # 2) prompt_length 기준
                    others_length_length = await session.scalar(
                        select(func.count()).select_from(UserStageProgressORM).where(
                            UserStageProgressORM.stage_id == stage.stage_id,
                            UserStageProgressORM.cleared.is_(True),
                            UserStageProgressORM.prompt_length.isnot(None),
                            UserStageProgressORM.user_id != data.user_id
                        )
                    ) or 0

                    total_length = others_length_length + (1 if my_best_length is not None else 0)

                    shorter_length = 0
                    if my_best_length is not None and total_length > 0:
                        shorter_length = await session.scalar(
                            select(func.count()).select_from(UserStageProgressORM).where(
                                UserStageProgressORM.stage_id == stage.stage_id,
                                UserStageProgressORM.cleared.is_(True),
                                UserStageProgressORM.prompt_length.isnot(None),
                                UserStageProgressORM.user_id != data.user_id,
                                UserStageProgressORM.prompt_length < my_best_length
                            )
                        ) or 0
                        rank_length = int(shorter_length) + 1
                        if total_length > 0:
                            rank_length_pct = round((rank_length / total_length) * 100.0, 2)
                        else:
                            rank_length_pct = 0.0

                if broadcaster:
                    try:
                        await broadcaster.publish(data.model_dump())
                    except Exception:
                        pass

                # 게임 결과창에서 바로 사용할 응답
                await ws.send_json({
                    "ack": True,
                    "user_id":data.user_id,
                    "stage": data.stage_code,
                    "rank_clear_time_percent": rank_clear_pct,
                    "rank_tokens_percent": rank_length_pct,
                    "rank_clear_time": rank_clear,
                    "rank_tokens": rank_length,
                    "total_records": total_time,
                    "received_text": "ok"
                })
                print("[WS] saved (progress-based ranks):", data.model_dump(),
                      f"time {rank_clear}/{total_time} ({rank_clear_pct}%), "
                      f"length {rank_length}/{total_length} ({rank_length_pct}%)",
                      f"improved_time={improved_time} improved_length={improved_length}")

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
