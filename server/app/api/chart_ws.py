import asyncio
from fastapi import APIRouter, WebSocket, WebSocketDisconnect
from fastapi.encoders import jsonable_encoder
from sqlalchemy import select, desc

from app.db.session  import async_session
from app.db.models   import RunLogORM
from app.realtime    import broadcaster

chart_router = APIRouter()

@chart_router.websocket("/chart")
async def chart_stream(ws: WebSocket):
    await ws.accept()

    # ① 실시간 구독을 가장 먼저 열어 둔다
    queue = await broadcaster.subscribe()

    # ② 그다음 DB에서 최근 100개를 읽어 온다
    async with async_session() as s:
        q = (
            select(RunLogORM)
            .order_by(desc(RunLogORM.created_at))
            .limit(100)
        )
        rows = (await s.execute(q)).scalars().all()

    snapshot = [
        jsonable_encoder(r, exclude={"_sa_instance_state"})
        for r in rows[::-1]          # 오래된 → 최신
    ]

    # ③ 스냅샷 전송
    await ws.send_json({"type": "snapshot", "rows": snapshot})

    # ④ 스냅샷을 읽는 동안 도착했을 수도 있는 메시지 먼저 비우기
    while not queue.empty():
        payload = await queue.get_nowait()
        await ws.send_json(jsonable_encoder(payload))

    # ⑤ 이후에는 실시간 메시지를 그대로 중계
    try:
        while True:
            payload = await queue.get()             # {id, stage, tokens, clear_time, ...}
            await ws.send_json(jsonable_encoder(payload))
    except WebSocketDisconnect:
        pass