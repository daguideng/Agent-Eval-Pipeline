# web_app.py
import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go

st.set_page_config(page_title="Agent Eval Studio", page_icon="🤖", layout="wide")

st.title("🤖 Agent Eval Studio")
st.markdown("### 企业级大模型 (LLM) Agent 自动化评测与 A/B 发布决策平台")
st.divider()

# ================= 核心指标卡 =================
col1, col2, col3 = st.columns(3)
col1.metric("当前评测批次", "Run #24", "Compare Mode")
col2.metric("加权总 Delta", "+0.154", "正收益 ✅")
col3.metric("发版建议", "推荐发布", "需关注 Conciseness 退步")

st.divider()

# ================= 数据准备 =================
dimensions = ["accuracy", "relevance", "safety", "completeness", "instruction_following"]
v7_scores = [8.2, 7.5, 9.9, 8.0, 8.5]
v8_scores = [8.4, 7.8, 9.9, 8.5, 8.6]
deltas = [0.02, 0.03, 0.00, 0.05, 0.01]

# ================= 1. 雷达图 =================
st.subheader("📊 新旧版本维度能力雷达图")
st.caption("对比新旧版本在各个维度的绝对得分，面积越大越强。")

fig_radar = go.Figure()
fig_radar.add_trace(go.Scatterpolar(
    r=v7_scores, theta=dimensions, fill='toself', name='旧版 (v7)',
    line_color='gray', fillcolor='rgba(128, 128, 128, 0.3)'
))
fig_radar.add_trace(go.Scatterpolar(
    r=v8_scores, theta=dimensions, fill='toself', name='新版 (v8)',
    line_color='#00CC96', fillcolor='rgba(0, 204, 150, 0.3)'
))
fig_radar.update_layout(
    polar=dict(radialaxis=dict(visible=True, range=[0, 10])),
    showlegend=True, margin=dict(l=40, r=40, t=20, b=20), height=400
)
st.plotly_chart(fig_radar, use_container_width=True)

st.divider()

# ================= 2. 维度差值柱状图 =================
st.subheader("📈 各维度性能变化 (Delta)")
st.caption("柱子在零轴以上代表提升，零轴以下代表退步。")

# 使用 Plotly 绘制带颜色区分的柱状图
df_bar = pd.DataFrame({"维度": dimensions, "Delta": deltas})
df_bar["颜色"] = df_bar["Delta"].apply(lambda x: '#00CC96' if x >= 0 else '#EF553B')

fig_bar = go.Figure(data=[
    go.Bar(x=df_bar["维度"], y=df_bar["Delta"], marker_color=df_bar["颜色"])
])
fig_bar.update_layout(
    yaxis_title="Delta 收益", margin=dict(l=40, r=40, t=20, b=20), height=300
)
st.plotly_chart(fig_bar, use_container_width=True)

st.divider()

# ================= 3. 历史趋势图 =================
st.subheader("🚀 历史版本迭代综合得分曲线")
st.caption("展示模型在历次 Prompt 迭代中的综合得分进步情况。")

trend_data = pd.DataFrame({
    "迭代批次": ["v5", "v6 (旧版)", "v7", "v8 (新版)", "v9 (预测)"],
    "综合得分": [7.1, 7.8, 8.2, 8.6, 8.7]
})
fig_line = px.line(trend_data, x="迭代批次", y="综合得分", markers=True)
fig_line.update_traces(line_color='#FF4B4B', line_width=3, marker_size=8)
fig_line.update_layout(margin=dict(l=40, r=40, t=20, b=20), height=300)
st.plotly_chart(fig_line, use_container_width=True)

st.divider()

# ================= 4. 详细数据表 =================
st.subheader("📋 多维差异数据明细")

demo_data = {
    "维度": dimensions,
    "旧版均分": v7_scores,
    "新版均分": v8_scores,
    "Delta (归一化)": deltas,
    "95% 置信区间": ["[+0.01, +0.03]", "[+0.01, +0.05]", "[-0.01, +0.01]", "[+0.02, +0.08]", "[-0.02, +0.04]"],
    "统计学判断": ["✅ 显著提升", "✅ 显著提升", "⚪ 跨零，无差异", "✅ 显著提升", "⚪ 跨零，无差异"]
}
df = pd.DataFrame(demo_data)
st.dataframe(df, use_container_width=True)

# ================= 商业钩子 =================
st.warning("💡 **提示：** 您正在查看**开源体验版**的静态演示数据。")
st.info("""
🔒 **企业版解锁功能：**
1. 实时读取您的 MySQL 数据库，渲染真实对比图表。
2. 多团队/多项目协同管理大盘。
3. 一键生成并导出 PDF 评估报告。

👉 **获取企业版 / 定制化私有部署请联系：** 微信 `wxid_2f5h1j7u0dm811` (备注：GitHub 评测)
""")
