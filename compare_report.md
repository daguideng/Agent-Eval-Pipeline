# 🤖 Agent 版本对比与发布决策报告

> 生成时间：2026-11-13 19:38:32

> 评测维度：accuracy, relevance, safety, completeness, instruction_following, tool_call, context_consistency, recovery_rate, rag_faithfulness, tone_sentiment

## 📈 全量测试集统计与发布决策

| 维度 | 旧版均分 | 新版均分 | Delta 置信区间 | 判断结论 |
| :--- | :---: | :---: | :---: | :--- |
| accuracy | 8.8 | 7.5 | [-0.30, +0.00] | ⚪ 跨零，无显著差异 |
| relevance | 9.0 | 8.0 | [-0.30, +0.00] | ⚪ 跨零，无显著差异 |
| safety | 9.0 | 8.8 | [-0.07, +0.00] | ⚪ 跨零，无显著差异 |
| completeness | 7.5 | 6.2 | [-0.25, -0.03] | ❌ 全在零左侧，新版更差 |
| instruction_following | 8.0 | 7.2 | [-0.17, +0.00] | ⚪ 跨零，无显著差异 |
| tool_call | 6.5 | 6.0 | [-0.15, +0.00] | ⚪ 跨零，无显著差异 |
| context_consistency | 9.0 | 8.2 | [-0.23, +0.00] | ⚪ 跨零，无显著差异 |
| recovery_rate | 7.5 | 6.5 | [-0.22, +0.00] | ⚪ 跨零，无显著差异 |
| rag_faithfulness | 7.0 | 6.0 | [-0.30, +0.00] | ⚪ 跨零，无显著差异 |
| tone_sentiment | 9.0 | 8.2 | [-0.15, +0.00] | ⚪ 跨零，无显著差异 |

### 🏁 综合决策
**❌ 新版整体加权后为负收益（-0.082），建议暂缓发布。**
