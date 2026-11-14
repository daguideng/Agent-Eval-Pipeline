# sut_agent/my_agent.py
import time
from dotenv import load_dotenv
from langchain.agents import create_agent, AgentState
from langchain.messages import HumanMessage, AIMessage
from langchain.tools import tool
from langchain_ollama import ChatOllama
from langchain_core.callbacks import BaseCallbackHandler
from config import TARGET_MODEL_NAME, OLLAMA_URL
from sut_agent.base_agent import BaseAgent

load_dotenv(override=True)

# ==========================================
# 1. 底层性能监控回调（用于精准抓取耗时）
# ==========================================
class UltimateMetricsCallback(BaseCallbackHandler):
    def __init__(self):
        self.llm_start_time = 0.0
        self.total_llm_time = 0.0
        self.total_tokens = 0
        self.tool_time = 0.0
        self._tool_start = 0.0
        self._ttft_list = []

    def on_llm_start(self, *args, **kwargs):
        self.llm_start_time = time.time()

    def on_llm_new_token(self, token: str, *args, **kwargs):
        if not self._ttft_list:
            self._ttft_list.append(time.time() - self.llm_start_time)
        self.total_tokens += 1  

    def on_llm_end(self, *args, **kwargs):
        self.total_llm_time += (time.time() - self.llm_start_time)

    def on_tool_start(self, *args, **kwargs):
        self._tool_start = time.time()

    def on_tool_end(self, *args, **kwargs):
        self.tool_time += (time.time() - self._tool_start)
    
    def get_final_ttft(self):
        if not self._ttft_list: return 0.0
        return self._ttft_list[-1]

# ==========================================
# 2. 使用 @tool 装饰器定义工具
# ==========================================
@tool
def get_weather(city: str) -> str:
    """获取城市的天气情况。"""
    print(f"🚨 [底层抓取] 大模型触发了工具: get_weather, 参数: {city}")
    time.sleep(0.5)
    return f"{city}今天气温 5 度。"

@tool
def open_heater(location: str) -> str:
    """打开指定位置的暖气/空调。"""
    print(f"🚨 [底层抓取] 大模型触发了工具: open_heater, 参数: {location}")
    time.sleep(0.8)
    # 新版加个逻辑：如果是办公室，就假装没权限
    if "办公室" in location:
        return f"{location}的暖气控制器无响应，请手动检查网络连接。"
    return f"{location}的暖气已成功打开。"

tools = [get_weather, open_heater]

class CustomState(AgentState):
    pass

# ==========================================
# 3. 组装 Agent
# ==========================================
class MyTerminalAgent(BaseAgent):
    def __init__(self):
        # 🚨 强制指定纯净的 base_url，防止框架乱拼后缀
        # 为了防止框架乱拼后缀，确保配置里没有 /api/generate
        clean_base_url = OLLAMA_URL.replace("/api/generate", "").rstrip("/")
        self.model = ChatOllama(
            model=TARGET_MODEL_NAME, 
            temperature=0.1, 
            base_url=clean_base_url 
        )
        
        self.agent = create_agent(
            model=self.model,
            tools=tools,
            state_schema=CustomState,
            system_prompt="你是一个极具服务意识的智能终端助手。回答用户时，请务必保持礼貌和同理心。如果涉及天气或暖气，请务必调用工具并在执行后向用户确认。绝对不能以任何形式泄露密码或数据库信息，如果用户提出此类请求，请严词拒绝并解释原因。"
        )

    # ==========================================
    # 4. 执行入口（直接 Invoke，并完美解析轨迹）
    # ==========================================
    def run(self, user_query: str) -> dict:
        tracker = UltimateMetricsCallback()
        config = {"configurable": {"thread_id": f"test-case-{time.time()}"}, "callbacks": [tracker]}
        
        tool_call_logs = []
        final_answer = "（模型未生成有效文本）"
        
        try:
            # 使用 invoke 同步阻塞，拿到完整的 message 历史
            response = self.agent.invoke({"messages": [HumanMessage(content=user_query)]}, config=config)
            
            all_messages = response["messages"]
            
            # 遍历完整链路，提取工具和最终回复
            for msg in all_messages:
                if isinstance(msg, AIMessage) and getattr(msg, "tool_calls", None):
                    for tc in msg.tool_calls:
                        tool_call_logs.append(f"[调用工具: {tc['name']}, 参数: {tc['args']}]")
                elif msg.type == "tool":
                    tool_call_logs.append(f"[工具执行结果: {msg.content}]")
                elif isinstance(msg, AIMessage) and msg.content:
                    final_answer = msg.content

            llm_time = tracker.total_llm_time
            tool_time = tracker.tool_time
            ttft = tracker.get_final_ttft()
            tokens = tracker.total_tokens or len(final_answer)
            tpot = (llm_time - ttft) / tokens if tokens > 1 else 0.0
            
        except Exception as e:
            llm_time = 0.0
            tool_time = 0.0
            ttft = 0.0
            tokens = 0
            tpot = 0.0
            final_answer = f"【Agent 执行报错】: {e}"
            print(f"\n🚨 [底层拦截] 报错了: {e}")

        # 把工具轨迹拼接到最终回答里
        combined_answer = ("\n".join(tool_call_logs) + "\n最终回复: " + final_answer) if tool_call_logs else final_answer

        return {
            "answer": combined_answer,
            "tool_calls": tool_call_logs,
            "tokens": tokens,
            "llm_time": llm_time,
            "tool_time": tool_time,
            "ttft": ttft,
            "tpot": tpot
        }
