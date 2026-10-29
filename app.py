import os
import json
import sqlite3
import pandas as pd
import streamlit as st
from openai import OpenAI

# 初始化 SQLite 数据库（用来实现持久化记忆）
DB_FILE = "study_agent.db"

def init_db():
    conn = sqlite3.connect(DB_FILE)
    cursor = conn.cursor()
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS tasks (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            task_desc TEXT,
            status TEXT DEFAULT '未完成',
            day_assigned TEXT
        )
    """)
    conn.commit()
    conn.close()

init_db()

# 页面标题
st.set_page_config(page_title="AI 学习规划 Agent", layout="wide")
st.title("🎓 你的专属 AI 学习规划 Agent")

# 侧边栏：API 配置与基础设置
with st.sidebar:
    st.header("⚙️ 配置中心")
    api_key = st.text_input("OpenAI / 兼容 API Key", type="password", value=os.environ.get("OPENAI_API_KEY", ""))
    base_url = st.text_input("API Base URL (可选)", value="https://api.openai.com/v1")
    available_hours = st.slider("每天可用学习时间 (小时)", 1.0, 10.0, 3.0, 0.5)
    
    st.markdown("---")
    st.markdown("### 💡 使用说明")
    st.markdown("1. 输入你的任务。")
    st.markdown("2. 点击生成计划。")
    st.markdown("3. 每日汇报进度，Agent 会自动帮你动态调整！")

# 客户端初始化函数
def get_client(key, url):
    if not key:
        return None
    return OpenAI(api_key=key, base_url=url)

# 主界面分两栏
col1, col2 = st.columns([1, 1])

with col1:
    st.subheader("📝 1. 输入任务或今日反馈")
    user_input = st.text_area(
        "写下这段时间的任务，或者今天完成情况（例如：'我今天只背了单词，没写爬虫'）：",
        height=150,
        placeholder="例如：\n1. 线性代数第 4 章习题\n2. 每天背 50 个单词\n3. 编程作业本周五截止"
    )
    
    if st.button("✨ 让 AI 规划/调整计划", type="primary"):
        if not api_key:
            st.error("请先在左侧侧边栏输入你的 API Key！")
        elif not user_input.strip():
            st.warning("请输入一些内容后再提交哦！")
        else:
            client = get_client(api_key, base_url)
            
            # 读取历史任务状态以供 AI 参考
            conn = sqlite3.connect(DB_FILE)
            df_history = pd.read_sql("SELECT * FROM tasks", conn)
            conn.close()
            
            system_prompt = """
            你是一个专业的个人学习规划与调整 Agent。
            你需要根据用户的输入、每天可用时间，以及历史任务完成情况，
            生成或动态调整一份清晰的每日执行计划（Markdown 格式）。
            如果用户反馈了今天的完成进度（比如完成了什么、没完成什么），你要在接下来的几天里帮他把未完成的任务合理顺延。
            """
            
            user_prompt = f"""
            【基本设置】
            每天可用时间：{available_hours} 小时
            
            【历史任务状态参考】
            {df_history.to_string() if not df_history.empty else "暂无历史任务"}
            
            【用户最新输入/反馈】
            {user_input}
            
            请输出最新的排期计划。
            """
            
            with st.spinner("AI 正在为你精心编排计划..."):
                try:
                    response = client.chat.completions.create(
                        model="deepseek-ai/DeepSeek-V3",
                        messages=[
                            {"role": "system", "content": system_prompt},
                            {"role": "user", "content": user_prompt}
                        ],
                        temperature=0.7
                    )
                    plan_result = response.choices[0].message.content
                    st.session_state["latest_plan"] = plan_result
                except Exception as e:
                    st.error(f"调用 API 出错: {e}")

with col2:
    st.subheader("📅 2. 你的智能学习排期")
    if "latest_plan" in st.session_state:
        st.markdown(st.session_state["latest_plan"])
    else:
        st.info("在左侧输入任务并点击按钮后，这里会显示你的专属计划。")

# 底部：持久化任务数据库预览
st.markdown("---")
st.subheader("🗂️ 3. 任务数据库（SQLite 持久化）")
conn = sqlite3.connect(DB_FILE)
df_tasks = pd.read_sql("SELECT * FROM tasks", conn)
conn.close()

if not df_tasks.empty:
    st.dataframe(df_tasks, use_container_width=True)
    if st.button("清空任务数据库"):
        conn = sqlite3.connect(DB_FILE)
        conn.execute("DELETE FROM tasks")
        conn.commit()
        conn.close()
        st.success("数据库已清空！")
        st.rerun()
else:
    st.text("当前数据库中暂无记录。")