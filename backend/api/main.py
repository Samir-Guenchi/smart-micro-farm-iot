"""GreenLoop Farm REST API.

Everything outside the backend (dashboard, assistant, agent) talks to this
API, never to the database or the broker directly. Contract: issue #14.

    uvicorn main:app --reload
"""

import logging
import time
from functools import lru_cache
from typing import Annotated

from fastapi import Depends, FastAPI, HTTPException, Query, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from pydantic import BaseModel, Field

import auth
from mqtt_pub import MqttPublisher
from settings import Settings
from store import PostgresStore

log = logging.getLogger("api")


@lru_cache
def get_settings():
    return Settings()


@lru_cache
def get_store():
    return PostgresStore(get_settings().database_url)


@lru_cache
def get_publisher():
    return MqttPublisher(get_settings())


SettingsDep = Annotated[Settings, Depends(get_settings)]
bearer = HTTPBearer(auto_error=False)


def current_user(settings: SettingsDep, creds: Annotated[HTTPAuthorizationCredentials | None, Depends(bearer)]):
    user = auth.verify_token(settings, creds.credentials) if creds else None
    if not user:
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Missing or invalid token", headers={"WWW-Authenticate": "Bearer"})
    return user


User = Annotated[str, Depends(current_user)]
Store = Annotated[PostgresStore, Depends(get_store)]

app = FastAPI(
    title="GreenLoop Farm API",
    version="0.1.0",
    docs_url="/api/docs",
    redoc_url=None,
    openapi_url="/api/openapi.json",
)
app.add_middleware(
    CORSMiddleware,
    allow_origins=get_settings().cors_origins,
    allow_methods=["GET", "POST"],
    allow_headers=["Authorization", "Content-Type"],
)


# Models -------------------------------------------------------------------


class LoginIn(BaseModel):
    username: str
    password: str


class LoginOut(BaseModel):
    token: str
    expires: int


class Node(BaseModel):
    id: str
    status: str
    last_seen: int | None
    latest: dict[str, float]


class Reading(BaseModel):
    ts: int
    value: float


class PumpIn(BaseModel):
    duration_s: int = Field(gt=0, description="Seconds to run; capped at MAX_PUMP_S (default 900)")


class PumpOut(BaseModel):
    ok: bool
    duration_s: int


# Routes -------------------------------------------------------------------


@app.post("/api/login", response_model=LoginOut, tags=["auth"])
def login(body: LoginIn, settings: SettingsDep):
    if not auth.check_password(settings, body.username, body.password):
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Wrong username or password")
    token, expires = auth.issue_token(settings, body.username)
    return {"token": token, "expires": expires}


@app.get("/api/nodes", response_model=list[Node], tags=["farm"])
def nodes(user: User, store: Store, settings: SettingsDep):
    now = time.time()
    out = []
    for node in store.nodes():
        stale = node["last_seen"] is None or now - node["last_seen"] > settings.offline_after_s
        out.append({**node, "status": "offline" if stale else node["status"]})
    return out


@app.get("/api/readings", response_model=list[Reading], tags=["farm"])
def readings(
    user: User,
    store: Store,
    node: str,
    metric: str,
    from_: Annotated[int | None, Query(alias="from", description="Unix seconds, default 24 h ago")] = None,
    to: Annotated[int | None, Query(description="Unix seconds, default now")] = None,
    limit: Annotated[int, Query(ge=1, le=10000)] = 5000,
):
    end = to if to is not None else int(time.time())
    start = from_ if from_ is not None else end - 24 * 3600
    if start > end:
        raise HTTPException(status.HTTP_422_UNPROCESSABLE_ENTITY, "`from` must be before `to`")
    return store.readings(node, metric, start, end, limit)


@app.get("/api/events", tags=["farm"])
def events(
    user: User,
    store: Store,
    node: str | None = None,
    type: str | None = None,
    limit: Annotated[int, Query(ge=1, le=500)] = 50,
) -> list[dict]:
    return store.events(node, type, limit)


@app.post("/api/nodes/{node_id}/pump", status_code=status.HTTP_202_ACCEPTED, response_model=PumpOut, tags=["control"])
def pump(
    node_id: str,
    body: PumpIn,
    user: User,
    settings: SettingsDep,
    publisher: Annotated[MqttPublisher, Depends(get_publisher)],
):
    if node_id not in settings.pump_nodes:
        raise HTTPException(status.HTTP_404_NOT_FOUND, f"{node_id} has no pump")
    # The firmware enforces the same cap; this keeps a bad request from even asking for more.
    duration = min(body.duration_s, settings.max_pump_s)
    try:
        publisher.command(node_id, {"action": "pump", "duration_s": duration})
    except OSError as exc:
        log.error("could not reach MQTT broker: %s", exc)
        raise HTTPException(status.HTTP_503_SERVICE_UNAVAILABLE, "MQTT broker unreachable") from exc
    log.info("%s started pump on %s for %d s", user, node_id, duration)
    return {"ok": True, "duration_s": duration}


@app.get("/api/health", include_in_schema=False)
def health():
    return {"ok": True}
