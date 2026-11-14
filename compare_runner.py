# compare_runner.py
import json
import time
import datetime
import pymysql
import numpy as np
from scipy import stats
from evaluator import evaluate_multi_dimension, get_dimensions, SCORE_WEIGHTS
from config import DB_HOST, DB_USER, DB_PASS, DB_NAME

# 导入你的两个 Agent
from sut_agent.my_agent import MyTerminalAgent
from sut_agent_1.my_agent import MyTerminalAgent as MyTerminalAgentV2 

def clean_json(text):
    """安全提取大模型返回的 JSON"""
    clean_text = text.replace("```json", "").replace("```", "").strip()
    start = clean_text.find('{')
    end = clean_text.rfind('}') + 1
    return json.loads(clean_text[start:end])

def get_db_connection():
    return pymysql.connect(
        host=DB_HOST, user=DB_USER, password=DB_PASS,
        database=DB_NAME, charset='utf8mb4',
        cursorclass=pymysql.cursors.DictCursor
    )

def create_eval_run(cursor, version_name, profile_name, repeat_count):
    sql = "INSERT INTO eval_runs (version_name, scenario_type, repeat_count, model_name, judge_model) VALUES (%s, %s, %s, %s, %s)"
    cursor.execute(sql, (version_name, profile_name, repeat_count, "qwen2.5:3b", "deepseek-chat"))
    return cursor.lastrowid

def calc_stats(arr):
    """核心算法：Bootstrap 95%置信区间、截尾均值、分位数"""
    if not arr or len(arr) == 0: 
        return 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0
    
    arr = np.array(arr)
    n = len(arr)
    mean_val = np.mean(arr)
    std_dev = np.std(arr, ddof=1) if n > 1 else 0.0
    
    # Bootstrap 重采样
    bootstrap_means = [np.mean(np.random.choice(arr, size=n, replace=True)) for _ in range(1000)]
    ci_lower = np.percentile(bootstrap_means, 2.5)
    ci_upper = np.percentile(bootstrap_means, 97.5)
    
    trimmed_mean = stats.trim_mean(arr, 0.1) if len(arr) >= 10 else mean_val
    
    p5 = np.percentile(arr, 5)
    p95 = np.percentile(arr, 95)
    
    return float(mean_val), float(std_dev), float(ci_lower), float(ci_upper), float(trimmed_mean), float(p5), float(p95)

