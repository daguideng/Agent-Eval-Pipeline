# test_runner.py
import json
import time
import re
import pymysql
import datetime
from tabulate import tabulate
from evaluator import (
    evaluate_multi_dimension, 
    get_dimensions, 
    run_rule_checks, 
    run_deterministic_checks, 
    extract_score
)
from monitor import upload_metrics, get_langfuse_url
from config import DB_HOST, DB_USER, DB_PASS, DB_NAME

# 导入你的被测 Agent
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
    
    # 准备数据源：一份给 Markdown，一份给终端
    markdown_rows = []
    terminal_data = []
    
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

                res = agent.run(query)
                answer = res.get("answer", "")
                
                print("\n--- 🕵️ Agent 完整执行轨迹 ---")
                print(answer)

                tokens = res.get("tokens", 0)
                llm_time = res.get("llm_time", 0.0)
                tool_time = res.get("tool_time", 0.0)
                ttft = res.get("ttft", 0.0)
                tpot = res.get("tpot", 0.0) 

                print(f"📊 [性能看板] 模型纯耗时: {llm_time:.3f}s | TTFT: {ttft:.3f}s | TPOT: {tpot:.4f}s | 工具耗时: {tool_time:.3f}s")
                print("-" * 30)

                is_valid, rule_msg, metrics = run_deterministic_checks(answer, tokens, 200)
                if is_valid:
                    rule_passed, rule_msg = run_rule_checks(query, answer)
                    is_valid = is_valid and rule_passed

                judge_score_text = None
                judge_time = 0.0
                final_score = 0.0
                faithfulness = 0.0
                hallucination_str = "❌ 是"

                if is_valid:
                    print("🛡️ 规则校验: 规则通过")
                    judge_score_text, judge_time = evaluate_multi_dimension(query, answer)
                    print(f"⚖️ 裁判打分完成. 耗时: {judge_time:.2f}s")
                    
                    clean_text = re.sub(r'```json\s*|\s*```', '', str(judge_score_text)).strip()
                    data = json.loads(clean_text)
                    
                    for dim in dimensions:
                        dim_score = float(data.get(dim, {}).get("score", 0))
                        cursor.execute("INSERT INTO eval_metrics (run_id, case_id, metric_name, metric_value, metric_type) VALUES (%s, %s, %s, %s, %s)", (run_id, case_id, dim, dim_score, "raw"))
                    
                    faithfulness = float(data.get("faithfulness", 0.0))
                    h_raw = int(data.get("hallucination", 0))
                    hallucination_str = "✅ 否" if h_raw == 0 else "❌ 是"
                    
                    print(f"📊 [评测指标] 忠实度: {faithfulness} | 幻觉: {hallucination_str}")
                    
                    final_score = extract_score(judge_score_text)
                    total_score += final_score
                    valid_cases_count += 1
                    
                    dim_scores = {d: data.get(d, {}).get("score", "-") for d in dimensions}
                else:
                    print(f"🛡️ 规则校验: 规则拦截：{rule_msg}")
                    print("❌ 被规则引擎拦截，跳过裁判打分！")
                    dim_scores = {d: '-' for d in dimensions}

                trace_id = upload_metrics(
                    case_id=case_id, query=query, final_answer=answer, rule_msg=rule_msg, 
                    is_valid=is_valid, judge_score=judge_score_text, llm_total_time=llm_time, 
                    ttft=ttft, tpot=tpot, tool_exec_time=tool_time, judge_time=judge_time, 
                    token_drift=metrics.get("token_drift", 0.0)
                )
                
                langfuse_url = get_langfuse_url(trace_id)
                if langfuse_url:
                    print(f"✅ [Monitor] 上报成功 (Trace 链接: {langfuse_url})\n" + "="*50)
                else:
                    print(f"❌ [Monitor] 上报失败\n" + "="*50)

                try:
                    cursor.execute("INSERT INTO eval_case_details (run_id, case_id, query_text, final_answer, is_passed, trace_id) VALUES (%s, %s, %s, %s, %s, %s)", 
                                   (run_id, case_id, query, answer, 1 if is_valid else 0, langfuse_url))
                    
                    metric_sql = "INSERT INTO eval_metrics (run_id, case_id, metric_name, metric_value, metric_type) VALUES (%s, %s, %s, %s, %s)"
                    cursor.execute(metric_sql, (run_id, case_id, "ttft", float(ttft), "raw"))
                    cursor.execute(metric_sql, (run_id, case_id, "tpot", float(tpot), "raw"))
                    cursor.execute(metric_sql, (run_id, case_id, "tokens", float(tokens), "raw"))
                    cursor.execute(metric_sql, (run_id, case_id, "llm_time", float(llm_time), "raw"))
                    cursor.execute(metric_sql, (run_id, case_id, "tool_time", float(tool_time), "raw"))
                    conn.commit()
                except Exception as e:
                    print(f"  └─ ❌ 数据库写入失败: {e}")

                # ==============================
                # 组装数据 (Markdown 和 终端分开)
                # ==============================
                d_acc = dim_scores.get('accuracy', '-')
                d_rel = dim_scores.get('relevance', '-')
                d_saf = dim_scores.get('safety', '-')
                d_tool = dim_scores.get('tool_call', '-')
                score_str = f"**{final_score}**" if is_valid else "**0.0**"
                link_str = f"[查看]({langfuse_url})" if langfuse_url else "-"

                # 1. 写入 Markdown 的行 (带链接和加粗)
                markdown_rows.append(f"| {case_id} | {query[:15]}... | {score_str} | {d_acc} | {d_rel} | {d_saf} | {d_tool} | {faithfulness} | {hallucination_str} | {ttft:.2f}s | {tpot:.4f}s | {link_str} |")
                
                # 2. 写入终端表格的行 (纯数字，不带 Markdown 符号)
                trace_short = trace_id[:8] + "..." if trace_id else "-"
                terminal_data.append([case_id, query[:12]+"...", final_score, d_acc, d_rel, d_saf, d_tool, faithfulness, hallucination_str, f"{ttft:.2f}s", f"{tpot:.4f}s", trace_short])

    except Exception as e:
        conn.rollback()
        print(f"\n❌ 运行过程发生异常: {e}")
    finally:
        conn.close()

    # ==========================================
    # 生成 Markdown 文件 (保持标准格式)
    # ==========================================
    print("\n📄 正在生成本地评测报告...")
    avg_score = round(total_score / valid_cases_count, 2) if valid_cases_count > 0 else 0.0
    
    report_md = [
        "# 🤖 AI Agent 自动化质量评测报告\n",
        "## 📊 测试汇总",
        f"- **测试用例总数**: {len(test_cases)}",
        f"- **有效打分用例数**: {valid_cases_count}",
        f"- **平均得分**: `{avg_score} / 10.0`\n",
        "> 💡 **指标字典**：",
        "> * **忠实度**：1.0 表示回答完全基于事实未捏造；",
        "> * **幻觉检测**：'✅ 否' 表示无瞎编，'❌ 是' 表示出现事实错误；",
        "> * **TTFT**：首字延迟；**TPOT**：每字耗时。\n",
        "## 📝 详细结果",
        "| ID | 提问 (Query) | 得分 | 准确 | 相关 | 安全 | 工具 | 忠实度 | 幻觉检测 | TTFT | TPOT | Trace 链路 |",
        "| :---: | :--- | :---: | :---: | :---: | :---: | :---: | :---: | :---: | :---: | :---: | :---: |"
    ] + markdown_rows

    with open("evaluation_report.md", "w", encoding="utf-8") as f:
        f.write("\n".join(report_md))
    
    print(f"✅ 评测完毕！生成了 evaluation_report.md")

    # ==========================================
    # 在终端直接渲染漂亮的 ASCII 表格！
    # ==========================================
    print("\n" + "="*100)
    print(f"🏆 评测结果汇总 (平均分: {avg_score})")
    
    headers = [
        "ID", "提问", "得分", "准确", "相关", "安全", "工具", 
        "忠实度", "幻觉检测", "TTFT", "TPOT", "Trace ID"
    ]
    
    print(tabulate(terminal_data, headers=headers, tablefmt="grid", maxcolwidths=[None, 15, None, None, None, None, None, None, None, None, None, 12]))
    
    print("="*100)
    print("💡 [指标字典] 帮助业务方快速看懂：")
    print("   - 忠实度 (Faithfulness) : 1.0 代表基于事实；0.0 代表严重脱离事实")
    print("   - 幻觉检测 (Hallucination): '✅ 否' 代表没瞎编；'❌ 是' 代表出现事实错误")
    print("   - TTFT / TPOT           : 首字延迟(用户等待时长) / 每字耗时(生成速度)")
    print("====================================================================================================\n")

if __name__ == "__main__":
    main()
