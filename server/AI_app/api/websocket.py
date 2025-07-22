# ai_app/api/websocket.py
from fastapi import APIRouter, WebSocket
from AI_app.llm.generator import PromptRequest, generate_action

ws_router = APIRouter()

@ws_router.websocket("/ws")
async def ai_ws(ws: WebSocket):
    await ws.accept()

    async for raw in ws.iter_text():
        try:
            req = PromptRequest.model_validate_json(raw)
            print(f"[AI] ⇐ user={req.userId} stage={req.stageId!s} prompt={req.prompt!r}")

        except ValueError as e:
            await ws.send_json({"error": f"입력 오류: {e}"})
            continue

        # ② LLM 호출 → ActionResponse
        res = await generate_action(req)
        await ws.send_text(res.model_dump_json())

        print(f"[AI] ⇒ data={res.param}, {res.promptLen}")
        print(f"[AI] ⇒ action={res.actionType} err={res.error}")
