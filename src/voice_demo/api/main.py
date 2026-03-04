from fastapi import FastAPI
from voice_demo.domain.errors import DomainError
from voice_demo.api.errors import domain_error_to_response
from voice_demo.api.routes import router


app = FastAPI(title="Voice Agent Streaming Demo", version="0.1.0")

app.add_exception_handler(DomainError, domain_error_to_response)
app.include_router(router)


@app.get("/healthz")
def healthz() -> dict:
    return {"ok": True}
