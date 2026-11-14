# compare_runner.py
import json
import time
import datetime
import pymysql
import numpy as np
from scipy import stats
from tabulate import tabulate
from evaluator import evaluate_multi_dimension, get_dimensions, SCORE_WEIGHTS
from config import DB_HOST, DB_USER, DB_PASS, DB_NAME

# 导入你的两个 Agent (请确保路径和类名与你实际一致)
from sut_agent.my_agent import MyTerminalAgent
from sut_agent_1.my_agent import MyTerminalAgent as MyTerminalAgentV2 

# ==========================================
# 🔥 在这里设置每个用例的重复运行次数
# ==========================================
REPEAT_COUNT = 1

def clean_json(text):
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

def create_eval_run(cursor, version_name, scenario_name, repeat_count):
    sql = "INSERT INTO eval_runs (version_name, scenario_type, repeat_count, model_name, judge_model) VALUES (%s, %s, %s, %s, %s)"
    cursor.execute(sql, (version_name, scenario_name, repeat_count, "qwen2.5:3b", "deepseek-chat"))
    return cursor.lastrowid

def calc_stats(arr):
    """计算均值、标准差、Bootstrap置信区间、P-value等"""
    if not arr or len(arr) == 0: 
        return 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 1.0
    
    arr = np.array(arr)
    n = len(arr)
    mean_val = np.mean(arr)
    std_dev = np.std(arr, ddof=1) if n > 1 else 0.0
    
    # 1. Bootstrap 重采样 95% CI
    if n > 0:
        bootstrap_means = [np.mean(np.random.choice(arr, size=n, replace=True)) for _ in range(1000)]
        ci_lower = np.percentile(bootstrap_means, 2.5)
        ci_upper = np.percentile(bootstrap_means, 97.5)
    else:
        ci_lower, ci_upper = mean_val, mean_val
        
    # 2. 截尾均值
    trimmed_mean = stats.trim_mean(arr, 0.1) if n >= 10 else mean_val
    
    # 3. 分位数
    p5 = np.percentile(arr, 5)
    p95 = np.percentile(arr, 95)
    
    # 4. T检验 P-value (假设均值=0)
    if n > 1 and std_dev > 0:
        t_stat, p_val = stats.ttest_1samp(arr, 0)
        p_value = float(p_val)
    else:
        p_value = 1.0

    return float(mean_val), float(std_dev), float(ci_lower), float(ci_upper), float(trimmed_mean), float(p5), float(p95), p_value

