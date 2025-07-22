# ai_app/main.py
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from AI_app.api.websocket import ws_router
from AI_app.config import settings

def create_app() -> FastAPI:
    app = FastAPI()
    app.include_router(ws_router)

    # (옵션) CORS
    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],
        allow_methods=["*"],
        allow_headers=["*"],
    )
    return app

app = create_app()

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        "ai_app.main:app",
        host=settings.http_host,
        port=settings.http_port,
        reload=True,
    )
    
#uvicorn AI_app.main:app --host 0.0.0.0 --port 8002 실행용