import streamlit as st
import sqlite3
import datetime
from openai import OpenAI

# 1. 数据库初始化与操作函数
def init_db():
    conn = sqlite3.connect("study_agent.db")
    c = conn.cursor()
    c.execute('''
        CREATE TABLE IF NOT EXISTS study_tasks (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            timestamp TEXT,
            task_input TEXT,
            plan_output TEXT
        )
    ''')
    conn.commit()
    conn.close()

def save_task(task_input, plan_output):
    conn = sqlite3.connect("study_agent.db")
    c = conn.cursor()
    timestamp = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    c.execute("INSERT INTO study_tasks (timestamp, task_input, plan_output) VALUES (?, ?, ?)",
              (timestamp, task_input, plan_output))
    conn.commit()
    conn.close()

def get_tasks():
    conn = sqlite3.connect("study_agent.db")
    c = conn.cursor()
    c.execute("SELECT timestamp, task_input, plan_output FROM study_tasks ORDER BY id DESC")
    rows = c.fetchall()
    conn.close()
    return rows

# 初始化数据库
init_db()

st.set_page_config(page_title="AI 学习规划 Agent", layout="wide")
st.title("🎓 你的专属 AI 学习规划 Agent")

# 侧边栏配置
with st.sidebar:
    st.header("⚙️ 配置中心")
    api_key = st.text_input("OpenAI / 兼容 API Key", type="password")
    base_url = st.text_input("API Base URL (可选)", value="https://api.siliconflow.cn/v1")
    hours = st.slider("每天可用学习时间 (小时)", 1.0, 10.0, 1.5)

# 主界面
st.subheader("📝 1. 输入任务或今日反馈")
task_input = st.text_area("写下这段时间的任务，或者今天完成情况：", placeholder="例如：学习C primer plus,写课后习题程序...")

if st.button("✨ 让 AI 规划/调整计划"):
    if not api_key:
        st.error("请先在左侧输入 API Key！")
    elif not task_input:
        st.warning("请先输入学习任务！")
    else:
        try:
            client = OpenAI(api_key=api_key, base_url=base_url)
            with st.spinner("AI 正在为你量身定制学习排期..."):
                response = client.chat.completions.create(
                    model="deepseek-ai/DeepSeek-V3",
                    messages=[
                        {"role": "system", "content": f"你是一个专业的学习规划助手。用户每天可用时间为 {hours} 小时。请根据用户的输入生成结构化的学习计划（使用 Markdown 排版，分天排布）。"},
                        {"role": "user", "content": task_input}
                    ]
                )
                plan_output = response.choices[0].message.content
                
                # 核心：生成成功后自动存入 SQLite 数据库
                save_task(task_input, plan_output)
                
                st.success("计划生成成功并已自动写入数据库！")
        except Exception as e:
            st.error(f"调用 API 出错: {e}")

# 获取历史任务
tasks = get_tasks()

# 展示最近一次生成的排期
if tasks:
    st.subheader("📅 2. 你的智能学习排期")
    st.markdown(tasks[0][2])
else:
    st.info("在左侧填入 Key，并在上方输入任务点击生成后，这里会显示你的专属计划。")

st.markdown("---")

# 3. 任务数据库展示区
st.subheader("📁 3. 任务数据库 (SQLite 持久化)")
if tasks:
    st.write(f"当前数据库共保存了 {len(tasks)} 条历史记录：")
    for idx, (ts, t_in, p_out) in enumerate(tasks):
        with st.expander(f"记录 #{len(tasks)-idx} —— 时间: {ts}"):
            st.write(f"**输入的任务**: {t_in}")
            st.markdown(f"**AI 生成的计划**: \n{p_out}")
else:
    st.info("当前数据库中暂无记录。")