def main():
    with open("test_cases.json", "r", encoding="utf-8") as f:
        test_cases = json.load(f)

    dimensions = get_dimensions()
    report_lines = ["# 🤖 Agent 版本对比与发布决策报告\n"]
    report_lines.append(f"> 生成时间：{datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
    report_lines.append(f"> 评测维度：{', '.join(dimensions)}\n")

    agent_v7 = MyTerminalAgent()
    agent_v8 = MyTerminalAgentV2()

    try:
        conn = get_db_connection()
    except Exception as e:
        print(f"❌ 数据库连接失败: {e}")
        return

    try:
        with conn.cursor() as cursor:
            run_id_v7 = create_eval_run(cursor, "sut_agent_v7", "compare_mode", len(test_cases))
            run_id_v8 = create_eval_run(cursor, "sut_agent_v8", "compare_mode", len(test_cases))
            conn.commit()

            summary_v7 = {d: [] for d in dimensions}
            summary_v8 = {d: [] for d in dimensions}
            diff_summary = {d: [] for d in dimensions}
            summary_v7["ttft"], summary_v8["ttft"] = [], []

            for case in test_cases:
                case_id = case["id"]
                query = case["query"]

                print(f"\n" + "="*80)
                print(f"题 #{case_id} 用户: \"{query}\"")
                print("="*80)

                res_old = agent_v7.run(query)
                res_new = agent_v8.run(query)
                ans_old = res_old.get("answer", "")
                ans_new = res_new.get("answer", "")

                judge_old_text, _ = evaluate_multi_dimension(query, ans_old)
                judge_new_text, _ = evaluate_multi_dimension(query, ans_new)
                data_old = clean_json(judge_old_text)
                data_new = clean_json(judge_new_text)

                detail_sql = "INSERT INTO eval_case_details (run_id, case_id, query_text, final_answer, is_passed, trace_id) VALUES (%s, %s, %s, %s, %s, %s)"
                cursor.execute(detail_sql, (run_id_v7, case_id, query, ans_old, 1, None))
                cursor.execute(detail_sql, (run_id_v8, case_id, query, ans_new, 1, None))

                print(f"{'维度':<22} {'旧版v7':<8} {'新版v8':<8} {'差值':<8} 归因分析（新版）")
                print("-" * 80)
                
                metric_sql = "INSERT INTO eval_metrics (run_id, case_id, metric_name, metric_value, metric_type) VALUES (%s, %s, %s, %s, %s)"
                
                for dim in dimensions:
                    # 这里拿到的是 1-10 分的原始分
                    score_old = data_old.get(dim, {}).get("score", 0)
                    score_new = data_new.get(dim, {}).get("score", 0)
                    reason_new = data_new.get(dim, {}).get("reason", "")
                    
                    # 强制归一化：转为 0~1 尺度再相减，完美匹配业务看板
                    norm_old = score_old / 10.0
                    norm_new = score_new / 10.0
                    diff = norm_new - norm_old
                    diff_str = f"{diff:+.2f}" if diff != 0 else "0.00"

                    # 收集汇总数据
                    summary_v7[dim].append(score_old) # 绝对分依然存原始分
                    summary_v8[dim].append(score_new)
                    diff_summary[dim].append(diff)    # 差值集合存归一化后的，方便算置信区间
                    
                    # 入库：原始分存 score_old，差值存归一化 diff
                    cursor.execute(metric_sql, (run_id_v7, case_id, dim, float(score_old), "raw"))
                    cursor.execute(metric_sql, (run_id_v8, case_id, dim, float(score_new), "raw"))
                    cursor.execute(metric_sql, (run_id_v8, case_id, f"diff_{dim}", float(diff), "diff"))

                    print(f"{dim:<22} {score_old:<8} {score_new:<8} {diff_str:<8} {reason_new}")

                for run_id, res in [(run_id_v7, res_old), (run_id_v8, res_new)]:
                    cursor.execute(metric_sql, (run_id, case_id, "ttft", float(res.get("ttft", 0)), "raw"))
                summary_v7["ttft"].append(res_old.get("ttft", 0))
                summary_v8["ttft"].append(res_new.get("ttft", 0))

            # ==========================================
            # 核心：全局统计、Bootstrap 与发布决策
            # ==========================================
            stat_sql = """
                INSERT INTO eval_summary_stats 
                (run_id, metric_name, mean_val, std_dev, ci_95_lower, ci_95_upper, trimmed_mean, p5_val, p95_val)
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)
            """

            print("\n" + "="*80)
            print("📊 多维差异 (Delta) 95% 置信区间与发布决策分析")
            print("="*80)
            print(f"{'维度':<22} {'旧版均分':<10} {'新版均分':<10} {'95%置信区间':<25} {'判断结论'}")
            print("-" * 80)

            report_lines.append("## 📈 全量测试集统计与发布决策\n")
            report_lines.append("| 维度 | 旧版均分 | 新版均分 | Delta 置信区间 | 判断结论 |")
            report_lines.append("| :--- | :---: | :---: | :---: | :--- |")

            weighted_delta_total = 0.0

            for dim in dimensions:
                # 绝对分统计
                m7, s7, l7, u7, tm7, p5_7, p95_7 = calc_stats(summary_v7[dim])
                m8, s8, l8, u8, tm8, p5_8, p95_8 = calc_stats(summary_v8[dim])
                cursor.execute(stat_sql, (run_id_v7, dim, m7, s7, l7, u7, tm7, p5_7, p95_7))
                cursor.execute(stat_sql, (run_id_v8, dim, m8, s8, l8, u8, tm8, p5_8, p95_8))

                # Delta 统计（已归一化）
                md, sd, ld, ud, tmd, p5_d, p95_d = calc_stats(diff_summary[dim])
                cursor.execute(stat_sql, (run_id_v8, f"diff_{dim}", md, sd, ld, ud, tmd, p5_d, p95_d))

                # 判断逻辑
                interval_str = f"[{ld:+.2f}, {ud:+.2f}]"
                if ld > 0:
                    judge = "✅ 全在零右侧，新版更好"
                elif ud < 0:
                    judge = "❌ 全在零左侧，新版更差"
                else:
                    judge = "⚪ 跨零，无显著差异"

                # 加权贡献计算
                weight = SCORE_WEIGHTS.get(dim, 0)
                contribution = md * weight
                weighted_delta_total += contribution

                print(f"{dim:<22} {m7:<10.1f} {m8:<10.1f} {interval_str:<25} {judge}")
                report_lines.append(f"| {dim} | {m7:.1f} | {m8:.1f} | {interval_str} | {judge} |")

            cursor.execute(stat_sql, (run_id_v7, "ttft") + calc_stats(summary_v7["ttft"]))
            cursor.execute(stat_sql, (run_id_v8, "ttft") + calc_stats(summary_v8["ttft"]))

            # ==========================================
            # 最终发布决策
            # ==========================================
            print("-" * 80)
            print(f"🔥 新版整体加权总 Delta: {weighted_delta_total:+.3f}")
            
            if weighted_delta_total > 0:
                decision_text = f"✅ 新版整体加权后是正收益（{weighted_delta_total:+.3f}），可以考虑发布。"
            else:
                decision_text = f"❌ 新版整体加权后为负收益（{weighted_delta_total:+.3f}），建议暂缓发布。"
            
            print(decision_text)
            print("=" * 80 + "\n")
            report_lines.append(f"\n### 🏁 综合决策\n**{decision_text}**\n")

            conn.commit()
            print(f"✅ 所有对比指标、归一化 Delta、置信区间已成功入库！")

    except Exception as e:
        conn.rollback()
        print(f"\n❌ 数据库操作失败，已回滚: {e}")
    finally:
        conn.close()

    with open("compare_report.md", "w", encoding="utf-8") as f:
        f.write("\n".join(report_lines))
    print(f"✅ 完整对比报告已生成: compare_report.md")

if __name__ == "__main__":
    main()
