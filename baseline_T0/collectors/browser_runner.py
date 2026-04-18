#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
browser_runner.py
B 档平台（无公开 API 或需登录）用 Playwright 半自动采集。
当前支持：
  - yuanbao      腾讯元宝
  - baidu_ai     百度AI搜索
  - quark_ai     夸克AI

使用步骤：
  1. 首次为每个平台做登录并保存 storage_state:
     python browser_runner.py --login yuanbao
     （脚本会打开浏览器，请在 120s 内完成扫码/登录，然后回车）
  2. 正式采集：
     python browser_runner.py --platform yuanbao --tier 1

⚠️ 平台网页结构经常变动，下方选择器(selectors) 需要在首次跑之前 inspect 校准。
   每个平台的 selector 集中在 PLATFORM_SELECTORS 中维护。

依赖：
    pip install playwright pyyaml
    playwright install chromium
"""
from __future__ import annotations
import argparse
import datetime as dt
import json
import sys
import time
import uuid
from pathlib import Path
import yaml

ROOT = Path(__file__).resolve().parent.parent
CONFIG = ROOT / "config"
RAW = ROOT / "raw"
STATE = ROOT / ".playwright_state"
STATE.mkdir(exist_ok=True)

# ---- 每个平台的选择器（需要首次跑之前人工校准） ----
PLATFORM_SELECTORS = {
    "yuanbao": {
        "url": "https://yuanbao.tencent.com/",
        "new_chat_btn": "button:has-text('新建对话'), [class*='new-chat']",
        "input_box": "textarea, div[contenteditable='true']",
        "send_btn": "button[class*='send'], button:has-text('发送')",
        "answer_container": "[class*='markdown'], [class*='message-content']",
        "wait_done_selector": "[class*='stop']",     # 出现停止按钮=生成中；消失=完成
        "wait_done_strategy": "disappear",
    },
    "baidu_ai": {
        "url": "https://chat.baidu.com/",
        "new_chat_btn": "button:has-text('新对话'), [class*='new']",
        "input_box": "textarea",
        "send_btn": "button[class*='send']",
        "answer_container": "[class*='answer'], [class*='markdown']",
        "wait_done_selector": "[class*='stop']",
        "wait_done_strategy": "disappear",
    },
    "quark_ai": {
        "url": "https://quark.sm.cn/",
        "new_chat_btn": None,
        "input_box": "textarea, input[type='search']",
        "send_btn": "button[class*='search'], button[class*='send']",
        "answer_container": "[class*='answer'], [class*='result']",
        "wait_done_selector": "[class*='loading']",
        "wait_done_strategy": "disappear",
    },
}


def state_path(platform_id: str) -> Path:
    return STATE / f"{platform_id}.json"


def do_login(platform_id: str):
    from playwright.sync_api import sync_playwright
    sel = PLATFORM_SELECTORS[platform_id]
    with sync_playwright() as pw:
        browser = pw.chromium.launch(headless=False)
        ctx = browser.new_context()
        page = ctx.new_page()
        page.goto(sel["url"])
        print(f"请在浏览器中完成登录（扫码/账号密码），完成后回到终端按回车继续…")
        input()
        ctx.storage_state(path=state_path(platform_id))
        print(f"[ok] 登录态已保存 -> {state_path(platform_id)}")
        browser.close()


def write_raw(platform_id: str, qid: str, trial: int, prompt: str, answer: str, model: str = ""):
    out_dir = RAW / platform_id
    out_dir.mkdir(parents=True, exist_ok=True)
    meta = {
        "run_id": str(uuid.uuid4())[:8],
        "date": dt.date.today().isoformat(),
        "time": dt.datetime.now().isoformat(timespec="seconds"),
        "platform": platform_id,
        "model": model,
        "question_id": qid,
        "trial": trial,
        "prompt": prompt,
    }
    header = f"<!--META:{json.dumps(meta, ensure_ascii=False)}-->\n\n"
    (out_dir / f"{qid}_t{trial}.md").write_text(header + answer, encoding="utf-8")


def ask_one(page, sel: dict, prompt: str, max_wait_s: int = 120) -> str:
    """在打开的页面上提交 prompt 并等待回答完成，返回回答文本。
    对页面结构强依赖，需要根据平台实际 DOM 调整。"""
    # 新建对话（如果有按钮）
    if sel.get("new_chat_btn"):
        try:
            page.locator(sel["new_chat_btn"]).first.click(timeout=5000)
            page.wait_for_timeout(1000)
        except Exception:
            pass
    # 输入
    box = page.locator(sel["input_box"]).first
    box.click()
    box.fill("")
    box.type(prompt, delay=20)
    page.wait_for_timeout(500)
    # 发送
    page.locator(sel["send_btn"]).first.click()
    # 等待完成
    strategy = sel.get("wait_done_strategy", "disappear")
    done_sel = sel.get("wait_done_selector")
    deadline = time.time() + max_wait_s
    if done_sel:
        # 先等它出现（开始生成）
        try:
            page.wait_for_selector(done_sel, timeout=10000)
        except Exception:
            pass
        # 再等它消失（生成完成）
        while time.time() < deadline:
            if page.locator(done_sel).count() == 0:
                break
            page.wait_for_timeout(1000)
    else:
        page.wait_for_timeout(max_wait_s * 1000)

    page.wait_for_timeout(1500)  # 稳定等待
    containers = page.locator(sel["answer_container"]).all()
    if not containers:
        return ""
    # 取最后一段作为最新回答
    return containers[-1].inner_text()


def run_platform(platform_id: str, questions: list, trials: int, force: bool):
    if platform_id not in PLATFORM_SELECTORS:
        print(f"[error] 未实现的平台: {platform_id}"); return
    sel = PLATFORM_SELECTORS[platform_id]
    sp = state_path(platform_id)
    from playwright.sync_api import sync_playwright
    with sync_playwright() as pw:
        browser = pw.chromium.launch(headless=False)   # 保持 headful 方便观察
        ctx_kwargs = {}
        if sp.exists():
            ctx_kwargs["storage_state"] = str(sp)
        ctx = browser.new_context(**ctx_kwargs)
        page = ctx.new_page()
        page.goto(sel["url"])
        page.wait_for_timeout(3000)

        for q in questions:
            for t in range(1, trials + 1):
                target = RAW / platform_id / f"{q['id']}_t{t}.md"
                if target.exists() and not force:
                    continue
                try:
                    answer = ask_one(page, sel, q["prompt"])
                    if not answer.strip():
                        print(f"[empty] {platform_id}/{q['id']}/t{t} 回答为空，人工兜底")
                        continue
                    write_raw(platform_id, q["id"], t, q["prompt"], answer)
                    print(f"[ok] {platform_id}/{q['id']}/t{t} ({len(answer)} chars)")
                except Exception as e:
                    print(f"[fail] {platform_id}/{q['id']}/t{t}: {e}")
                time.sleep(2.0)
        browser.close()


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--login", help="为某平台保存登录态，如 yuanbao")
    ap.add_argument("--platform", help="正式采集某平台")
    ap.add_argument("--tier", type=int)
    ap.add_argument("--question")
    ap.add_argument("--force", action="store_true")
    args = ap.parse_args()

    if args.login:
        do_login(args.login); return
    if not args.platform:
        print("请用 --platform 指定要跑的平台"); sys.exit(1)

    plats = yaml.safe_load((CONFIG / "platforms.yaml").read_text(encoding="utf-8"))
    qs = yaml.safe_load((CONFIG / "questions.yaml").read_text(encoding="utf-8"))
    trials = plats["collection"]["trials_per_question"]
    questions = qs["questions"]
    if args.tier:
        questions = [q for q in questions if q["tier"] == args.tier]
    if args.question:
        questions = [q for q in questions if q["id"] == args.question]

    run_platform(args.platform, questions, trials, args.force)


if __name__ == "__main__":
    main()
