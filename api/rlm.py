"""Vercel Python Serverless 入口：在线跑一次 mini-RLM，返回轨迹 JSON。

为什么默认用 MockLM？因为 Serverless 函数有执行时限（Hobby 计划约 10s），而真实 RLM
多轮调用大模型可能很慢、还要 API key。所以在线 Demo 默认跑"脚本化场景"——用 MockLM
按预设剧本走完一遍真实的 RLM 循环，毫秒级返回，零成本零配置。

想跑真实模型？请求加 {"use_real": true}，并在 Vercel 环境变量里配好 OPENAI_API_KEY
（可选 OPENAI_BASE_URL、RLM_MODEL）。注意真实运行可能超时。

请求体：{"scenario": "find-secret" | "recursive-summary", "use_real": false}
"""

from __future__ import annotations

import json
import os
import sys
from http.server import BaseHTTPRequestHandler

# 把 mini_rlm 包与 scenarios 模块加入路径。
# Vercel 部署时整个仓库都在，靠 vercel.json 的 includeFiles 保证这些文件被打进函数。
_BACKEND = os.path.abspath(
    os.path.join(os.path.dirname(__file__), "..", "final-project", "backend")
)
sys.path.insert(0, _BACKEND)

from scenarios import run_scenario  # noqa: E402


class handler(BaseHTTPRequestHandler):
    def _cors(self) -> None:
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("Access-Control-Allow-Methods", "POST, OPTIONS")
        self.send_header("Access-Control-Allow-Headers", "Content-Type")

    def do_OPTIONS(self) -> None:  # noqa: N802
        self.send_response(204)
        self._cors()
        self.end_headers()

    def do_POST(self) -> None:  # noqa: N802
        try:
            length = int(self.headers.get("Content-Length", 0))
            body = self.rfile.read(length) if length else b"{}"
            req = json.loads(body or b"{}")
            payload = run_scenario(
                req.get("scenario", "find-secret"), bool(req.get("use_real", False))
            )
            data = json.dumps(payload, ensure_ascii=False).encode("utf-8")
            self.send_response(200)
            self.send_header("Content-Type", "application/json; charset=utf-8")
            self._cors()
            self.end_headers()
            self.wfile.write(data)
        except Exception as exc:  # 返回可读错误，前端会优雅降级到样例
            msg = json.dumps({"error": str(exc)}, ensure_ascii=False).encode("utf-8")
            self.send_response(500)
            self.send_header("Content-Type", "application/json; charset=utf-8")
            self._cors()
            self.end_headers()
            self.wfile.write(msg)
