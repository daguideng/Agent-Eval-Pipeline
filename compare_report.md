# 🤖 Agent 版本对比与发布决策报告

> 生成时间：2026-11-14 13:52:12

> 评测维度：accuracy, relevance, safety, completeness, instruction_following, tool_call, context_consistency, recovery_rate, rag_faithfulness, tone_sentiment

## 📈 全量测试集统计与发布决策

| 维度 | 旧版均分 | 新版均分 | Delta 置信区间 | 判断结论 |
| :--- | :---: | :---: | :---: | :--- |
| accuracy | 9.0 | 7.0 | [-0.48, -0.02] | ❌ 全在零左侧，新版更差 |
| relevance | 9.2 | 7.2 | [-0.60, +0.00] | ⚪ 跨零，无显著差异 |
| safety | 9.2 | 8.2 | [-0.20, +0.00] | ⚪ 跨零，无显著差异 |
| completeness | 7.5 | 5.8 | [-0.33, -0.10] | ❌ 全在零左侧，新版更差 |
| instruction_following | 8.5 | 7.0 | [-0.38, +0.00] | ⚪ 跨零，无显著差异 |
| tool_call | 8.8 | 5.8 | [-0.55, -0.05] | ❌ 全在零左侧，新版更差 |
| context_consistency | 9.2 | 7.5 | [-0.52, +0.00] | ⚪ 跨零，无显著差异 |
| recovery_rate | 7.5 | 6.5 | [-0.22, +0.00] | ⚪ 跨零，无显著差异 |
| rag_faithfulness | 9.0 | 6.0 | [-0.60, +0.00] | ⚪ 跨零，无显著差异 |
| tone_sentiment | 8.8 | 8.0 | [-0.15, +0.00] | ⚪ 跨零，无显著差异 |

### 🏁 综合决策
**❌ 新版整体加权后为负收益（-0.185），建议暂缓发布。**
