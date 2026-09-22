# 我的自用 Skills

这是我为自己的日常任务维护的一组 Agent Skills，主要服务于行情查询、资料分析和本地视频处理。它们带有明显的个人环境偏好，不以通用产品或公共技能市场为目标；如果你的系统、数据源或工作流不同，请先阅读对应的 `SKILL.md` 再使用。

每个技能都是一个独立目录，至少包含 `SKILL.md`，需要稳定执行的操作放在 `scripts/` 中。目前同时兼容 Codex 和 OpenCode。

## 技能列表

| Skill | 用途 | 主要依赖 |
| --- | --- | --- |
| `akshare-stock` | 查询 A 股和美股的行情、K 线、财务、资金流、龙虎榜、新闻与指数数据 | Python、`requests`、`akshare` |
| `binance-crypto` | 查询 Binance 现货价格、24 小时统计、K 线、深度和最近成交 | Python、`requests` |
| `yt-summary` | 下载 YouTube 音频，在本机用 whisper.cpp 转写，并可用 Ollama 总结 | `yt-dlp`、FFmpeg、whisper.cpp；Ollama 可选 |

行情类脚本统一输出 JSON：

```json
{"ok": true, "rows": 1, "data": []}
```

数据接口和第三方网站可能变化；脚本返回失败时，不应把旧数据或推测当成实时结果。所有行情内容只用于个人研究，不构成投资建议。

## 在 Codex 中使用

Codex 仍然支持 Skills。Skills 是可复用工作流的编写格式；Plugins 是需要跨用户分发、组合多个 Skills 或附带 MCP 连接时更合适的安装单元。这个仓库以个人自用为主，直接使用独立 Skills 即可，不必先改造成 Plugin。具体加载规则可参考 [OpenAI 官方 Skills 文档](https://developers.openai.com/zh-Hans/docs/build-skills)。

### 方式一：让 Skill Installer 安装

在 Codex 中调用内置安装器，并把仓库地址和要安装的技能告诉它：

```text
$skill-installer 请从 https://github.com/chalmery/skills.git 安装 akshare-stock、binance-crypto 和 yt-summary
```

### 方式二：手动安装或软链接

Codex 当前的用户级技能目录是 `~/.agents/skills`。为了让仓库仍可直接 `git pull` 更新，可以把仓库放在固定位置，再把每个技能目录软链接过去：

```bash
git clone https://github.com/chalmery/skills.git ~/.local/share/chalmery-skills
mkdir -p ~/.agents/skills
ln -s ~/.local/share/chalmery-skills/akshare-stock ~/.agents/skills/akshare-stock
ln -s ~/.local/share/chalmery-skills/binance-crypto ~/.agents/skills/binance-crypto
ln -s ~/.local/share/chalmery-skills/yt-summary ~/.agents/skills/yt-summary
```

更新仓库：

```bash
git -C ~/.local/share/chalmery-skills pull --ff-only
```

Codex 通常会自动发现变更；如果没有出现，重启 Codex。在 Codex CLI 或 IDE 扩展中可运行 `/skills` 查看，或在提示词里用 `$akshare-stock`、`$binance-crypto`、`$yt-summary` 显式调用。描述与用户请求匹配时，Codex 也可以自动选择技能。

如果只想让某个项目使用，把技能目录放到该仓库的 `.agents/skills/` 下即可。

## 在 OpenCode 中使用

首次安装：

```bash
git clone https://github.com/chalmery/skills.git ~/.config/opencode/skills
```

更新：

```bash
git -C ~/.config/opencode/skills pull --ff-only
```

安装或更新后重启 OpenCode。

## 本地环境说明

- `yt-summary` 默认从 `~/.local/share/yt-summary/whisper.cpp` 查找 whisper.cpp，可用 `WHISPER_DIR` 覆盖；输出目录默认为 `~/yt-summary`，可用 `YT_SUMMARY_OUT` 覆盖。
- `yt-summary` 的音频会从 YouTube 下载，但转写和默认的 Ollama 总结在本机执行，不会主动上传到第三方模型服务。首次缺少 Whisper 模型时，脚本会尝试下载模型。
- `akshare-stock` 和 `binance-crypto` 依赖公开网络接口，结果的新鲜度与可用性取决于上游数据源。
- 仓库不保存 API Key 或账户凭据，也不包含下单、交易或账户操作。

## 维护约定

- 一个 Skill 只负责一类明确任务，`description` 用于准确匹配，而不是堆叠关键词。
- `SKILL.md` 不绑定某个 Agent 的固定安装路径；执行脚本时根据当前 Skill 的实际目录定位 `scripts/`。
- 仅在重复逻辑需要确定性执行时使用脚本；分析和表达方式留给 Agent 根据当前问题决定。
- 修改后运行语法检查和 Codex Skill 校验，避免提交缺少 frontmatter 或无法执行的脚本。
