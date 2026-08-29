#!/usr/bin/env bash
# ============================================================
# yt-summary - YouTube 视频转写脚本（利用 AMD GPU via Vulkan）
# 位置: ~/.config/opencode/skills/yt-summary/scripts/yt-summary.sh
#
# 功能: 下载音频 → 转16kHz WAV → whisper.cpp(GPU)转写 → 输出带时间戳文本
# 依赖: yt-dlp, ffmpeg, node(js-runtime), whisper.cpp(Vulkan 编译)
#
# 用法:
#   yt-summary <YouTube链接> [模型名]
#   模型: tiny | base | small(默认) | medium | large
#
# 输出: <输出目录>/<视频ID>/transcript.txt
# ============================================================
set -euo pipefail

# ---------- 路径配置 ----------
WHISPER_DIR="${WHISPER_DIR:-$HOME/.local/share/yt-summary/whisper.cpp}"
OUT_ROOT="${YT_SUMMARY_OUT:-$HOME/yt-summary}"
MODEL="${2:-small}"
URL="${1:?用法: yt-summary <YouTube链接> [模型名] 例如: yt-summary \"https://youtu.be/xxx\" small}"

WHISPER_BIN="$WHISPER_DIR/build/bin/whisper-cli"
MODEL_FILE="$WHISPER_DIR/models/ggml-$MODEL.bin"
export LD_LIBRARY_PATH="$WHISPER_DIR/build/bin${LD_LIBRARY_PATH:+:$LD_LIBRARY_PATH}"

# ---------- 依赖检查 ----------
check_dep() {
  command -v "$1" >/dev/null 2>&1 || { echo "❌ 缺少依赖: $1 (请先安装)"; return 1; }
}
check_dep yt-dlp || exit 1
check_dep ffmpeg || exit 1
check_dep node || { echo "⚠️  缺少 node，yt-dlp 可能无法下载部分视频"; }
[ -x "$WHISPER_BIN" ] || { echo "❌ whisper-cli 不存在: $WHISPER_BIN"; echo "   请先编译 whisper.cpp (Vulkan):"; echo "   cd $WHISPER_DIR && cmake -B build -DGGML_VULKAN=ON -DCMAKE_BUILD_TYPE=Release -G Ninja && ninja -C build"; exit 1; }
if [ ! -f "$MODEL_FILE" ]; then
  echo "⚠️  模型 ggml-$MODEL.bin 不存在，尝试下载..."
  (cd "$WHISPER_DIR" && ./models/download-ggml-model.sh "$MODEL")
  [ -f "$MODEL_FILE" ] || { echo "❌ 模型下载失败"; exit 1; }
fi

# ---------- 1. 获取视频信息 ----------
echo "==> [1/4] 获取视频信息..."
VIDEO_ID=$(yt-dlp --print "%(id)s" --no-warnings "$URL")
TITLE=$(yt-dlp --print "%(title)s" --no-warnings "$URL")
OUT_DIR="$OUT_ROOT/$VIDEO_ID"
mkdir -p "$OUT_DIR"
echo "    视频: $TITLE"
echo "    输出: $OUT_DIR"

# ---------- 2. 下载音频 ----------
echo "==> [2/4] 下载音频..."
JS_ARG=()
if command -v node >/dev/null 2>&1; then
  JS_ARG=(--js-runtimes "node:$(command -v node)")
fi
yt-dlp -f "bestaudio[ext=m4a]/bestaudio" "${JS_ARG[@]}" \
  -o "$OUT_DIR/audio.%(ext)s" "$URL" --no-warnings 2>&1 | grep -E "Destination|100%" || true
AUDIO_FILE=$(ls "$OUT_DIR"/audio.* 2>/dev/null | head -1 || true)
[ -n "$AUDIO_FILE" ] || { echo "❌ 音频下载失败"; exit 1; }
echo "    音频: $AUDIO_FILE"

# ---------- 3. 转 WAV ----------
echo "==> [3/4] 转换 16kHz WAV..."
ffmpeg -y -i "$AUDIO_FILE" -ar 16000 -ac 1 -c:a pcm_s16le "$OUT_DIR/audio.wav" -loglevel error

# ---------- 4. GPU 转写 ----------
echo "==> [4/4] GPU 转写 ($MODEL 模型) — 利用 AMD Vulkan..."
"$WHISPER_BIN" -m "$MODEL_FILE" -f "$OUT_DIR/audio.wav" \
  -l zh -otxt -of "$OUT_DIR/transcript" --no-prints

echo ""
echo "=============================================="
echo " ✅ 完成！转写文本: $OUT_DIR/transcript.txt"
echo "    标题: $TITLE"
echo "=============================================="
