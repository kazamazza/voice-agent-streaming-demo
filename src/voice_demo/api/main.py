from fastapi import FastAPI

app = FastAPI(title="Voice Agent Streaming Demo", version="0.1.0")

@app.get("/healthz")
def healthz() -> dict:
    return {"ok": True}