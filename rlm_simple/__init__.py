"""rlm_simple —— 递归语言模型（RLM）的精简实现。

既支持在目录内直接运行脚本（``python main.py``），也支持作为包导入
（``import rlm_simple``）。为兼容扁平的绝对导入，这里把自身目录加入 sys.path。
"""
import os
import sys

# 让扁平的绝对导入（from llm import ...）在被当作包导入时也能解析
_PKG_DIR = os.path.dirname(os.path.abspath(__file__))
if _PKG_DIR not in sys.path:
    sys.path.insert(0, _PKG_DIR)

from rlm import RLM
from llm import LLMClient
from repl import REPLEnv

__all__ = ["RLM", "LLMClient", "REPLEnv"]
