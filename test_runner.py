# test_runner.py
import json
import time
import re
import pymysql
import datetime
from evaluator import (
    evaluate_multi_dimension, 
    get_dimensions, 
    run_rule_checks, 
    run_deterministic_checks, 
    extract_score
)
from monitor import upload_metrics
from config import DB_HOST, DB_USER, DB_PASS, DB_NAME

# 导入你的单版本 Agent
from sut_agent.my_agent import MyTerminalAgent

def get_db_connection():
    return pymysql.connect(
        host=DB_HOST, user=DB_USER, password=DB_PASS, 
        database=DB_NAME, charset='utf8mb4',
        cursorclass=pymysql.cursors.DictCursor
    )

def create_eval_run(cursor, version_name, scenario_type, repeat_count):
    sql = "INSERT INTO eval_runs (version_name, scenario_type, repeat_count, model_name, judge_model) VALUES (%s, %s, %s, %s, %s)"
    cursor.execute(sql, (version_name, scenario_type, repeat_count, "qwen2.5:3b", "deepseek-chat"))
    return cursor.lastrowid

def main():
    with open("test_cases.json", "r", encoding="utf-8") as f:
        test_cases = json.load(f)

    agent = MyTerminalAgent()
    dimensions = get_dimensions()
    
    # 准备报告数据
    report_rows = []
    total_score = 0.0
    valid_cases_count = 0

    try:
        conn = get_db_connection()
    except Exception as e:
        print(f"❌ 数据库连接失败: {e}")
        return

    try:
        with conn.cursor() as cursor:
            run_id = create_eval_run(cursor, "sut_agent_single", "baseline", len(test_cases))
            conn.commit()

            for case in test_cases:
                case_id = case["id"]
                query = case["query"]
                
                print(f"\n🚀 Start Case [{case_id}], Query: {query}")

                # 1. 运行 Agent
                res = agent.run(query)
                answer = res.get("answer", "")
                
                # 打印执行轨迹
                print("\n--- 🕵️ Agent 完整执行轨迹 ---")
                print(answer)

                tokens = res.get("tokens", 0)
                llm_time = res.get("llm_time", 0.0)
                tool_time = res.get("tool_time", 0.0)
                ttft = res.get("ttft", 0.0)
                tpot = res.get("tpot", 0.0)

                print(f"📊 [性能看板] 模型纯耗时: {llm_time:.3f}s | TTFT(首字延迟): {ttft:.3f}s | TPOT(每字耗时): {tpot:.4f}s | 工具耗时: {tool_time:.3f}s")
                print("-" * 30)

                # 2. 规则拦截与校验
                is_valid, rule_msg, metrics = run_deterministic_checks(answer, tokens, 200)
                if is_valid:
                    rule_passed, rule_msg = run_rule_checks(query, answer)
                    is_valid = is_valid and rule_passed

                judge_score_text = None
                judge_time = 0.0
                final_score = 0.0

                # 3. 裁判打分
                if is_valid:
                    print("🛡️ 规则校验: 规则通过")
                    judge_score_text, judge_time = evaluate_multi_dimension(query, answer)
                    print(f"⚖️ 裁判打分完成. 耗时: {judge_time:.2f}s")
                    
                    # 提取分数用于报告和入库
                    clean_text = re.sub(r'```json\s*|\s*```', '', str(judge_score_text)).strip()
                    data = json.loads(clean_text)
                    for dim in dimensions:
                        dim_score = float(data.get(dim, {}).get("score", 0))
                        cursor.execute("INSERT INTO eval_metrics (run_id, case_id, metric_name, metric_value, metric_type) VALUES (%s, %s, %s, %s, %s)", (run_id, case_id, dim, dim_score, "raw"))
                    
                    faithfulness = float(data.get("faithfulness", 0.0))
                    hallucination = int(data.get("hallucination", 0))
                    print(f"📊 [评测指标] 忠实度(Faithfulness): {faithfulness} | 幻觉(Is_Hallucination): {hallucination}")
                    
                    final_score = extract_score(judge_score_text)
                    total_score += final_score
                    valid_cases_count += 1
                    
                    # 准备 Markdown 表格数据
                    dim_scores = {d: data.get(d, {}).get("score", 0) for d in dimensions}
                    report_rows.append(f"| {case_id} | {query[:15]}... | **{final_score}** | {dim_scores.get('accuracy', '-')} | {dim_scores.get('relevance', '-')} | {dim_scores.get('safety', '-')} | {dim_scores.get('tool_call', '-')} | {faithfulness} | {hallucination} | {ttft:.2f}s |")
                else:
                    print(f"🛡️ 规则校验: 规则拦截：{rule_msg}")
                    print("❌ 被规则引擎拦截，跳过裁判打分！")
                    report_rows.append(f"| {case_id} | {query[:15]}... | **0.0** | - | - | - | - | - | - | {ttft:.2f}s |")

                # 4. 数据入库 (明细与性能指标)
                try:
                    cursor.execute("INSERT INTO eval_case_details (run_id, case_id, query_text, final_answer, is_passed, trace_id) VALUES (%s, %s, %s, %s, %s, %s)", 
                                   (run_id, case_id, query, answer, 1 if is_valid else 0, None))
                    
                    metric_sql = "INSERT INTO eval_metrics (run_id, case_id, metric_name, metric_value, metric_type) VALUES (%s, %s, %s, %s, %s)"
                    cursor.execute(metric_sql, (run_id, case_id, "ttft", float(ttft), "raw"))
                    cursor.execute(metric_sql, (run_id, case_id, "tokens", float(tokens), "raw"))
                    cursor.execute(metric_sql, (run_id, case_id, "llm_time", float(llm_time), "raw"))
                    cursor.execute(metric_sql, (run_id, case_id, "tool_time", float(tool_time), "raw"))
                    conn.commit()
                except Exception as e:
                    print(f"  └─ ❌ 数据库写入失败: {e}")

                # 5. 上报 Langfuse
                trace_id = upload_metrics(
                    case_id=case_id, query=query, final_answer=answer, rule_msg=rule_msg, 
                    is_valid=is_valid, judge_score=judge_score_text, llm_total_time=llm_time, 
                    ttft=ttft, tpot=tpot, tool_exec_time=tool_time, judge_time=judge_time, 
                    token_drift=metrics.get("token_drift", 0.0)
                )
                print(f"✅ [Monitor] 数据上报 LangFuse 成功 (Trace: {trace_id})\n" + "="*50)

    except Exception as e:
        conn.rollback()
        print(f"\n❌ 运行过程发生异常: {e}")
    finally:
        conn.close()

    # 6. 生成本地 evaluation_report.md 报告
    print("📄 正在生成本地评测报告...")
    avg_score = round(total_score / valid_cases_count, 2) if valid_cases_count > 0 else 0.0
    
    report_md = [
        "# 🤖 AI Agent 自动化质量评测报告\n",
        "## 📊 测试汇总",
        f"- **测试用例总数**: {len(test_cases)}",
        f"- **有效打分用例数**: {valid_cases_count}",
        f"- **平均得分**: `{avg_score} / 10.0`\n",
        "## 📝 详细结果",
        "| ID | 提问 (Query) | 得分 | 准确 | 相关 | 安全 | 工具 | 忠实度 | 幻觉(0/1) | TTFT |",
        "|---|---|---|---|---|---|---|---|---|---|"
    ] + report_rows

    with open("evaluation_report.md", "w", encoding="utf-8") as f:
        f.write("\n".join(report_md))
    
    print(f"✅ 评测完毕！生成了 evaluation_report.md")
    print("👉 打开 LangFuse 看板，查看 Faithfulness 与 Is_Hallucination 指标！")

if __name__ == "__main__":
    main()
