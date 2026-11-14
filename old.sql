CREATE DATABASE IF NOT EXISTS ai_evaluator CHARACTER SET utf8mb4 COLLATE utf8mb4_0900_ai_ci;


use ai_evaluator;
-- ==========================================
-- 表 1：评测批次表 (记录每一次跑的宏观信息)
-- ==========================================
CREATE TABLE IF NOT EXISTS eval_runs (
    id INT AUTO_INCREMENT PRIMARY KEY,
    version_name VARCHAR(50) NOT NULL COMMENT '版本号，如 sut_agent_v1 / v2',
    scenario_type VARCHAR(20) NOT NULL COMMENT '场景类型: baseline(单次基准) / batch(分批分布) / trimmed(截尾置信)',
    repeat_count INT NOT NULL COMMENT '总采样次数 (如 100 或 1000)',
    model_name VARCHAR(50) COMMENT '被测模型 (如 qwen2.5:3b)',
    judge_model VARCHAR(50) COMMENT '裁判模型 (如 deepseek-chat)',
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP COMMENT '执行时间'
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='评测批次总表';

-- ==========================================
-- 表 2：用例执行原始明细表 (记录每一条用例、每一次采样的原始数据)
-- ==========================================
CREATE TABLE IF NOT EXISTS eval_case_details (
    id INT AUTO_INCREMENT PRIMARY KEY,
    run_id INT NOT NULL COMMENT '关联 eval_runs 的 id',
    case_id INT NOT NULL COMMENT '用例ID',
    query_text TEXT NOT NULL COMMENT '用户提问',
    final_answer TEXT COMMENT 'Agent最终回答',
    is_passed TINYINT(1) DEFAULT 0 COMMENT '是否通过规则/确定性校验 (1:通过, 0:拦截)',
    pass_rate DECIMAL(5,2) DEFAULT 0.00 COMMENT '该用例在当前批次的通过率',
    trace_id VARCHAR(255) COMMENT 'LangFuse Trace ID',
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (run_id) REFERENCES eval_runs(id) ON DELETE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='用例执行明细';

-- ==========================================
-- 表 3：指标垂直扩展表 (核心设计：把所有指标像流水账一样存进去)
-- 不管是准确率、TTFT、还是以后的什么多模态指标，全放这里
-- ==========================================
CREATE TABLE IF NOT EXISTS eval_metrics (
    id INT AUTO_INCREMENT PRIMARY KEY,
    run_id INT NOT NULL COMMENT '关联批次表',
    case_id INT NOT NULL COMMENT '关联具体哪个用例',
    metric_name VARCHAR(50) NOT NULL COMMENT '指标名称 (如: accuracy, ttft, faithfulness, std_dev)',
    metric_value DECIMAL(10,4) NOT NULL COMMENT '指标数值',
    metric_type VARCHAR(20) NOT NULL COMMENT '指标类型: raw(原始单次值) / average(均值) / variance(方差) / ci_bound(置信区间边界)',
    FOREIGN KEY (run_id) REFERENCES eval_runs(id) ON DELETE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='所有原始及聚合指标明细';

-- ==========================================
-- 表 4：全局聚合统计表 (存场景一、二、三的最终对比指标)
-- ==========================================
CREATE TABLE IF NOT EXISTS eval_summary_stats (
    id INT AUTO_INCREMENT PRIMARY KEY,
    run_id INT NOT NULL COMMENT '关联批次表',
    metric_name VARCHAR(50) NOT NULL COMMENT '指标名 (如: overall_ttft)',
    mean_val DECIMAL(10,4) COMMENT '平均值',
    std_dev DECIMAL(10,4) COMMENT '标准差',
    ci_95_lower DECIMAL(10,4) COMMENT '标准 95% 置信区间下限',
    ci_95_upper DECIMAL(10,4) COMMENT '标准 95% 置信区间上限',
    trimmed_mean DECIMAL(10,4) COMMENT '截尾均值 (场景三)',
    p5_val DECIMAL(10,4) COMMENT '5% 分位数 (场景三)',
    p95_val DECIMAL(10,4) COMMENT '95% 分位数 (场景三)',
    p_value DECIMAL(10,4) DEFAULT NULL COMMENT '显著性检验 P-value', -- 👈 新增这行
    FOREIGN KEY (run_id) REFERENCES eval_runs(id) ON DELETE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='全局聚合统计指标';
