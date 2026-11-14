<div align="center">

# 🤖 Agent Eval Studio
### 企业级大模型 (LLM) Agent 自动化评测与 A/B 发布决策平台

<p align="center">
  <b>告别“凭感觉”调 Prompt，用统计学置信区间与加权收益，给老板一个无法反驳的发版结论！</b>
</p>

[![Python](https://img.shields.io/badge/Python-3.10%2B-blue.svg?style=flat-square)](https://www.python.org/)
[![Langchain](https://img.shields.io/badge/LangChain-1.2-green.svg?style=flat-square)](https://python.langchain.com/)
[![MySQL](https://img.shields.io/badge/MySQL-8.0-orange.svg?style=flat-square)](https://www.mysql.com/)
[![Langfuse](https://img.shields.io/badge/Langfuse-Supported-blueviolet.svg?style=flat-square)](https://langfuse.com/)
[![Docker](https://img.shields.io/badge/Docker-Supported-blue.svg?style=flat-square)](https://www.docker.com/)
[![License](https://img.shields.io/badge/License-MIT-yellow.svg?style=flat-square)](https://opensource.org/licenses/MIT)

<br />

*( 💡 建议：在此处拖拽上传一张你的 `web_app.py` 界面截图，或 `compare_report.md` 的精美截图，展示给访客 )*

</div>

---

## 💡 为什么需要 Agent Eval Studio？

在 AI Agent 落地的真实场景中，Prompt 的迭代往往充满盲目性：
* ❌ **主观偏差**：新版本更友好了，但变得啰嗦，到底算好还是坏？
* ❌ **随机波动**：测试了几道题分数下降了，是真的退步了，还是模型随机性导致的？
* ❌ **缺乏业务视角**：客服 Agent 和 金融 Agent 的考核标准完全不同，如何量化？
* ❌ **无法闭环**：跑完测试只有一堆冰冷的 JSON 代码，无法向老板解释“到底能不能发布”。

**Agent Eval Studio** 专为解决这些问题而生。本项目基于 **LangChain 1.2** 与 **DeepSeek** 裁判模型构建，抛弃了粗暴的“通过/不通过”判定，引入了 **多维加权权衡** 与 **Bootstrap 置信区间**，为你提供最严谨的 A/B 实验发布决策。

---

## ✨ 核心特性 (Features)

- 🧠 **多维度动态评估**：内置通用质量、Agent 专属、金融业务 3 套评估维度配置。支持准确性、安全性、工具调用、RAG 忠实度等 10+ 项指标。
- 📊 **Bootstrap 统计学检验**：拒绝简单平均。底层集成 1000 次重采样算法，自动计算新旧版本差值（Delta）的 **95% 置信区间**。
- ⚖️ **加权总收益决策**：基于业务视角的权重配置，自动计算整体发布收益，秒级输出是否应该发布的终极结论。
- 🔍 **全链路可观测性**：深度集成 [Langfuse](https://langfuse.com/)，每一次工具调用、Token 消耗、首字延迟 (TTFT) 尽在掌握。
- 💾 **高维数据垂直存储**：开箱即用的 MySQL 表结构设计，支持海量 Metric 的极速写入与多维聚合查询。
- 📊 **可视化 Web 看板**：内置基于 Streamlit 的极简看板，直观展示各维度胜负与决策建议。

---

## 🏗️ 系统架构与目录设计

```text
Agent-Eval-Pipeline/
├── configs/                  # 🗂️ 评测维度配置档
│   ├── general_quality.yaml  #    - 第一类：通用维度 (5维)
│   ├── agent_specialty.yaml  #    - 第二类：Agent专属 (8维)
│   └── business_finance.yaml #    - 第三类：业务专属 (10维)
├── sut_agent/                # 🤖 旧版被测 Agent (v7)
├── sut_agent_1/              # 🤖 新版被测 Agent (v8)
├── evaluator.py              # ⚖️ 裁判打分引擎 (负责调用大模型评测及加权计算)
├── monitor.py                # 📡 链路监控 (将单次测试上报至 Langfuse)
├── compare_runner.py         # 🚀 核心对比执行器 (包含 Bootstrap 算法与入库逻辑)
├── test_runner.py            # 🏃 单版本基准测试执行器
├── web_app.py                # 📊 Web 数据看板 (Streamlit)
├── old.sql                   # 💾 数据库建表语句
├── Dockerfile                # 🐳 Docker 容器配置
├── docker-compose.yml        # 🐳 一键启动配置
└── README.md                 # 📖 项目说明
🚀 快速开始 (Quick Start)
1. 本地安装
bash
# 克隆仓库并切换至开发分支
git clone -b ai_model_v6 https://github.com/daguideng/Agent-Eval-Pipeline.git
cd Agent-Eval-Pipeline

# 安装所需依赖
pip install -r requirements.txt
2. 配置环境变量
复制 .env.example 为 .env，并填入你的 API Key：

env
LANGFUSE_PUBLIC_KEY=your_public_key
LANGFUSE_SECRET_KEY=your_secret_key
DEEPSEEK_API_KEY=your_deepseek_api_key
# DB_HOST, DB_USER 等配置在 config.py 中修改
3. Docker 一键部署 (强烈推荐)
无需本地配环境，直接一键拉起 MySQL 和 Web 界面：

bash
docker-compose up -d --build
访问 Web 看板：http://localhost:8501

数据库已自动完成建表（端口 3306）

🛠️ 使用指南 (Usage)
本系统既支持单机跑测，也支持双版本 A/B 对比。通过以下命令组合，可满足从开发自测到发版决策的全流程需求。

一、 三种单机运行方法（单版本基准测试）
如果你只想测试单个 Agent 的输出质量，请使用 test_runner.py，跑完的数据会自动打入 Langfuse 监控面板。

运行模式	运行命令	特点说明
通用质量 (5维)	python test_runner.py	默认加载。包含准确性、相关性、安全性等基础测试。
Agent 专属 (8维)	EVAL_PROFILE=agent_specialty python test_runner.py	增加了工具调用准确率、上下文一致性等 Agent 特有维度。
金融业务 (10维)	EVAL_PROFILE=business_finance python test_runner.py	增加了 RAG 忠实度、语气与情感等严苛金融维度。
二、 三种对比方法（A/B 实验发布决策）
如果你有 sut_agent (旧版 v7) 和 sut_agent_1 (新版 v8)，想判断新版能否上线，请使用 compare_runner.py。同样支持三种维度的对比：

对比模式	运行命令	特点说明
通用 A/B 对比	python compare_runner.py	默认加载通用 5 维，输出基础 A/B 差值统计。
Agent A/B 对比	EVAL_PROFILE=agent_specialty python compare_runner.py	重点对比新旧版在“工具调用”和“上下文记忆”上的差异。
金融 A/B 对比	EVAL_PROFILE=business_finance python compare_runner.py	重点对比新旧版在“RAG 幻觉”与“语气态度”上的差异。
💡 对比结果去哪了？
以上所有 A/B 对比命令运行结束后，系统会自动计算 Bootstrap 置信区间，在根目录生成 compare_report.md 详细分析报告，并将所有统计指标全量写入 MySQL 数据库（可通过 web_app.py 查看数据大盘）。

📈 决策报告展示
系统运行后，终端及 Markdown 报告中会生成如下分析：

维度 (Dimension)	旧版均分 (v7)	新版均分 (v8)	Delta 95%置信区间	统计学判断结论
TaskCompletion	7.5	7.8	[+0.15, +0.28]	✅ 全在零右侧，新版确实更好
ToneAppropriateness	8.0	8.5	[+0.18, +0.31]	✅ 全在零右侧，新版确实更好
InstructionFollowing	8.5	8.4	[-0.03, +0.05]	⚪ 跨零，无显著差异 (随机波动)
Conciseness	8.2	7.1	[-0.22, -0.09]	❌ 全在零左侧，新版确实更差
🔥 新版整体加权总 Delta: +0.154
🏁 综合决策建议：新版整体加权后是正收益，可以考虑发布。但需注意 Conciseness 维度出现退步，建议在下次迭代中优化 Prompt 啰嗦度。

💼 企业级私有化与商业合作 (Commercial)
本开源仓库提供了核心的评测算法、Bootstrap 统计逻辑与基础命令行工具。

如果您是企业团队，需要以下高级能力，欢迎联系作者获取商业授权、定制开发与私有化部署服务：

📊 高级可视化 Web 数据看板：多团队管理、自动生成 PDF 汇报文档、拖拽式配置维度权重。

🏢 高可用私有化架构：提供完整的包含 Langfuse（ClickHouse/Redis/MinIO）的企业级高可用全家桶部署方案。

🛠️ 定制化开发：对接贵司内部 Agent 接口、定制特定行业（金融/医疗）的 Judge Prompt 体系。

📬 联系方式

微信：wxid_2f5h1j7u0dm811 (添加请备注：GitHub 评测)

邮箱：dengdagui8@qq.com

<div align="center"> <b>如果这个项目对你有帮助，请给个 ⭐️ Star 支持一下！</b> </div>
📄 License
This project is licensed under the MIT License.
