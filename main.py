import sentry_sdk
from fastapi import FastAPI, Depends, Response, HTTPException
from fastapi.security import HTTPBasic, HTTPBasicCredentials
from prometheus_client import generate_latest
from prometheus_client.exposition import CONTENT_TYPE_LATEST
from sentry_sdk.integrations.asgi import SentryAsgiMiddleware

from config import config
import parser  # noqa

app = FastAPI()
security = HTTPBasic()

if config["sentry"]["dsn"]:
    sentry_sdk.init(dsn=config["sentry"]["dsn"])
    app.add_middleware(SentryAsgiMiddleware)


@app.get("/metrics")
async def get_metrics(credentials: HTTPBasicCredentials = Depends(security)):
    if (
        credentials.username != config["prometheus"]["username"]
        or credentials.password != config["prometheus"]["password"]
    ):
        return HTTPException(status_code=403, detail="Wrong auth")

    return Response(generate_latest(), media_type=CONTENT_TYPE_LATEST)
