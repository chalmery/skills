---
name: yt-summary
description: 下载 YouTube 视频音频并在本机用 whisper.cpp 转写，可继续用本地 Ollama 生成中文摘要。当用户给出 YouTube 链接并要求转写、提取内容或总结视频时使用；不适用于普通网页或已有文本的摘要。
---

# YouTube 本地转写与总结

该工作流用 `yt-dlp` 下载音频、FFmpeg 转换格式、whisper.cpp 转写，并可用 Ollama 总结。音频获取需要联网；转写和默认总结在本机完成，不会主动把内容上传到第三方模型服务。

## 执行原则

1. 根据本 `SKILL.md` 的实际路径确定 Skill 目录，不要假设固定的 Agent 安装路径。
2. 用户只要求摘要时，也先获得可靠转写；不要仅根据视频标题或简介编造内容。
3. 运行结束后报告转写文件和摘要文件的实际路径，并说明自动转写可能存在专有名词、数字和同音字错误。
4. 处理长视频时检查是否发生文本截断；涉及关键数字、引述或争议结论时回看相应时间段，不把机器转写当成逐字校对稿。
5. 遵守视频版权与平台规则，只处理用户有权访问和用于个人学习、研究的内容。

## 环境要求

- `yt-dlp`、FFmpeg；Node.js 可提高部分 YouTube 视频的解析成功率。
- whisper.cpp 可执行文件，默认位置为 `~/.local/share/yt-summary/whisper.cpp/build/bin/whisper-cli`。
- Whisper 模型；缺失时转写脚本会调用 whisper.cpp 自带的下载脚本。
- Ollama 仅在需要本地自动总结时使用；`--prompt-only` 模式不要求 Ollama。

可用环境变量：

- `WHISPER_DIR`：覆盖 whisper.cpp 根目录。
- `YT_SUMMARY_OUT`：覆盖输出根目录，默认 `~/yt-summary`。
- `YT_SUMMARY_MAX_CHARS`：限制送入本地模型的转写字符数，默认 `60000`。

## 使用方式

以下示例中的 `SKILL_DIR` 表示本文件所在目录：

```bash
SKILL_DIR="<yt-summary 的实际目录>"

# 下载音频并转写；模型可选 tiny/base/small/medium/large
bash "$SKILL_DIR/scripts/yt-summary.sh" "<YouTube URL>" small

# 用本地 Ollama 总结实际生成的 transcript.txt
python3 "$SKILL_DIR/scripts/summarize.py" "/实际输出目录/transcript.txt"

# 只生成总结提示词，不调用 Ollama
python3 "$SKILL_DIR/scripts/summarize.py" "/实际输出目录/transcript.txt" --prompt-only

# 选择其他本地模型
python3 "$SKILL_DIR/scripts/summarize.py" "/实际输出目录/transcript.txt" --ollama qwen2.5:7b
```

转写结果默认写入 `~/yt-summary/<视频ID>/transcript.txt`，摘要写入同目录的 `transcript_summary.md`。应以脚本实际输出为准，不要为了寻找视频 ID 再重复请求 YouTube。

## 故障边界

- 下载失败：先检查 URL、网络、`yt-dlp` 版本与 Node.js；不要绕过需要登录、地区限制或版权限制的内容。
- whisper.cpp 不存在：按脚本显示的路径检查 `WHISPER_DIR` 和 Vulkan 构建产物。
- GPU 不可用：报告当前环境问题；是否改用 CPU、重编译或安装系统包应由用户决定。
- Ollama 不存在：脚本会输出提示词而不是本地摘要。这不等于已经生成摘要，应明确告诉用户当前产物是什么。
- 长文本：当前总结脚本会按 `YT_SUMMARY_MAX_CHARS` 截断，可能遗漏视频后半段；需要完整覆盖时，应分段总结后再综合。
