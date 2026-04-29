from fastapi import FastAPI

from router.pr_router import router as pr_router


app = FastAPI(title="quartz")
app.include_router(pr_router)


@app.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok"}
