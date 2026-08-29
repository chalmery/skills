#!/usr/bin/env python3
"""yt-summary 总结脚本：读取转写文本，生成中文结构化摘要。

两种模式:
1. 本地总结（推荐）: 使用 Ollama 本地大模型生成摘要（完全离线/免费）
   python3 summarize.py <transcript.txt> [--ollama qwen2.5:7b]
2. 提示词模式: 生成一段可直接粘贴给任意 AI 助手的总结提示词
   python3 summarize.py <transcript.txt> --prompt-only
"""
import argparse
import os
import subprocess
import sys

PROMPT_TEMPLATE = """你是一位专业的视频内容分析助手。请阅读下面的视频转写文本（带时间戳），用简体中文输出一份结构化摘要，包含：

## 视频要点
- 用 3-5 条核心要点概括视频主要内容

## 详细内容
- 按主题分小节展开，每个小节包含关键论点和数据

## 关键数据/引述
- 提取视频中的具体数字、对比数据、重要引述

## 总结
- 作者的核心结论和观点

要求：忠实于原文，不添加原文没有的信息；如有疑似转写错误（同音字/错别字）请在不影响理解的前提下尽量还原；保留所有关键数字。

以下是转写文本：
---BEGIN TRANSCRIPT---
{transcript}
---END TRANSCRIPT---
"""


def read_transcript(path: str) -> str:
    with open(path, encoding="utf-8") as f:
        return f.read()


def build_prompt(transcript: str) -> str:
    # 文本可能很长，截断到合理长度（本地 LLM 上下文限制）
    max_chars = int(os.environ.get("YT_SUMMARY_MAX_CHARS", "60000"))
    if len(transcript) > max_chars:
        transcript = transcript[:max_chars] + "\n...[已截断]...\n"
    return PROMPT_TEMPLATE.format(transcript=transcript)


def summarize_with_ollama(prompt: str, model: str) -> str:
    """调用 Ollama 本地模型总结"""
    result = subprocess.run(
        ["ollama", "run", model, prompt],
        capture_output=True, text=True, timeout=1800,
    )
    if result.returncode != 0:
        raise RuntimeError(f"Ollama 调用失败: {result.stderr.strip()}")
    return result.stdout.strip()


def main():
    ap = argparse.ArgumentParser(description="YouTube 转写文本总结")
    ap.add_argument("transcript", help="转写文本文件路径（yt-summary.sh 的输出）")
    ap.add_argument("--ollama", default="qwen2.5:7b", help="Ollama 模型名（默认 qwen2.5:7b）")
    ap.add_argument("--prompt-only", action="store_true",
                    help="只输出提示词，不调用本地模型（可自行粘贴给任意 AI）")
    args = ap.parse_args()

    if not os.path.exists(args.transcript):
        sys.exit(f"❌ 文件不存在: {args.transcript}")

    transcript = read_transcript(args.transcript)
    prompt = build_prompt(transcript)

    if args.prompt_only:
        print(prompt)
        return

    # 检查 Ollama
    if subprocess.run(["which", "ollama"], capture_output=True).returncode != 0:
        print("⚠️  未安装 Ollama，改用 --prompt-only 模式输出提示词：")
        print("=" * 60)
        print(prompt)
        return

    print(f"==> 调用本地模型 {args.ollama} 生成摘要（可能需 1-3 分钟）...")
    try:
        summary = summarize_with_ollama(prompt, args.ollama)
        out_path = os.path.splitext(args.transcript)[0] + "_summary.md"
        with open(out_path, "w", encoding="utf-8") as f:
            f.write(summary)
        print(f"✅ 摘要已保存: {out_path}")
        print("=" * 60)
        print(summary)
    except RuntimeError as e:
        print(f"❌ {e}")
        print("提示: 先安装 Ollama 并拉取模型:")
        print("  curl -fsSL https://ollama.com/install.sh | sh")
        print(f"  ollama pull {args.ollama}")


if __name__ == "__main__":
    main()
