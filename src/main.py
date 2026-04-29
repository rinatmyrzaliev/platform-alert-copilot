from fastapi import FastAPI

app = FastAPI(title="Alert Copilot")


@app.get("/healthz")
def healthz():
    return {"status": "ok"}