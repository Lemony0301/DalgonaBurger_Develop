from fastapi import FastAPI

from DB_app.config import settings
from DB_app.db.session import init_db, dispose_db
from DB_app.api.websocket import ws_router
from DB_app.api.chart_ws import chart_router

def create_app() -> FastAPI:
    app = FastAPI()
    app.include_router(ws_router)
    app.include_router(chart_router)

    @app.on_event("startup")
    async def startup():
        await init_db()

    @app.on_event("shutdown")
    async def shutdown():
        await dispose_db()

    return app

app = create_app()

if __name__ == "__main__":
    import uvicorn
    uvicorn.run("DB_app.main:app",
                host=settings.http_host,
                port=settings.http_port,
                reload=True)
    
#uvicorn DB_app.main:app --host 0.0.0.0 --port 8001