def main():
    with open("test_cases.json", "r", encoding="utf-8") as f:
        test_cases = json.load(f)

    dimensions = get_dimensions()
    report_lines = ["# 🤖 Agent 版本对比与发布决策报告\n"]
    report_lines.append(f"> 生成时间：{datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
    report_lines.append(f"> 评测维度：{', '.join(dimensions)}\n")
    report_lines.append(f"> 累计采样：{len(test_cases)} 条用例 × {REPEAT_COUNT} 次重复 = {len(test_cases) * REPEAT_COUNT} 次样本\n")
    
    agent_v7 = MyTerminalAgent()
    agent_v8 = MyTerminalAgentV2()

    conn = get_db_connection()

    try:
        with conn.cursor() as cursor:
            run_id_v7 = create_eval_run(cursor, "sut_agent_v7", "compare_mode", len(test_cases) * REPEAT_COUNT)
            run_id_v8 = create_eval_run(cursor, "sut_agent_v8", "compare_mode", len(test_cases) * REPEAT_COUNT)
            conn.commit()

            summary_v7 = {d: [] for d in dimensions}
            summary_v8 = {d: [] for d in dimensions}
            diff_summary = {d: [] for d in dimensions}

            for case in test_cases:
                case_id = case["id"]
                query = case["query"]

                print(f"\n" + "="*80)
                print(f"题 #{case_id} 用户: \"{query}\"")
                print("="*80)

                for r in range(REPEAT_COUNT):
                    if REPEAT_COUNT > 1:
                        print(f"  👉 正在执行第 {r+1}/{REPEAT_COUNT} 次采样...")

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

                    if r == 0:
                        print(f"\n{'维度':<22} {'旧版v7':<8} {'新版v8':<8} {'差值':<8} 归因分析（新版）")
                        print("-" * 80)
                    
                    metric_sql = "INSERT INTO eval_metrics (run_id, case_id, metric_name, metric_value, metric_type) VALUES (%s, %s, %s, %s, %s)"
                    
                    for dim in dimensions:
                        score_old = data_old.get(dim, {}).get("score", 0)
                        score_new = data_new.get(dim, {}).get("score", 0)
                        reason_new = data_new.get(dim, {}).get("reason", "")
                        
                        norm_old = score_old / 10.0
                        norm_new = score_new / 10.0
                        diff = norm_new - norm_old
                        diff_str = f"{diff:+.2f}" if diff != 0 else "0.00"

                        summary_v7[dim].append(score_old)
                        summary_v8[dim].append(score_new)
                        diff_summary[dim].append(diff)
                        
                        cursor.execute(metric_sql, (run_id_v7, case_id, dim, float(score_old), "raw"))
                        cursor.execute(metric_sql, (run_id_v8, case_id, dim, float(score_new), "raw"))
                        cursor.execute(metric_sql, (run_id_v8, case_id, f"diff_{dim}", float(diff), "diff"))

                        if r == 0:
                            print(f"{dim:<22} {score_old:<8} {score_new:<8} {diff_str:<8} {reason_new}")

            # ==========================================
            # 统计分析与 P-value 判定
            # ==========================================
            stat_sql = """
                INSERT INTO eval_summary_stats 
                (run_id, metric_name, mean_val, std_dev, ci_95_lower, ci_95_upper, trimmed_mean, p5_val, p95_val, p_value)
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
            """

            report_lines.append("## 📈 全量测试集统计与发布决策\n")
            report_lines.append("| 维度 | Delta 置信区间 | P-value | 结论 |")
            report_lines.append("| :--- | :---: | :---: | :--- |")

            weighted_delta_total = 0.0
            terminal_table_data = []

            for dim in dimensions:
                m7, s7, l7, u7, tm7, p5_7, p95_7, _ = calc_stats(summary_v7[dim])
                cursor.execute(stat_sql, (run_id_v7, dim, m7, s7, l7, u7, tm7, p5_7, p95_7, None))
                
                m8, s8, l8, u8, tm8, p5_8, p95_8, _ = calc_stats(summary_v8[dim])
                cursor.execute(stat_sql, (run_id_v8, dim, m8, s8, l8, u8, tm8, p5_8, p95_8, None))

                md, sd, ld, ud, tmd, p5_d, p95_d, p_val = calc_stats(diff_summary[dim])
                cursor.execute(stat_sql, (run_id_v8, f"diff_{dim}", md, sd, ld, ud, tmd, p5_d, p95_d, p_val))

                interval_str = f"[{ld:+.2f}, {ud:+.2f}]"
                
                if p_val < 0.05:
                    if md > 0:
                        judge = "✅ 显著提升 (P<0.05)"
                    elif md < 0:
                        judge = "❌ 显著下降 (P<0.05)"
                    else:
                        judge = "⚪ 无显著差异"
                else:
                    judge = "⚪ 跨零，无显著差异"

                weight = SCORE_WEIGHTS.get(dim, 0)
                contribution = md * weight
                weighted_delta_total += contribution

                report_lines.append(f"| {dim} | {interval_str} | {p_val:.4f} | {judge} |")
                
                terminal_table_data.append([
                    dim, f"{m7:.1f}", f"{m8:.1f}", interval_str, f"{p_val:.4f}", judge
                ])

            if weighted_delta_total > 0:
                decision_text = f"✅ 整体正收益，推荐发布。"
                decision_icon = "✅"
            else:
                decision_text = f"❌ 整体负收益，暂缓发布。"
                decision_icon = "❌"
            
            report_lines.append(f"\n### 🏁 综合决策\n**{decision_text}**\n")

            conn.commit()
            print(f"\n✅ 所有对比指标、置信区间、P-value 已成功入库！")

    except Exception as e:
        conn.rollback()
        print(f"\n❌ 数据库操作失败，已回滚: {e}")
        return 
    finally:
        conn.close()

    with open("compare_report.md", "w", encoding="utf-8") as f:
        f.write("\n".join(report_lines))
    
    # ==========================================
    # 🔥 终极渲染：终端 P-value 判决书！
    # ==========================================
    total_sampled = len(test_cases) * REPEAT_COUNT
    print("\n" + "="*105)
    print(f"⚖️ 多维差异 (Delta) 统计学检验看板 | 用例总数: {len(test_cases)} 条 | REPEAT_COUNT: {REPEAT_COUNT} | 累计采样: {total_sampled} 次")
    print("="*105)
    
    headers = ["维度", "旧版均分", "新版均分", "95% 置信区间", "P-value", "判断结论"]
    print(tabulate(terminal_table_data, headers=headers, tablefmt="grid", maxcolwidths=[28, None, None, 22, 12, 25]))
    
    print("="*105)
    
    # ==========================================
    # 🚀 终极渲染：加权收益审计明细表 (商业闭环版)
    # ==========================================
    print("\n📊 业务加权收益审计明细 (结合统计学与业务权重，为什么得出这个总 Delta？)")
    
    audit_headers = ["维度", "权重系数", "旧版分", "新版分", "归一化Delta", "95%置信区间", "显著性(P)", "加权贡献"]
    audit_data = []
    
    for dim in dimensions:
        avg_v7 = np.mean(summary_v7[dim]) if summary_v7[dim] else 0.0
        avg_v8 = np.mean(summary_v8[dim]) if summary_v8[dim] else 0.0
        raw_diff = avg_v8 - avg_v7
        norm_delta = raw_diff / 10.0
        
        weight = SCORE_WEIGHTS.get(dim, 0)
        contribution = norm_delta * weight
        
        md, sd, ld, ud, _, _, _, p_val = calc_stats(diff_summary[dim])
        interval_str = f"[{ld:+.2f}, {ud:+.2f}]"
        
        if p_val < 0.05:
            sig_str = "显著"
        else:
            sig_str = "不显著"
            
        audit_data.append([
            dim, 
            f"{weight*100:.0f}%", 
            f"{avg_v7:.1f}", 
            f"{avg_v8:.1f}", 
            f"{norm_delta:+.3f}", 
            interval_str,
            f"{p_val:.4f} ({sig_str})",
            f"{contribution:+.3f}"
        ])
    
    print(tabulate(audit_data, headers=audit_headers, tablefmt="grid", maxcolwidths=[24, None, None, None, None, 18, 16, None]))
    
    print("-" * 105)
    print(f"🔥 新版整体加权总 Delta: {weighted_delta_total:+.3f}")
    print(f"{decision_icon} 综合决策建议：{decision_text}")
    print("-" * 105)
    
    print("💡 [判决书阅读指南] 帮助业务方快速看懂：")
    print("   - 置信区间 : 如果区间 [下限, 上限] 全部跨过 0，说明波动太大，不能判断真的变好或变差。")
    print("   - P-value  : 如果 < 0.05，说明统计学上差异显著（不是模型抽风），判定生效。")
    print("   - 整体 Delta: 结合配置的业务权重，算出新版到底赚了还是亏了。")
    print("="*105 + "\n")

    print(f"✅ 完整对比报告已生成: compare_report.md")

if __name__ == "__main__":
    main()
