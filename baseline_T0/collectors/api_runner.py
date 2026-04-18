#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
api_runner.py
批量调用 A 档平台的官方 API，将回答落盘到 raw/{platform}/{qid}_t{trial}.md

用法：
    python api_runner.py                        # 全量：6 平台 × 20 题 × 3 轮
    python api_runner.py --platform deepseek    # 单平台
    python api_runner.py --tier 1               # 只跑一级 4 题
    python api_runner.py --dry-run              # 只列计划不请求

依赖：
    pip install openai zhipuai dashscope requests pyyaml
"""
from __future__ import annotations
import argparse
import datetime as dt
import json
import os
import sys
import time
import uuid
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path
import yaml

ROOT = Path(__file__).resolve().parent.parent
CONFIG = ROOT / "config"
RAW = ROOT / "raw"

# ------- 平台适配层 -------

def call_openai_compatible(endpoint: str, api_key: str, model: str,
                           prompt: str, max_tokens: int, timeout: int) -> str:
    """兼容 OpenAI Chat Completions 协议的通用客户端，适用于：
    DeepSeek / Moonshot (Kimi) / 火山方舟(豆包) / 阿里 DashScope 兼容模式。"""
    from openai import OpenAI
    client = OpenAI(api_key=api_key, base_url=endpoint, timeout=timeout)
    resp = client.chat.completions.create(
        model=model,
        messages=[{"role": "user", "content": prompt}],
        max_tokens=max_tokens,
    )
    return resp.choices[0].message.content or ""


def call_zhipu(endpoint: str, api_key: str, model: str,
               prompt: str, max_tokens: int, timeout: int) -> str:
    from zhipuai import ZhipuAI
    client = ZhipuAI(api_key=api_key)
    resp = client.chat.completions.create(
        model=model,
        messages=[{"role": "user", "content": prompt}],
        max_tokens=max_tokens,
    )
    return resp.choices[0].message.content or ""


def call_qianfan(endpoint: str, api_key: str, model: str,
                 prompt: str, max_tokens: int, timeout: int) -> str:
    """百度千帆 v2 支持 OpenAI 兼容模式。"""
    from openai import OpenAI
    client = OpenAI(api_key=api_key, base_url=endpoint, timeout=timeout)
    resp = client.chat.completions.create(
        model=model,
        messages=[{"role": "user", "content": prompt}],
        max_tokens=max_tokens,
    )
    return resp.choices[0].message.content or ""


PROVIDER_DISPATCH = {
    "openai_compatible": call_openai_compatible,
    "volcengine": call_openai_compatible,      # 火山方舟也是 OpenAI 兼容
    "dashscope": call_openai_compatible,       # DashScope 兼容模式
    "zhipu": call_zhipu,
    "qianfan": call_qianfan,
}


# ------- 主流程 -------

def load_configs():
    plats = yaml.safe_load((CONFIG / "platforms.yaml").read_text(encoding="utf-8"))
    qs = yaml.safe_load((CONFIG / "questions.yaml").read_text(encoding="utf-8"))
    return plats, qs


def write_raw(platform_id: str, qid: str, trial: int, prompt: str,
              answer: str, platform_meta: dict):
    out_dir = RAW / platform_id
    out_dir.mkdir(parents=True, exist_ok=True)
    meta = {
        "run_id": str(uuid.uuid4())[:8],
        "date": dt.date.today().isoformat(),
        "time": dt.datetime.now().isoformat(timespec="seconds"),
        "platform": platform_id,
        "model": platform_meta.get("model"),
        "question_id": qid,
        "trial": trial,
        "prompt": prompt,
    }
    header = f"<!--META:{json.dumps(meta, ensure_ascii=False)}-->\n\n"
    (out_dir / f"{qid}_t{trial}.md").write_text(header + answer, encoding="utf-8")


def run(args):
    plats, qs = load_configs()
    trials = plats["collection"]["trials_per_question"]
    max_tokens = plats["collection"]["max_tokens"]
    timeout = plats["collection"]["timeout_seconds"]

    # 过滤平台：只跑 A 档
    all_platforms = [p for p in plats["platforms"] if p["tier"] == "A"]
    if args.platform:
        all_platforms = [p for p in all_platforms if p["id"] == args.platform]
    if not all_platforms:
        print("[error] 没有可跑的 A 档平台")
        sys.exit(1)

    # 过滤题目
    questions = qs["questions"]
    if args.tier:
        questions = [q for q in questions if q["tier"] == args.tier]
    if args.question:
        questions = [q for q in questions if q["id"] == args.question]

    total = len(all_platforms) * len(questions) * trials
    print(f"[plan] {len(all_platforms)} 平台 × {len(questions)} 题 × {trials} 轮 = {total} 次调用")
    if args.dry_run:
        for p in all_platforms:
            print(f"  - {p['id']:12s} provider={p['provider']:18s} model={p['model']}")
        return

    # 平台级并行：每个平台一个 worker，内部仍串行（保留原节流）
    def run_platform(p):
        api_key = os.environ.get(p["api_key_env"])
        if not api_key:
            print(f"[skip] {p['id']}: 环境变量 {p['api_key_env']} 未设置", flush=True)
            return (p["id"], 0, 0)
        dispatcher = PROVIDER_DISPATCH.get(p["provider"])
        if dispatcher is None:
            print(f"[skip] {p['id']}: provider={p['provider']} 无适配器", flush=True)
            return (p["id"], 0, 0)

        d, f = 0, 0
        for q in questions:
            for t in range(1, trials + 1):
                target = RAW / p["id"] / f"{q['id']}_t{t}.md"
                if target.exists() and not args.force:
                    continue
                try:
                    ans = dispatcher(
                        endpoint=p["endpoint"],
                        api_key=api_key,
                        model=p["model"],
                        prompt=q["prompt"],
                        max_tokens=max_tokens,
                        timeout=timeout,
                    )
                    write_raw(p["id"], q["id"], t, q["prompt"], ans, p)
                    d += 1
                    print(f"[ok] {p['id']} / {q['id']} / t{t} ({len(ans)} chars)", flush=True)
                    time.sleep(1.0)       # 节流，避免触发限流
                except Exception as e:
                    f += 1
                    print(f"[fail] {p['id']} / {q['id']} / t{t}: {e}", flush=True)
                    time.sleep(3.0)
        print(f"[platform-done] {p['id']}: 成功 {d} 条，失败 {f} 条", flush=True)
        return (p["id"], d, f)

    done, failed = 0, 0
    with ThreadPoolExecutor(max_workers=len(all_platforms)) as ex:
        futures = [ex.submit(run_platform, p) for p in all_platforms]
        for fut in as_completed(futures):
            _, d, f = fut.result()
            done += d
            failed += f

    print(f"[done] 成功 {done} 条，失败 {failed} 条")


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--platform", help="只跑某平台 id，如 deepseek")
    ap.add_argument("--tier", type=int, help="只跑 tier (1=一级4题)")
    ap.add_argument("--question", help="只跑某题 id，如 M1")
    ap.add_argument("--force", action="store_true", help="覆盖已存在的 raw 文件")
    ap.add_argument("--dry-run", action="store_true", help="只列计划不调用")
    run(ap.parse_args())
