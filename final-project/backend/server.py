"""本地开发服务器：把 /api/rlm 跑在 localhost，供前端 dev 时联调。

线上用 Vercel Serverless（api/rlm.py），本地用这个 FastAPI 服务，两者共用 scenarios.py。

运行：
    uv pip install -e ".[api]"
    uvicorn server:app --reload --port 8000
然后前端 `npm run dev`（vite 已把 /api 代理到 :8000）。
"""

from __future__ import annotations

from typing import Any

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

from scenarios import run_scenario

app = FastAPI(title="mini-RLM Dev API")
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)


class RunRequest(BaseModel):
    scenario: str = "find-secret"
    use_real: bool = False


@app.post("/api/rlm")
def run(req: RunRequest) -> dict[str, Any]:
    return run_scenario(req.scenario, req.use_real)


@app.get("/api/health")
def health() -> dict[str, str]:
    return {"status": "ok"}
