"""mini-RLM：一个简化但保留核心思想的递归语言模型教学实现。

最小用法：

    from mini_rlm import MiniRLM, RLMConfig, MockLM

    # 零成本：用 MockLM 脚本驱动一整轮 RLM 循环
    mock = MockLM(responses=[
        "先看看 context\\n```repl\\nprint(len(context))\\n```",
        "```repl\\nanswer['content'] = '一共 ' + str(len(context)) + ' 字符'\\nanswer['ready'] = True\\n```",
    ])
    rlm = MiniRLM(config=RLMConfig(max_iterations=4), client=mock)
    result = rlm.completion(context="hello world" * 100, task="统计字符数")
    print(result.response)
"""

from .clients import BaseLM, MockLM, OpenAICompatClient, build_client
from .logger import TrajectoryLogger
from .repl import MiniREPL
from .rlm import MiniRLM
from .types import (
    CodeBlock,
    Message,
    REPLResult,
    RLMConfig,
    RLMIteration,
    RLMResult,
    UsageSummary,
)

__all__ = [
    "MiniRLM",
    "MiniREPL",
    "RLMConfig",
    "BaseLM",
    "MockLM",
    "OpenAICompatClient",
    "build_client",
    "TrajectoryLogger",
    "Message",
    "REPLResult",
    "CodeBlock",
    "RLMIteration",
    "RLMResult",
    "UsageSummary",
]
