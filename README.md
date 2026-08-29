# OpenCode Skills

[opencode](https://opencode.ai) 自定义技能合集。克隆到 `~/.config/opencode/skills/` 后即可在 opencode 中使用，换电脑迁移只需一条命令：

```bash
git clone git@github.com:chalmery/skills.git ~/.config/opencode/skills
```

## 技能列表

### 📈 akshare-stock — A股 + 美股行情分析

基于实测可用数据源（东财/腾讯/新浪）的股票数据查询工具。

- **行情**：A股（`600519`、`000001`）与美股（`QQQ`、`AAPL`）实时价格、K线
- **财务**：财务指标、业绩数据
- **资金流**：个股/板块资金流向
- **龙虎榜**：龙虎榜数据
- **新闻/指数**：市场新闻、指数行情

输出统一为 JSON（`{"ok": bool, "rows": int, "data": [...]}`），由 `scripts/akdata.py` 提供。

**依赖**：`akshare`（`pip3 install --user akshare`）

**触发器**：查股票、股票分析、A股行情、美股行情、查K线、查龙虎榜、查资金流

---

### 🪙 binance-crypto — 加密货币行情

基于币安公开 API 的加密货币数据工具（无需密钥）。

- `price BTC` — 单币实时价格
- `prices` — 全部币种价格（400+ 交易对，支持过滤）
- `ticker BTC` — 24小时统计（涨跌幅/高低点/成交量额）
- `kline BTC daily` — 历史K线（支持区间与周期）
- `depth BTC` — 订单簿深度
- 最近成交记录

由 `scripts/binance.py` 提供，输出统一 JSON。

**依赖**：`requests`

**触发器**：加密货币、币价、BTC行情、币安

---

### 🎬 yt-summary — YouTube 本地转写 + 总结

基于 **yt-dlp + whisper.cpp(Vulkan) + Ollama** 的全本地视频处理流水线，利用 AMD GPU（RX 9070 GRE 已验证）加速转写，**无需 API key、无需上传云端**，支持中文视频自动识别。

```
YouTube URL → yt-dlp(下载音频) → ffmpeg(转16kHz WAV)
            → whisper.cpp Vulkan(GPU转写) → transcript.txt(带时间戳)
            → summarize.py(本地LLM总结) → summary.md
```

**环境要求**：

- `yt-dlp` + `ffmpeg` + `node`
- `whisper.cpp`（Vulkan 编译版，GPU 加速）
- `Ollama`（本地 LLM，`qwen2.5:7b` 已就绪）

**触发器**：总结视频、视频转文字、YouTube 总结、转写

---

## 安装到 opencode

```bash
# 首次（或换新电脑）
git clone git@github.com:chalmery/skills.git ~/.config/opencode/skills

# 更新
cd ~/.config/opencode/skills && git pull
```

克隆后重启 opencode，技能即生效。

## 开发约定

- 每个技能包含 `SKILL.md`（opencode 技能描述，含触发器关键词）与 `scripts/`（可执行脚本）
- 脚本统一输出 JSON：`{"ok": bool, "rows": int, "data": [...]}`
- 数据源均为公开 API，不存储任何密钥
