# web_app.py
import streamlit as st
import pandas as pd
import numpy as np

st.set_page_config(page_title="Agent Eval Studio", page_icon="🤖", layout="wide")

st.title("🤖 Agent Eval Studio")
st.markdown("### 企业级大模型 (LLM) Agent 自动化评测与 A/B 发布决策平台")

st.divider()

col1, col2, col3 = st.columns(3)
col1.metric("当前评测批次", "Run #24", "Compare Mode")
col2.metric("加权总 Delta", "+0.154", "正收益 ✅")
col3.metric("发版建议", "推荐发布", "需关注 Conciseness 退步")

st.markdown("---")
st.subheader("📊 多维差异 (Delta) 95% 置信区间与决策")

# 模拟展示你数据库里跑出来的数据 (实际开发中，这里可以用 pymysql 读取数据库)
data = {
    "维度": ["accuracy", "relevance", "safety", "completeness", "instruction_following"],
    "旧版均分": [8.2, 7.5, 9.9, 8.0, 8.5],
    "新版均分": [8.4, 7.8, 9.9, 8.5, 8.6],
    "Delta (归一化)": [0.02, 0.03, 0.00, 0.05, 0.01],
    "95% 置信区间": ["[+0.01, +0.03]", "[+0.01, +0.05]", "[-0.01, +0.01]", "[+0.02, +0.08]", "[-0.02, +0.04]"],
    "统计学判断": ["✅ 显著提升", "✅ 显著提升", "⚪ 跨零，无差异", "✅ 显著提升", "⚪ 跨零，无差异"]
}

df = pd.DataFrame(data)
st.dataframe(df, use_container_width=True)

st.info("💡 提示：开源版展示基础统计数据。如需读取真实 MySQL 数据并自动生成图表，请获取企业版。")
