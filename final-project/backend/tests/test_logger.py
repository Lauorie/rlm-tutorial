"""轨迹日志测试：payload 结构与落盘。"""

import json
import os

from mini_rlm import MiniRLM, MockLM, RLMConfig, TrajectoryLogger


def _run(log_dir: str | None = None) -> TrajectoryLogger:
    logger = TrajectoryLogger(log_dir=log_dir)
    mock = MockLM(
        responses=[
            "```repl\nprint(len(context))\n```",
            "```repl\nanswer['content'] = 'ok'\nanswer['ready'] = True\n```",
        ]
    )
    rlm = MiniRLM(config=RLMConfig(max_iterations=4), client=mock, trajectory_logger=logger)
    rlm.completion(context="hello" * 10, task="t")
    return logger


def test_payload_structure() -> None:
    logger = _run()
    payload = logger.last_payload
    assert payload is not None
    assert payload["metadata"]["type"] == "metadata"
    assert payload["metadata"]["final_answer"] == "ok"
    assert payload["metadata"]["total_iterations"] == 2
    assert len(payload["iterations"]) == 2
    assert payload["iterations"][0]["code_blocks"][0]["code"]


def test_writes_jsonl(tmp_path) -> None:
    logger = _run(log_dir=str(tmp_path))
    files = [f for f in os.listdir(tmp_path) if f.endswith(".jsonl")]
    assert len(files) == 1
    lines = (tmp_path / files[0]).read_text(encoding="utf-8").strip().splitlines()
    # 第一行 metadata，其余是 iterations
    assert json.loads(lines[0])["type"] == "metadata"
    assert json.loads(lines[1])["iteration"] == 0
