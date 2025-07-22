import threading
import uvicorn

def run_ai():
    uvicorn.run("AI_app.main:app", host="0.0.0.0", port=8000, reload=True)

def run_db():
    uvicorn.run("DB_app.main:app", host="0.0.0.0", port=8001, reload=True)

if __name__ == "__main__":
    threading.Thread(target=run_ai).start()
    threading.Thread(target=run_db).start()