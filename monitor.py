# monitor.py
import requests
import base64
import uuid
import time
import json
import re
from config import PUBLIC_KEY, SECRET_KEY, LANGFUSE_HOST
from evaluator import extract_score, get_dimensions

auth_str = f"{PUBLIC_KEY}:{SECRET_KEY}"
auth_base64 = base64.b64encode(auth_str.encode('utf-8')).decode('utf-8')
HEADERS = {"Authorization": f"Basic {auth_base64}", "Content-Type": "application/json"}

# 当前配置档声明的维度清单
DIMENSIONS = get_dimensions()

def upload_metrics(case_id, query, final_answer, rule_msg, is_valid, judge_score,
                   llm_total_time, ttft, tpot, tool_exec_time, judge_time, token_drift):
    """
    注意：这里加入了 token_drift 参数，完美兼容 test_runner.py 的调用
    """
    trace_id = str(uuid.uuid4())
    current_time = time.strftime("%Y-%m-%dT%H:%M:%S.000Z", time.gmtime())

    payload = {
        "batch": [
            {"id": str(uuid.uuid4()), "type": "trace-create", "timestamp": current_time,
             "body": {"id": trace_id, "name": f"Case-{case_id}", "input": query, "output": final_answer}},
            {"id": str(uuid.uuid4()), "type": "generation-create", "timestamp": current_time,
             "body": {"id": str(uuid.uuid4()), "traceId": trace_id, "name": "Agent-Response",
                      "model": "qwen2.5:3b", "input": query, "output": final_answer,
                      "metadata": {
                          "LLM_Total_Time": f"{round(llm_total_time, 2)}s",
                          "TTFT": f"{round(ttft, 3)}s",
                          "TPOT": f"{round(tpot, 4)}s",
                          "Tool_Time": f"{round(tool_exec_time, 2)}s",
                          "Token_Drift": f"{token_drift * 100:.1f}%"
                      }}},
            {"id": str(uuid.uuid4()), "type": "span-create", "timestamp": current_time,
             "body": {"id": str(uuid.uuid4()), "traceId": trace_id, "name": "Rule-Check",
                      "input": final_answer, "output": rule_msg}}
        ]
    }

    if is_valid and judge_score:
        payload["batch"].append({
            "id": str(uuid.uuid4()), "type": "generation-create", "timestamp": current_time,
            "body": {"id": str(uuid.uuid4()), "traceId": trace_id, "name": "LLM-Judge",
                     "model": "deepseek-chat", "input": query, "output": judge_score,
                     "metadata": {"judge_time": f"{round(judge_time, 2)}s"}}
        })

        try:
            clean_text = re.sub(r'```json\s*|\s*```', '', str(judge_score)).strip()
            data = json.loads(clean_text)

            # 动态遍历维度写入分数
            for dim in DIMENSIONS:
                dim_score = data.get(dim, {}).get("score", 0)
                payload["batch"].append({
                    "id": str(uuid.uuid4()), "type": "score-create", "timestamp": current_time,
                    "body": {"traceId": trace_id, "name": f"Dim_{dim}", "value": float(dim_score)}
                })

            faithfulness = float(data.get("faithfulness", 0.0))
            payload["batch"].append({
                "id": str(uuid.uuid4()), "type": "score-create", "timestamp": current_time,
                "body": {"traceId": trace_id, "name": "Metric_Faithfulness", "value": faithfulness}
            })

            hallucination = int(data.get("hallucination", 1))
            payload["batch"].append({
                "id": str(uuid.uuid4()), "type": "score-create", "timestamp": current_time,
                "body": {"traceId": trace_id, "name": "Is_Hallucination", "value": float(hallucination)}
            })

        except Exception as e:
            print(f"[Monitor] JSON Parse Failed: {e}")

        # 最终得分（加权+一票否决）
        payload["batch"].append({
            "id": str(uuid.uuid4()), "type": "score-create", "timestamp": current_time,
            "body": {"traceId": trace_id, "name": "Final_Score", "value": extract_score(judge_score)}
        })

    try:
        res = requests.post(f"{LANGFUSE_HOST}/api/public/ingestion", headers=HEADERS, json=payload)
        if res.status_code in [200, 207]:
            return trace_id
        else:
            print(f"[Monitor] 上报失败 status={res.status_code}: {res.text[:200]}")
    except Exception as e:
        print(f"[Monitor] 连接失败: {e}")
    return None
