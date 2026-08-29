---
name: yt-summary
description: "YouTube 视频本地转写+总结工具。基于 yt-dlp + whisper.cpp(Vulkan) 利用 AMD GPU 加速，全本地运行（无需 API key）。触发器：'总结视频'、'视频转文字'、'YouTube 总结'、'转写'、'yt-summary'、'youtube 视频总结'、'下载视频转文字'。使用方式：调用 scripts/yt-summary.sh 下载转写，scripts/summarize.py 总结。"
---

# YouTube 视频本地转写 + 总结

基于 **yt-dlp + whisper.cpp(Vulkan) + Ollama** 的全本地流水线，利用 AMD GPU（RX 9070 GRE 已验证）做 Whisper 加速转写，无需任何 API key、无需上传云端。支持中文视频自动识别。

## 架构

```
YouTube URL → yt-dlp(下载音频) → ffmpeg(转16kHz WAV) → whisper.cpp Vulkan(GPU转写)
                → transcript.txt(带时间戳) → summarize.py(本地LLM总结) → summary.md
```

## 环境要求

- **yt-dlp**（下载音频，需可访问 YouTube）
- **ffmpeg**（音频格式转换）
- **node**（yt-dlp 的 JS runtime，解决部分视频 403/签名解密问题）
- **whisper.cpp**（Vulkan 编译版，GPU 加速）— 已安装在 `~/.local/share/yt-summary/whisper.cpp`
- **Ollama**（本地 LLM 总结，ROCm 加速，服务已开机自启）— `qwen2.5:7b` 模型已就绪

## 使用步骤

### 1. 转写视频（核心命令）

```bash
bash ~/.config/opencode/skills/yt-summary/scripts/yt-summary.sh "<YouTube链接>" [模型名]
```

- 模型可选：`tiny` | `base` | `small`(默认) | `medium` | `large`
- **small 模型**：质量/速度平衡，22 分钟中文视频约 2 分钟转写完成
- **medium 模型**：中文更准，速度约为 small 的 1/4
- 输出：`~/yt-summary/<视频ID>/transcript.txt`（带时间戳）

### 2. 总结转写文本

```bash
# 方式 A：本地 Ollama 总结（推荐，完全离线）
python3 ~/.config/opencode/skills/yt-summary/scripts/summarize.py ~/yt-summary/<视频ID>/transcript.txt

# 方式 B：只生成提示词，粘贴给任意 AI（无 Ollama 时）
python3 ~/.config/opencode/skills/yt-summary/scripts/summarize.py ~/yt-summary/<视频ID>/transcript.txt --prompt-only
```

输出：`transcript_summary.md`

### 3. 一步到位（转写+总结）

```bash
yt_summary_pipeline() {
  bash ~/.config/opencode/skills/yt-summary/scripts/yt-summary.sh "$1" "${2:-small}"
  local id
  id=$(yt-dlp --print "%(id)s" --no-warnings "$1")
  python3 ~/.config/opencode/skills/yt-summary/scripts/summarize.py ~/yt-summary/"$id"/transcript.txt
}
```

## 常见问题

1. **视频下载 403 / 需要 JS runtime**：脚本已自动带上 `--js-runtimes node`，确保 node 已安装。
2. **libwhisper.so.1 找不到**：脚本内已设置 `LD_LIBRARY_PATH` 指向 `build/bin`。
3. **GPU 未识别**：运行 `vulkaninfo --summary` 检查 Vulkan 驱动（Mesa radv）。若报 `glslc`/`SPIRV-Headers` 缺失，需安装：
   ```
   pkexec dnf install -y vulkan-devel glslc spirv-headers-devel
   ```
4. **模型未下载**：脚本会自动触发 `models/download-ggml-model.sh`。
5. **无字幕视频**：whisper 直接转写音频，不依赖 YouTube 字幕，中文准确度高。
6. **长视频（>1小时）**：转写时间随时长线性增长，建议用 small 模型；如遇上下文超限，summarize.py 会自动截断（默认 60000 字符，可用环境变量 `YT_SUMMARY_MAX_CHARS` 调整）。

## 已装组件清单

| 组件 | 位置 | 说明 |
|---|---|---|
| whisper.cpp (Vulkan) | `~/.local/share/yt-summary/whisper.cpp` | 编译产物含 `build/bin/whisper-cli` |
| small 模型 | `~/.local/share/yt-summary/whisper.cpp/models/ggml-small.bin` | 466MB，中文友好 |
| 转写脚本 | `scripts/yt-summary.sh` | 下载→转写 一键完成 |
| 总结脚本 | `scripts/summarize.py` | Ollama 本地总结（qwen2.5:7b 已装）/ 提示词模式 |
| Ollama | 系统服务（开机自启） | ROCm 加速 AMD GPU，模型存于 `/var/lib/ollama/.ollama/models` |
| 转写结果示例 | `~/yt-summary/NfcbziRSqfs/transcript.txt` | 示例视频（方脸说：通缩时代） |

## 注意事项

- 本工具仅用于个人学习、研究用途。请尊重视频版权，勿将转写内容用于商业用途。
- 转写文本由 Whisper 自动生成，可能存在同音字/专有名词误差，总结时请注意核对。
- `/tmp` 是内存盘（tmpfs），**所有工具文件已迁移至 `~/.local/share/yt-summary/`**，重启不丢失。
