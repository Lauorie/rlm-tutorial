import re
import ast
import asyncio
import logging
from typing import Any, List, Optional

from llm import LLMClient
from repl import REPLEnv
from sys_prompt import SYSTEM_PROMPT

logger = logging.getLogger(__name__)

# 子 LLM 需要聚合长答案，给它更大的输出预算
SUB_LLM_MAX_TOKENS = 4096


class RLM:
    """带异步 REPL 环境的递归语言模型（Recursive Language Model）。"""

    # 当模型不写代码、直接用文字作答时，回灌的纠正提示
    _NUDGE = (
        "Your prose reply does NOT count as an answer, and you must not guess from memory. "
        "You MUST write a single ```repl code block, actually inspect the `context` variable "
        "(e.g. slice it or use llm_query on chunks), and submit the result by calling "
        "FINAL(answer) INSIDE that code block. Do not answer in prose."
    )

    # 迭代预算用尽仍未 FINAL 时，强制收口的提示（接受纯文本直接作答）
    _FORCE_FINAL = (
        "You have no exploration turns left. Based ONLY on what you have already found "
        "above, reply with the direct final answer to the question in one short sentence. "
        "Answer in plain text (no code). If the document does not contain the answer, "
        "reply exactly: Not found in the document."
    )

    def __init__(
        self,
        model: str = "auto",
        sub_model: str = "auto",
        max_iterations: int = 5,
    ) -> None:
        """初始化 RLM。

        Args:
            model: 主控 LLM 的模型名（"auto" 自动探测）。
            sub_model: 递归子 LLM 的模型名（"auto" 自动探测）。
            max_iterations: 主控循环的最大迭代轮数。
        """
        self.llm = LLMClient(model=model)
        self.sub_llm = LLMClient(model=sub_model, max_tokens=SUB_LLM_MAX_TOKENS)
        self.max_iterations = max_iterations
        self.repl: Optional[REPLEnv] = None

    async def _llm_query(self, prompt: str) -> Any:
        """供 REPL 内部使用的**异步**递归 LLM 调用。

        在线程池中执行同步的 OpenAI 调用，从而让 REPL 里的
        ``asyncio.gather`` 能够真正并行多个子查询。返回子 LLM 答案；
        若子 LLM 用 FINAL(...) 包裹，则尽量解析为对应的 Python 对象。
        """
        text = await asyncio.to_thread(
            self.sub_llm.chat, [{"role": "user", "content": prompt}]
        )
        return self._parse_sub_answer(text)

    @staticmethod
    def _parse_sub_answer(text: str) -> Any:
        """解析子 LLM 的回复：若含 FINAL(...) 则取其内容并尝试转为 Python 字面量。"""
        idx = text.find("FINAL(")
        if idx == -1:
            return text
        inner = RLM._extract_balanced(text, idx + len("FINAL"))
        if inner is None:
            return text
        inner = inner.strip()
        try:
            return ast.literal_eval(inner)  # 还原 list/dict/数字等字面量
        except (ValueError, SyntaxError):
            return inner  # 普通字符串答案

    @staticmethod
    def _extract_balanced(text: str, start: int) -> Optional[str]:
        """从 ``start``（指向左括号）开始抽取括号平衡的内容。"""
        depth = 0
        for i in range(start, len(text)):
            ch = text[i]
            if ch == "(":
                depth += 1
            elif ch == ")":
                depth -= 1
                if depth == 0:
                    return text[start + 1 : i]
        return None  # 括号未闭合

    @staticmethod
    def _find_code_blocks(text: str) -> List[str]:
        """从响应中抽取 ```repl 代码块。"""
        pattern = r"```repl\s*\n(.*?)\n```"
        return re.findall(pattern, text, re.DOTALL)

    def completion(self, context: Any, query: str, verbose: bool = True) -> Any:
        """运行 RLM，基于 context 回答 query。

        Args:
            context: 上下文数据（通常为长文本字符串）。
            query: 待回答的问题。
            verbose: 为 True 时输出迭代过程日志。

        Returns:
            主 LLM 通过 FINAL() 提交的答案（任意类型）；未给出则返回 None。
        """
        if verbose:
            logging.getLogger().setLevel(logging.INFO)

        # 用上下文初始化异步 REPL
        self.repl = REPLEnv(llm_query_fn=self._llm_query, context=context)

        # 构建初始消息：系统提示词原样使用（含字面 {} 不可 format），
        # 上下文元信息按提示词约定通过用户消息单独告知模型。
        ctx_meta = (
            f"Context metadata: type={type(context).__name__}, "
            f"total_characters={len(str(context))}."
        )
        messages: List[dict] = [
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": ctx_meta},
            {
                "role": "user",
                "content": (
                    f'First, explore the context in the REPL. Then answer: "{query}"'
                    "\n\nYour next action:"
                ),
            },
        ]

        try:
            for iteration in range(self.max_iterations):
                logger.info("%s [迭代 %d/%d]", "=" * 40, iteration + 1, self.max_iterations)

                response = self.llm.chat(messages)
                messages.append({"role": "assistant", "content": response})

                logger.info("响应:\n%s%s", response[:500], "..." if len(response) > 500 else "")

                code_blocks = self._find_code_blocks(response)

                # 模型没写任何 repl 代码（往往是直接用大白话瞎答）：
                # 不能放任循环空转，必须明确纠正它去用 REPL + FINAL。
                if not code_blocks:
                    logger.info("未检测到 ```repl 代码块，提示模型必须用 REPL 并调用 FINAL()")
                    messages.append({"role": "user", "content": self._NUDGE})
                    continue

                # 执行响应中的代码块
                for code in code_blocks:
                    output = self.repl.execute(code)
                    logger.info(
                        "REPL 输出:\n%s%s", output[:500], "..." if len(output) > 500 else ""
                    )
                    messages.append(
                        {
                            "role": "user",
                            "content": f"Code executed:\n```python\n{code}\n```\n\nOutput:\n{output}",
                        }
                    )

                    # FINAL() 被调用即结束
                    if self.repl.has_final:
                        logger.info("%s ✓ 已得到最终答案", "=" * 40)
                        return self.repl.final_value

            # 预算用尽仍未 FINAL：强制最后一搏，逼模型基于已有发现收口
            logger.info("%s 迭代预算用尽，强制最后一次直接作答", "=" * 40)
            messages.append({"role": "user", "content": self._FORCE_FINAL})
            response = self.llm.chat(messages)

            # 若它仍写了 repl 代码并调用 FINAL，优先采用
            for code in self._find_code_blocks(response):
                self.repl.execute(code)
                if self.repl.has_final:
                    logger.info("%s ✓ 已得到最终答案（强制收口）", "=" * 40)
                    return self.repl.final_value

            # 兜底：接受纯文本直接作答（已读过文档，非凭记忆瞎答）
            parsed = self._parse_sub_answer(response) if response else ""
            answer = parsed.strip() if isinstance(parsed, str) else parsed
            if answer not in (None, ""):
                logger.info("%s ✓ 已得到最终答案（纯文本兜底）", "=" * 40)
                return answer

            logger.warning("达到最大迭代轮数（%d）仍未给出最终答案", self.max_iterations)
            return None
        finally:
            self.repl.close()
