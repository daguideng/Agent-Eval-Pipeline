# test_runner.py
import json
import time
import re
from agent_bot import run_agent
from evaluator import run_rule_checks, evaluate_multi_dimension, extract_score
from monitor import upload_metrics
from config import LANGFUSE_HOST

def main():
    with open("test_cases.json", "r", encoding="utf-8") as f:
        test_cases = json.load(f)

    report_data = []
    
    for case in test_cases:
        print(f"\n==================================================")
        print(f"🚀 Start Case [{case['id']}], Query: {case['query']}")

        final_answer, llm_total_time, tool_exec_time = run_agent(case['query'], case['id'])
        
        print(f"\n--- 🕵️ Agent 完整执行轨迹 ---")
        print(final_answer)
        print(f"------------------------------")

        # 1. 提取性能指标
        ttft = 0.0
        tpot = 0.0
        ttft_match = re.search(r"TTFT\(首字延迟\): ([\d\.]+)s", final_answer)
        tpot_match = re.search(r"TPOT\(每字耗时\): ([\d\.]+)s", final_answer)
        if ttft_match: ttft = float(ttft_match.group(1))
        if tpot_match: tpot = float(tpot_match.group(1))

        # 2. 规则校验
        is_valid, rule_msg = run_rule_checks(final_answer)
        print(f"🛡️ 规则校验: {rule_msg}")

        # 3. 裁判打分
        score_text = ""
        judge_time = 0.0
        final_score = 0.0
        faithfulness = 0.0
        hallucination = 1
        dim_scores = {"accuracy": "-", "relevance": "-", "safety": "-", "tool_call": "-"}

        if is_valid:
            start_judge = time.time() 
            score_text, _ = evaluate_multi_dimension(case['query'], final_answer)
            judge_time = time.time() - start_judge
            
            print(f"⚖️ 裁判打分完成. 耗时: {judge_time:.2f}s")
            final_score = extract_score(score_text)
            
            try:
                start_idx = score_text.find('{')
                end_idx = score_text.rfind('}') + 1
                data = json.loads(score_text[start_idx:end_idx])
                for dim in dim_scores.keys():
                    dim_scores[dim] = data.get(dim, {}).get("score", 0)
                faithfulness = float(data.get("faithfulness", 0.0))
                hallucination = int(data.get("hallucination", 1))
                
                # 💡 关键：终端打印评测指标
                print(f"📊 [评测指标] 忠实度(Faithfulness): {faithfulness} | 幻觉(Is_Hallucination): {hallucination}")
                
            except Exception as e:
                print(f"[!] 评测 JSON 解析失败: {e}")
        else:
            print("❌ 被规则引擎拦截，跳过裁判打分！")

        # 4. 上报 LangFuse
        trace_id = upload_metrics(
            case_id=case['id'], query=case['query'], final_answer=final_answer,
            rule_msg=rule_msg, is_valid=is_valid, judge_score=score_text,
            llm_total_time=llm_total_time, ttft=ttft, tpot=tpot, 
            tool_exec_time=tool_exec_time, judge_time=judge_time
        )

        report_data.append({
            "case_id": case['id'], "query": case['query'], "passed_rule": is_valid,
            "final_score": final_score, "dims": dim_scores, "trace_id": trace_id, 
            "hallucination": hallucination, "faithfulness": faithfulness, "ttft": ttft
        })

    # ================= 生成 Markdown 报告 =================
    print("\n" + "="*50)
    print("📄 正在生成本地评测报告...")
    
    md_content = "# 🤖 AI Agent 自动化质量评测报告\n\n"
    md_content += "## 📊 测试汇总\n"
    total_score = sum([r["final_score"] for r in report_data]) / len(report_data) if report_data else 0
    md_content += f"- **测试用例总数**: {len(report_data)}\n"
    md_content += f"- **平均得分**: `{total_score:.2f} / 10.0`\n\n"

    md_content += "## 📝 详细结果\n"
    md_content += "| ID | 提问 (Query) | 得分 | 准确 | 相关 | 安全 | 工具 | 忠实度 | 幻觉(0/1) | TTFT | Trace 链路 |\n"
    md_content += "|---|---|---|---|---|---|---|---|---|---|---|\n"
    
    for r in report_data:
        trace_link = f"[查看]({LANGFUSE_HOST}/trace/{r['trace_id']})" if r['trace_id'] else "未上传"
        d = r['dims']
        if not r["passed_rule"]:
            md_content += f"| {r['case_id']} | {r['query'][:10]}... | **{r['final_score']}** | - | - | - | - | - | - | {r['ttft']:.2f}s | {trace_link} |\n"
        else:
            md_content += f"| {r['case_id']} | {r['query'][:10]}... | **{r['final_score']}** | {d['accuracy']} | {d['relevance']} | {d['safety']} | {d['tool_call']} | {r['faithfulness']} | {r['hallucination']} | {r['ttft']:.2f}s | {trace_link} |\n"

    with open("evaluation_report.md", "w", encoding="utf-8") as f:
        f.write(md_content)

    print("✅ 评测完毕！生成了 evaluation_report.md")
    print("👉 打开 LangFuse 看板，查看 Faithfulness 与 Is_Hallucination 指标！")

if __name__ == "__main__":
    main()
