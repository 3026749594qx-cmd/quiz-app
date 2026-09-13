#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Quiz Assistant · 题库生成参考脚本（面向 Agent）

作用：把「文本化的题目材料」解析成刷题器可用的 banks/<bank-id>/questions.json。

这个脚本是针对《安全测试-学习资料》这种「题号 + 题干 + 选项 + 答案 + 题型」格式
写的参考实现。不同学习资料的排版格式不一样，Agent 接入新题库时必须先读原始材料，
按实际格式调整下面第 1 步的正则切块逻辑，其余步骤（JSON 结构、校验、写入）通用。

用法（在项目根目录 quiz-web/ 下执行）：
    python tools/parse_quiz.py <题目txt文件> <输出json路径> --source "题库显示名"

示例：
    python tools/parse_quiz.py ..\pdf_text_raw.txt banks\new-bank\questions.json --source "我的新题库"

前置：需要先通过 pdfplumber 等工具把 PDF 提取为纯文本 txt（见 README 接入指南第 1 步）。
"""

import argparse
import json
import os
import re
import sys
from collections import Counter


# ---------- 1. 切块：把纯文本按「题号」切成题目块 ----------
# 常见题号行形态：`1、xxx` / `1. xxx` / `1．xxx`
NUM_RE = re.compile(r"^(\d{1,3})[、．.]\s*(.*)$")

# 选项行：`A、xxx` / `A. xxx` / `A．xxx`
OPT_RE = re.compile(r"^([A-H])[\.．、]\s*(.*)$")

# 答案 / 题型行（可能跟在选项后面，也可能在题号行附近）
ANS_RE = re.compile(r"^答案[:：]\s*([A-H]+)\s*$")
TYPE_RE = re.compile(r"^题型[:：]\s*(.+?)\s*$")

TYPE_MAP = {
    "判断题": "judge",
    "单选题": "single",
    "多选题": "multiple",
    "填空题": "blank",
}


def split_blocks(lines):
    """按题号行切块，返回 [{num, lines}]。"""
    blocks = []
    cur = None
    for line in lines:
        m = NUM_RE.match(line)
        if m:
            if cur is not None:
                blocks.append(cur)
            cur = {"num": int(m.group(1)), "lines": []}
            if m.group(2).strip():
                cur["lines"].append(m.group(2).strip())
        elif cur is not None:
            cur["lines"].append(line)
    if cur is not None:
        blocks.append(cur)
    return blocks


def parse_block(blk):
    """把一个题目块解析为刷题器题目对象；格式不符合时返回 None。"""
    all_lines = list(blk["lines"])

    # 找到第一个选项行，之前都是题干
    first_opt_idx = None
    for i, line in enumerate(all_lines):
        if OPT_RE.match(line):
            first_opt_idx = i
            break
    if first_opt_idx is None:
        return None

    stem = "".join(all_lines[:first_opt_idx]).strip()
    options = {}
    answer = None
    qtype_label = None
    cur_label = None
    cur_text = []

    for line in all_lines[first_opt_idx:]:
        m_ans = ANS_RE.match(line)
        m_type = TYPE_RE.match(line)
        m_opt = OPT_RE.match(line)
        if m_ans:
            answer = m_ans.group(1)
        elif m_type:
            qtype_label = m_type.group(1)
        elif m_opt:
            if cur_label is not None:
                options[cur_label] = "".join(cur_text).strip()
            cur_label = m_opt.group(1)
            cur_text = [m_opt.group(2)]
        else:
            if cur_label is not None:
                cur_text.append(line)
    if cur_label is not None:
        options[cur_label] = "".join(cur_text).strip()

    if answer is None or qtype_label is None:
        return None

    qtype = TYPE_MAP.get(qtype_label, qtype_label)
    return {
        "num": blk["num"],
        "id": f"q{blk['num']}",
        "type": qtype,
        "stem": stem,
        "options": options,
        "answer": answer,
    }


def main():
    ap = argparse.ArgumentParser(description="把文本化题目解析为 Quiz Assistant 题库 JSON")
    ap.add_argument("input_txt", help="题目纯文本 txt 路径")
    ap.add_argument("output_json", help="输出 questions.json 路径")
    ap.add_argument("--source", default="", help="题库显示名（写入 meta.source）")
    args = ap.parse_args()

    with open(args.input_txt, encoding="utf-8") as f:
        text = f.read()

    # 去掉分页标记等噪音
    text = re.sub(r"={5,}\s*PAGE\s*\d+\s*={5,}", "", text)
    text = text.replace("\u3000", " ")
    lines = [l.strip() for l in text.split("\n") if l.strip()]

    blocks = split_blocks(lines)
    questions = []
    for blk in blocks:
        q = parse_block(blk)
        if q:
            questions.append(q)
    questions.sort(key=lambda q: q["num"])

    # ---------- 校验：只输出 Agent 要看的报告，别让坏数据入库 ----------
    issues = []
    for i, q in enumerate(questions):
        if q["num"] != i + 1:
            issues.append(("题号不连续", i + 1, q["num"]))
        if not q["options"]:
            issues.append(("缺选项", q["num"]))
        if not q["answer"]:
            issues.append(("缺答案", q["num"]))
        if not q["stem"]:
            issues.append(("缺题干", q["num"]))
        if q["type"] not in ("judge", "single", "multiple", "blank"):
            issues.append(("未知题型", q["num"], q["type"]))
        for opt, val in q["options"].items():
            if not val:
                issues.append(("空选项内容", q["num"], opt))

    print("解析成功题数:", len(questions))
    print("题型分布:", dict(Counter(q["type"] for q in questions)))
    print("选项数分布:", dict(Counter(len(q["options"]) for q in questions)))
    print("答案分布:", dict(Counter(q["answer"] for q in questions)))
    print("问题:", issues if issues else "无")

    if issues:
        print("存在校验问题，请修正源文本或调整正则后重试（不要强行入库）。")
        sys.exit(1)
    if not questions:
        print("一个题目都没解析出来，请检查切块正则与源文本格式。")
        sys.exit(1)

    clean = [
        {"id": q["id"], "type": q["type"], "stem": q["stem"], "options": q["options"], "answer": q["answer"]}
        for q in questions
    ]
    data = {"meta": {"source": args.source or os.path.basename(os.path.dirname(args.output_json)), "total": len(clean)}, "questions": clean}

    os.makedirs(os.path.dirname(args.output_json), exist_ok=True)
    with open(args.output_json, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)
    print("已写入:", os.path.abspath(args.output_json))


if __name__ == "__main__":
    main()
