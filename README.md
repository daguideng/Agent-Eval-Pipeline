markdown
<div align="center">

# 🤖 Agent Eval Studio
### 企业级大模型 (LLM) Agent 自动化评测与 A/B 发布决策平台

<p align="center">
  <b>告别“凭感觉”调 Prompt，用统计学和加权收益，给老板一个无法反驳的发版结论！</b>
</p>

[![Python](https://img.shields.io/badge/Python-3.10%2B-blue.svg?style=flat-square)](https://www.python.org/)
[![Langchain](https://img.shields.io/badge/LangChain-v0.2-green.svg?style=flat-square)](https://python.langchain.com/)
[![Docker](https://img.shields.io/badge/Docker-Supported-blue.svg?style=flat-square)](https://www.docker.com/)
[![License](https://img.shields.io/badge/License-MIT-yellow.svg?style=flat-square)](https://opensource.org/licenses/MIT)
[![PRs Welcome](https://img.shields.io/badge/PRs-welcome-brightgreen.svg?style=flat-square)]()

<br />

*( 💡 建议：在此处拖拽上传一张你的 `compare_report.md` 精美截图，展示给访客 )*

</div>

---

## 💡 为什么需要 Agent Eval Studio？

在大模型 Agent 的迭代过程中，你是否经常遇到以下痛点：
* ❌ **主观偏差**：新版本更友好了，但变得啰嗦，到底算好还是坏？
* ❌ **随机波动**：测试了几道题分数下降了，是真的退步了，还是模型随机性导致的？
* ❌ **缺乏业务视角**：客服 Agent 和 金融 Agent 的考核标准完全不同，如何量化？
* ❌ **无法闭环**：跑完测试只有一堆 JSON，无法向老板解释“到底能不能发布”。

**Agent Eval Studio** 专为解决这些问题而生。我们抛弃了粗暴的“通过/不通过”判定，引入了**多维加权权衡**与**Bootstrap 置信区间**，为你提供最严谨的 A/B 实验发布决策。

---

## ✨ 核心特性 (Features)

- 🧠 **多维度动态评估 (Multi-Dimension)**：内置通用、Agent 专属、金融业务 3 套评估维度配置。支持准确性、安全性、工具调用、RAG 忠实度等 10+ 项指标。
- 📊 **Bootstrap 统计学检验**：拒绝简单平均。底层集成 1000 次重采样算法，自动计算新旧版本差值（Delta）的 **95% 置信区间**。
- ⚖️ **加权总收益决策 (Weighted Delta)**：基于业务视角的权重配置，自动计算整体发布收益，秒级输出是否应该发布的终极结论。
- 🔍 **全链路可观测性**：深度集成 [Langfuse](https://langfuse.com/)，每一次工具调用、Token 消耗、首字延迟 (TTFT) 尽在掌握。
- 💾 **高维数据垂直存储**：开箱即用的 MySQL 表结构设计，支持海量 Metric 的极速写入与多维聚合查询。
- 🐳 **一键私有化部署**：提供完整的 Docker Compose 方案，数据完全留存内网，满足金融级合规要求。

---

## 🏗️ 系统架构

```text
                               +-------------------+
                               |  Web UI Dashboard |
                               | (Streamlit/Vue)   |
                               +---------+---------+
                                         |
+-------------+    +-------------+    +--v--------------+    +-------------------+
| sut_agent   |    | sut_agent_1 |    |                  |    |  LLM Judge (裁判) |
| (旧版 v7)   +--->+ (新版 v8)   +--->+  Compare Runner  +--->+  (DeepSeek/GPT-4) |
+-------------+    +-------------+    |                  |    +-------------------+
                                      +--+------------+--+
                                         |            |
                           +-------------v--+      +--v--------------+
                           |  Langfuse      |      |  MySQL Database |
                           |  (Trace链路)   |      |  (垂直指标存储) |
                           +----------------+      +-----------------+
🚀 快速开始 (Quick Start)
1. 本地安装
bash
# 克隆仓库
git clone https://github.com/yourname/Agent-Eval-Studio.git
cd Agent-Eval-Studio

# 安装依赖
pip install -r requirements.txt
2. 配置环境变量
复制 .env.example 为 .env，并填入你的 API Key：

env
LANGFUSE_PUBLIC_KEY=your_public_key
LANGFUSE_SECRET_KEY=your_secret_key
DEEPSEEK_API_KEY=your_deepseek_api_key
# ... 数据库配置等
3. Docker 一键部署 (推荐)
bash
docker-compose up -d --build
访问 Web 界面：http://localhost:8501

访问 Langfuse 链路追踪：http://localhost:3000

4. 运行 A/B 对比测试
bash
# 运行新旧版本对比，并自动写入 MySQL 数据库
python compare_runner.py
运行结束后，终端会直接打印出带有统计学置信区间的决策报告，并生成 compare_report.md。

📈 决策报告展示
系统运行后，不仅会在终端输出结果，还会生成一份高可读性的 Markdown 报表：

维度	旧版均分	新版均分	Delta 95%置信区间	判断结论
TaskCompletion	7.5	7.8	[+0.15, +0.28]	✅ 全在零右侧，新版更好
ToneAppropriateness	8.0	8.5	[+0.18, +0.31]	✅ 全在零右侧，新版更好
InstructionFollowing	8.5	8.4	[-0.03, +0.05]	⚪ 跨零，无显著差异
Conciseness	8.2	7.1	[-0.22, -0.09]	❌ 全在零左侧，新版更差
🔥 新版整体加权总 Delta: +0.154
🏁 综合决策建议：新版整体加权后是正收益，可以考虑发布。但需注意 Conciseness 维度出现退步，建议在下次迭代中优化 Prompt 啰嗦度。

💼 企业级私有化与商业合作 (Commercial)
本开源仓库提供了核心的评测算法、Bootstrap 统计逻辑与基础命令行工具。

如果您是企业团队，需要以下高级能力，欢迎联系作者获取商业授权、定制开发与私有化部署服务：

📊 可视化 Web 数据看板：多团队管理、自动生成 PDF 汇报文档、拖拽式配置维度权重。

🏢 高可用私有化架构：提供完整的包含 Langfuse（ClickHouse/Redis/MinIO）的企业级高可用全家桶部署方案。

🛠️ 定制化开发：对接贵司内部 Agent 接口、定制特定行业（金融/医疗）的 Judge Prompt 体系。

📬 联系方式

微信：your_wechat_id (备注：GitHub 评测)

邮箱：your_email@example.com

🤝 贡献与致谢
欢迎提交 Issue 或 Pull Request！
如果这个项目对你有帮助，请给个 ⭐️ Star 支持一下！

📄 License
This project is licensed under the MIT License - see the LICENSE file for details.
