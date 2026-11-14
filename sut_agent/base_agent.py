# sut_agent/base_agent.py
from abc import ABC, abstractmethod

class BaseAgent(ABC):
    """
    所有被测 Agent 必须继承此基类，并实现 run 方法。
    这就是测试架构师定的规矩。
    """
    @abstractmethod
    def run(self, user_query: str) -> dict:
        """
        必须返回一个字典，包含以下字段：
        {
            "answer": str,           # Agent 的最终文本回答
            "tool_calls": list,      # 调用的工具列表 [{"name": "xx", "args": {...}}]
            "tokens": int,           # 消耗的 Token 数量
            "llm_time": float,       # 大模型耗时
            "tool_time": float,      # 工具耗时
            "ttft": float,           # 首字延迟
            "tpot": float            # 每字耗时
        }
        """
        pass
