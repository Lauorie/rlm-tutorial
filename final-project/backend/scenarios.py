"""预设在线 Demo 场景：脚本化的 MockLM 剧本，供 Serverless / 本地服务共用。

每个场景 = (context, task, mock 剧本)。剧本里 responses 的顺序必须严格等于
真实调用顺序（递归场景里父子共享一个 MockLM，要把子调用穿插进去）。
"""

from __future__ import annotations

import os
from typing import Any

from mini_rlm import MiniRLM, MockLM, RLMConfig, TrajectoryLogger


def _repl(code: str) -> str:
    return f"```repl\n{code}\n```"


def _submit(content: str) -> str:
    return _repl(f"answer['content'] = {content!r}\nanswer['ready'] = True")


def get_scenarios() -> dict[str, dict[str, Any]]:
    secret_ctx = "\n".join(
        [f"[{i}] INFO ok" for i in range(120)]
        + ["[120] CONFIG SECRET_TOKEN=sk-rlm-9f3a2b"]
        + [f"[{i}] INFO ok" for i in range(121, 240)]
    )
    summary_ctx = (
        "### 第一章 背景\n长上下文模型会 context rot，越长越糊。\n"
        "### 第二章 思想\nRLM 把 prompt 放进 REPL 当变量，用代码 peek。\n"
        "### 第三章 递归\nrlm_query 让子调用也是完整 RLM。\n"
    )
    return {
        "find-secret": {
            "context": secret_ctx,
            "task": "找出日志里的 SECRET_TOKEN 值",
            "max_depth": 1,
            "responses": [
                "先看看日志规模。\n" + _repl("print('字符', len(context))\nprint(context[:60])"),
                "用正则定位 token。\n"
                + _repl(
                    "import re\nm = re.search(r'SECRET_TOKEN=(\\S+)', context)\n"
                    "token = m.group(1)\nprint('命中', token)"
                ),
                _repl(
                    "answer['content'] = f'SECRET_TOKEN 的值是 {token}'\n"
                    "answer['ready'] = True"
                ),
            ],
        },
        "recursive-summary": {
            "context": summary_ctx,
            "task": "生成全文摘要（递归）",
            "max_depth": 2,
            "responses": [
                "按章节拆开，每章交给子 RLM。\n"
                + _repl(
                    "chs=[c.strip() for c in context.split('###') if c.strip()]\n"
                    "sums=[]\n"
                    "for c in chs:\n    s=rlm_query(f'一句话总结：{c}')\n"
                    "    sums.append(s)\n    print(s)"
                ),
                _submit("背景：长上下文会退化"),
                _submit("思想：prompt 当环境用代码读"),
                _submit("递归：子调用也是完整 RLM"),
                "汇总并交卷。\n"
                + _repl("answer['content']=' / '.join(sums)\nanswer['ready']=True"),
            ],
        },
    }


def run_scenario(scenario: str, use_real: bool = False) -> dict[str, Any]:
    """跑一个预设场景，返回前端要的轨迹 payload。"""
    scenarios = get_scenarios()
    spec = scenarios.get(scenario) or scenarios["find-secret"]

    logger = TrajectoryLogger()
    if use_real:
        from mini_rlm.clients import OpenAICompatClient

        model = os.getenv("RLM_MODEL", "gpt-4o-mini")
        client = OpenAICompatClient(model_name=model)
        config = RLMConfig(
            model_name=model, backend="openai", max_iterations=8, max_depth=spec["max_depth"]
        )
    else:
        client = MockLM(responses=list(spec["responses"]))
        config = RLMConfig(
            model_name="mock-model", max_iterations=8, max_depth=spec["max_depth"]
        )

    MiniRLM(config=config, client=client, trajectory_logger=logger).completion(
        context=spec["context"], task=spec["task"]
    )
    return logger.last_payload or {}


__all__ = ["get_scenarios", "run_scenario"]
