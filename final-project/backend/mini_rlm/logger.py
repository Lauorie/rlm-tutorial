"""轨迹日志：把一次 RLM 运行写成 JSONL，供 React 前端可视化。

格式刻意对齐官方可视化器：第一行是一条 metadata，之后每行是一轮 iteration。
前端读这个文件就能画出"迭代时间线 + 对话 + 代码执行 + 递归子调用"。
"""

from __future__ import annotations

import json
import logging
import os
from typing import Any

from .types import RLMConfig, RLMResult

logger = logging.getLogger(__name__)


class TrajectoryLogger:
    """把 RLMResult 落盘成 JSONL，或仅返回内存里的 dict。"""

    def __init__(self, log_dir: str | None = None) -> None:
        """
        Args:
            log_dir: 落盘目录；None 表示只在内存里保存（通过 last_payload 取）。
        """
        self.log_dir = log_dir
        self.last_payload: dict[str, Any] | None = None
        if log_dir:
            os.makedirs(log_dir, exist_ok=True)

    def build_payload(self, result: RLMResult, config: RLMConfig) -> dict[str, Any]:
        """构造前端要的结构：{metadata, iterations}。"""
        return {
            "metadata": {
                "type": "metadata",
                "root_model": config.model_name,
                "max_depth": config.max_depth,
                "max_iterations": config.max_iterations,
                "stopped_reason": result.stopped_reason,
                "final_answer": result.response,
                "total_iterations": len(result.iterations),
                "total_code_blocks": sum(len(it.code_blocks) for it in result.iterations),
                "total_sub_calls": sum(
                    len(b.result.rlm_calls)
                    for it in result.iterations
                    for b in it.code_blocks
                ),
                "total_execution_time": result.execution_time,
                "usage": result.usage.to_dict(),
            },
            "iterations": [it.to_dict() for it in result.iterations],
        }

    def write(self, result: RLMResult, config: RLMConfig, name: str | None = None) -> str | None:
        """保存轨迹。返回写入的文件路径（仅内存时返回 None）。"""
        payload = self.build_payload(result, config)
        self.last_payload = payload

        if not self.log_dir:
            return None

        # 用迭代数+时间戳无关的稳定命名：交给调用方传 name，否则用序号
        filename = (name or f"trajectory_{len(result.iterations)}it") + ".jsonl"
        path = os.path.join(self.log_dir, filename)
        try:
            with open(path, "w", encoding="utf-8") as f:
                f.write(json.dumps(payload["metadata"], ensure_ascii=False) + "\n")
                for it in payload["iterations"]:
                    f.write(json.dumps(it, ensure_ascii=False) + "\n")
        except OSError:
            logger.exception("写轨迹日志失败：%s", path)
            return None
        return path


__all__ = ["TrajectoryLogger"]
