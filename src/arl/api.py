from __future__ import annotations

from typing import Literal
from contextlib import asynccontextmanager
from dataclasses import asdict

from fastapi import FastAPI, HTTPException, Request, Response
from pydantic import BaseModel, ConfigDict, Field

from arl import config, diagnostic
from arl.agent import Agent
from arl.cli import build_agent
from arl.errors import SupplierError

@asynccontextmanager
async def lifespan(app: FastAPI):
    settings = config.load()
    app.state.settings = settings
    app.state.agent = build_agent(settings, display=False)
    yield

app = FastAPI(lifespan=lifespan) #nom de l'API

class Question(BaseModel):
    model_config = ConfigDict(str_strip_whitespace=True)  # "   " devient "" et échoue sur min_length

    question: str = Field(min_length=1, max_length=500, description="Question sur les notes")

class Call(BaseModel):
    tool: str
    arguments: dict | None  # None quand le modèle envoie un JSON mal formé
    result: str

class Step(BaseModel):
    step_number: int
    latency_s: float
    removed_observations: int
    entry_token: int | None  # None quand le service ne renvoie pas l'usage
    exit_token: int | None
    calls: list[Call]
    reminder: bool = False


class Verification(BaseModel):
    valid: bool
    citations: list[str]
    problems: list[str]

class ResultResponse(BaseModel):
    id: str
    date: str
    model: str
    instruction: str
    instruction_footprint: str
    question: str
    response: str
    status: Literal["termine", "limite_etapes"]
    steps: list[Step]
    notes_read: list[str]
    verification: Verification
    entry_token: int
    exit_token: int
    duration_s: float

class Check(BaseModel):
    ok: bool
    detail: str

class DiagnosticResponse(BaseModel):
    ready: bool
    checks: dict[str, Check]


@app.post("/demander", response_model=ResultResponse)
def demander(q: Question, request: Request) -> ResultResponse:
    try:
        r = request.app.state.agent.answer(q.question)
    except SupplierError as exc:
        raise HTTPException(status_code=503, detail=str(exc))
    return ResultResponse.model_validate(asdict(r))


@app.get("/diagnostic", response_model=DiagnosticResponse)
def diagnostic_route(request: Request, response: Response) -> DiagnosticResponse:
    checks = diagnostic.checks(request.app.state.settings)
    ready = all(c["ok"] for c in checks.values())
    if not ready:
        response.status_code = 503  # l'API tourne mais ne peut pas répondre aux questions
    return DiagnosticResponse(ready=ready, checks=checks)