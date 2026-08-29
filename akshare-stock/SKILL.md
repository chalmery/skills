---
name: akshare-stock
description: "A股+美股股票数据分析工具。基于实测可用的数据源（东财/腾讯/新浪）提供行情、财务、资金流、龙虎榜、新闻、指数等查询能力，支持美股（如 QQQ/AAPL）。触发器：'查股票'、'股票分析'、'A股行情'、'美股行情'、'查K线'、'查龙虎榜'、'查资金流'、'股票数据'。使用方式：调用 scripts/akdata.py 各子命令，输出为 JSON。"
---

# 股票数据分析（A股 + 美股）

基于实测可用接口的股票数据查询工具。所有数据通过 `scripts/akdata.py` 获取，输出统一为 JSON（`{"ok": bool, "rows": int, "data": [...]}`）。

## 使用前提

akshare 已安装（`pip3 install --user akshare`）。若报 `ModuleNotFoundError`，先安装：
```
pip3 install --user akshare
```

## 股票代码格式

- **A股**：6 位纯数字，如 `600519`（茅台）、`000001`（平安银行），脚本自动判断交易所前缀。
- **美股**：字母代码（大小写均可），如 `QQQ`、`AAPL`、`TSLA`。脚本自动转小写调用新浪接口。

## 命令清单

脚本位置：`scripts/akdata.py`（本 skill 目录下），统一用 `python3` 执行。

```
# 历史K线（A股/美股，日/周/月/分钟，支持复权）
#   A股=东财主源（失败自动降级新浪），美股=新浪（稳定，2001年至今全量）
python3 scripts/akdata.py kline <代码> <daily|weekly|monthly|1|5|15|30|60> [--adjust qfq|hfq] [--start 20250101] [--end 20260829] [--max-rows N]

# 单只实时行情（A股=腾讯，美股=新浪，含估值/盘口/52周高低）
python3 scripts/akdata.py quote <代码>        # 如 600519 或 QQQ

# 全市场实时快照/涨幅榜（腾讯，含PE/PB/主力资金）
python3 scripts/akdata.py spot [--top 20] [--sort pct_chg|amount|volume|price|turnover]

# A股全部股票列表（东财）
python3 scripts/akdata.py list [--max-rows N]

# 财务摘要（东财）
python3 scripts/akdata.py financial <代码> [--max-rows N]

# 个股资金流（新浪，含流入/流出/净额，单位亿）
python3 scripts/akdata.py fundflow <代码> [--max-rows N]

# 龙虎榜（东财，按日期区间）
python3 scripts/akdata.py lhb [--start 20250801] [--end 20260829] [--max-rows N]

# 个股新闻（东财）
python3 scripts/akdata.py news <代码> [--max-rows N]

# 指数历史日线（新浪，sh000001上证/sz399001深证/sz399006创业板）
python3 scripts/akdata.py index [sh000001] [--start 20260101] [--end 20260829] [--max-rows N]

# 财务分析指标（新浪，每股收益/ROE/利润率等，正序老→新，取尾部为最新）
python3 scripts/akdata.py indicator <代码> [--max-rows N]
```

## 使用规范

1. **代码格式**：A股用 6 位数字，美股用字母（`QQQ`/`AAPL`）。K线/行情命令自动识别 A股/美股。
2. **默认 `--max-rows 50`**：K线/列表/财务等大结果默认截取最近 50 条，需要更多时传 `--max-rows 0`（全部）或更大值。
3. **字段说明**：
   - `kline`：`date/open/high/low/close/volume/amount` 标准 K线字段。注意：A股（东财源）`volume` 单位是**股**，美股（新浪源）同。
   - `quote`：`item/value` 两列。A股含现价/涨跌幅/市盈率TTM/市净率/市值/涨停跌停等；美股含现价/涨跌幅/52周高低/总市值/市盈率等（ETF 如 QQQ 市盈率为 N/A）。
   - `spot`：列名为中文，`最新价/涨跌幅/市盈率TTM/市净率/主力净流入/总市值(亿)` 等；代码带 `sh/sz` 前缀（如 `sh600519`）。
   - `lhb`：含代码/名称/上榜日/解读/涨跌幅/换手率等。
   - `news`：含新闻标题/内容/发布时间/文章来源/新闻链接。
4. **数据源与稳定性**（2026-08-29 实测）：
   - **可用**：东财（K线走 20.push2his 子域、列表/财务/龙虎榜/新闻）、腾讯（实时行情/全市场快照）、新浪（K线降级/美股日K/美股行情/资金流/指数/财务指标）。
   - **不可用**：雪球（需登录 token）、东财 K线主域 push2his（网络不通，脚本已自动改用可用子域）。
   - 脚本内置重试（默认 4 次，间隔 2 秒）；A股 K线东财失败自动降级新浪。若返回 `"ok": false` 且 msg 含 "失败"，可稍后重试一次。
5. **分析建议**：
   - 分析单只 A股：`quote`（实时+估值）→ `kline`（走势）→ `financial` 或 `indicator`（财务）→ `fundflow`（资金）→ `news`（消息面）。
   - 分析美股：`quote QQQ`（实时+52周高低）→ `kline QQQ daily`（历史走势，2001年至今）。
   - 分析市场情绪：`spot --sort pct_chg --top 20`（涨幅榜）+ `lhb`（游资/机构动向）。
   - 对比大盘：`index sh000001`（上证）配合个股 K线判断相对强弱。
