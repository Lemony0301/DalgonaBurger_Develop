# websocket.py
from fastapi import APIRouter, WebSocket
from sqlalchemy.exc import SQLAlchemyError
from DB_app.db.session import async_session
from DB_app.db.models import RunLogORM
from DB_app.db.schemas import RunLog
from DB_app.realtime import broadcaster

ws_router = APIRouter()

@ws_router.websocket("/ws")

async def ws_handler(ws: WebSocket):
    await ws.accept()
    async for raw in ws.iter_text():
        # 1) 메시지 검증
        try:
            data = RunLog.model_validate_json(raw)
            print(f"[WS] ⇐ {data.id=} {data.stage=} {data.tokens=} {data.clear_time=}")

        except ValueError as e:
            await ws.send_json({"ack": False, "error": str(e)})
            continue

        # 2) DB 저장
        try:
            async with async_session() as session, session.begin():
                session.add(RunLogORM(**data.model_dump()))
                await broadcaster.publish(data.model_dump())
                await ws.send_json({"ack": True, "received_text": "db 통신 완료"})
                print("db 저장성공", data.model_dump())

        except SQLAlchemyError as e:
            print("db 저장 실패", e)
            await ws.send_json({"ack": False, "db_error": str(e.__class__.__name__)})
            continue