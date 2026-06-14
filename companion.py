"""DeepSeek 官方 API —— 国内直连，支付宝充值。"""

import os, json, requests
from loguru import logger
from persona import PERSONA
from memory import MemoryStore, Message

BASE_URL = "https://api.deepseek.com/v1/chat/completions"
MODEL = os.environ.get("MUSE_MODEL", "deepseek-chat")
PREF_MODEL = "deepseek-chat"
MAX_TOKENS = 2048
PREF_EXTRACT_INTERVAL = 6

PREF_EXTRACT_PROMPT = """从以上对话中提取关于"用户"的新信息，用 JSON 返回。
格式: [{"key": "mood", "value": "最近压力大"}, ...]
没有新信息返回 []。只返回 JSON 数组。"""


class Companion:
    """AI 伴侣 —— DeepSeek 官方 API（国内直连，无墙）。"""

    def __init__(self, api_key=""):
        self.api_key = api_key
        self.memory = MemoryStore()
        self._msg_count = self.memory.message_count()

    def _call(self, messages, model=MODEL, max_tokens=MAX_TOKENS, stream=True):
        body = {
            "model": model,
            "messages": messages,
            "max_tokens": max_tokens,
            "temperature": 0.9,
            "stream": stream,
        }
        r = requests.post(
            BASE_URL,
            headers={"Authorization": f"Bearer {self.api_key}", "Content-Type": "application/json"},
            json=body,
            timeout=120,
        )
        r.raise_for_status()

        if stream:
            full = ""
            for line in r.iter_lines(decode_unicode=True):
                if line and line.startswith("data: ") and line[6:] != "[DONE]":
                    try:
                        d = json.loads(line[6:])
                        c = d.get("choices", [{}])[0].get("delta", {}).get("content", "")
                        full += c
                    except Exception:
                        pass
            return full
        else:
            return r.json()["choices"][0]["message"]["content"]

    def send(self, text):
        h = self.memory.recent_messages()
        p = self.memory.all_preferences()
        msgs = [{"role": "system", "content": PERSONA}]
        if p:
            lines = ["# 关于对方的已知信息:"] + [f"- {k}: {v}" for k, v in p.items()]
            msgs += [
                {"role": "user", "content": "\n".join(lines)},
                {"role": "assistant", "content": "好的，我记住了。"},
            ]
        for m in h:
            msgs.append({"role": m.role, "content": m.content})
        msgs.append({"role": "user", "content": text})
        try:
            reply = self._call(msgs)
        except Exception as e:
            msg = str(e)
            logger.error(f"对话失败: {msg}")
            if hasattr(e, 'response') and e.response is not None:
                try:
                    detail = e.response.json()
                except:
                    detail = e.response.text[:300]
                logger.error(f"API详情: {detail}")
                return f"（API错误：{detail}）"
            return f"（信号不太好……{msg[:100]}）"
        self.memory.add_message("user", text)
        self.memory.add_message("assistant", reply)
        self._msg_count += 2
        if self._msg_count % (PREF_EXTRACT_INTERVAL * 2) == 0:
            self._extract(h, text)
        return reply

    def _extract(self, history, text):
        try:
            conv = "\n".join(
                f"{'用户' if m.role == 'user' else '镜'}: {m.content}"
                for m in history[-8:]
            )
            conv += f"\n用户: {text}"
            result = self._call(
                [
                    {"role": "system", "content": "信息提取助手。只返回 JSON。"},
                    {"role": "user", "content": conv},
                    {"role": "user", "content": PREF_EXTRACT_PROMPT},
                ],
                model=PREF_MODEL,
                max_tokens=256,
                stream=False,
            )
            a, b = result.find("["), result.rfind("]")
            if a != -1 and b != -1:
                for item in json.loads(result[a : b + 1]):
                    if isinstance(item, dict) and "key" in item:
                        self.memory.set_preference(item["key"], item["value"])
        except Exception:
            pass

    def reset(self):
        self.memory.reset()
        self._msg_count = 0

    @property
    def stats(self):
        return self.memory.stats()
