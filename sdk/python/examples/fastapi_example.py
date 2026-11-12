import os
from fastapi import FastAPI
from pulsewatch_sdk import init, integrate_fastapi

pulsewatch = init(os.environ["PULSEWATCH_DSN"], environment=os.getenv("APP_ENV", "development"))
app = FastAPI()
integrate_fastapi(app, pulsewatch)

@app.get("/fail")
async def fail():
    raise RuntimeError("Demo checkout failure")
