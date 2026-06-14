"""
Muse Mirror —— AI 情感伴侣。

启动: streamlit run app.py
"""

import sys, os
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

import streamlit as st
from companion import Companion


def resolve_api_key():
    """优先级: st.secrets → 环境变量 → .api_key 文件"""
    try:
        key = st.secrets.get("ANTHROPIC_API_KEY", "")
        if key:
            return key
    except Exception:
        pass
    key = os.environ.get("ANTHROPIC_API_KEY", "")
    if key:
        return key
    keyfile = PROJECT_ROOT / ".api_key"
    if keyfile.exists():
        return keyfile.read_text().strip()
    raise RuntimeError(
        "未找到 API Key。请在 Streamlit Cloud Secrets 或 .api_key 文件中设置 ANTHROPIC_API_KEY"
    )


# ─── 页面设置 ────────────────────────────────────────────

st.set_page_config(
    page_title="Muse Mirror",
    page_icon="🪞",
    layout="centered",
    initial_sidebar_state="collapsed",
)

# 隐藏 Streamlit 默认的汉堡菜单和 footer
st.markdown(
    """
<style>
    #MainMenu {visibility: hidden;}
    footer {visibility: hidden;}
    .stApp {max-width: 720px; margin: 0 auto;}
</style>
""",
    unsafe_allow_html=True,
)

# ─── 初始化 ──────────────────────────────────────────────

if "companion" not in st.session_state:
    api_key = resolve_api_key()
    st.session_state.companion = Companion(api_key=api_key)
    st.session_state.messages = []

    # 首条消息
    welcome = "嗨，我是镜。今天过得怎么样？"
    st.session_state.messages.append({"role": "assistant", "content": welcome})
    st.session_state.companion.memory.add_message("assistant", welcome)

companion = st.session_state.companion

# ─── 标题 ────────────────────────────────────────────────

st.title("🪞 Muse Mirror")
st.caption("一个会记得你的 AI 伴侣")

# ─── 聊天记录 ────────────────────────────────────────────

for msg in st.session_state.messages:
    with st.chat_message(msg["role"]):
        st.markdown(msg["content"])

# ─── 输入 ────────────────────────────────────────────────

if prompt := st.chat_input("说点什么吧……"):
    # 显示用户消息
    st.session_state.messages.append({"role": "user", "content": prompt})
    with st.chat_message("user"):
        st.markdown(prompt)

    # 获取 AI 回复
    with st.chat_message("assistant"):
        with st.spinner(""):
            reply = companion.send(prompt)
        st.markdown(reply)

    st.session_state.messages.append({"role": "assistant", "content": reply})
    st.rerun()

# ─── 侧边栏：记忆管理 ────────────────────────────────────

with st.sidebar:
    st.subheader("记忆")
    stats = companion.stats
    st.metric("对话条数", stats["messages"])
    st.metric("已知偏好", stats["preferences"])

    prefs = companion.memory.all_preferences()
    if prefs:
        with st.expander("我了解的关于你"):
            for k, v in prefs.items():
                st.markdown(f"- **{k}** → {v}")

    st.divider()
    if st.button("清空记忆", type="secondary", use_container_width=True):
        companion.reset()
        st.session_state.messages = []
        welcome = "记忆清空啦。我们重新认识一下吧。我是镜，你呢？"
        st.session_state.messages.append({"role": "assistant", "content": welcome})
        companion.memory.add_message("assistant", welcome)
        st.rerun()
