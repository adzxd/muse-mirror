"""快速测试脚本 —— 从 key.txt 读取 DeepSeek Key 并测试对话。"""
import os, sys
sys.path.insert(0, os.path.dirname(__file__))

key_path = os.path.join(os.path.dirname(__file__), "key.txt")
if not os.path.exists(key_path):
    print("请先把 DeepSeek Key 写入 key.txt，然后运行: python test_chat.py")
    sys.exit(1)

with open(key_path) as f:
    os.environ["ANTHROPIC_API_KEY"] = f.read().strip()

from companion import Companion
c = Companion()
print("正在测试...")
reply = c.send("你好，用一句话介绍你自己是谁")
print("REPLY:", reply)
print("STATS:", c.stats)
print("成功！现在运行: streamlit run app.py")
