---
name: akshare-stock
description: 查询和分析 A 股与美股的行情、K 线、估值、财务、资金流、龙虎榜、新闻和指数数据。当用户要求股票数据或基于这些数据分析个股与市场时使用；不用于交易执行、账户管理或其他市场品种。
---

# A 股与美股数据分析

使用 `scripts/akdata.py` 从公开数据源获取股票数据，成功时统一输出 JSON。它适合查询和研究，不负责下单，也不保证任何第三方接口永久可用。

## 执行原则

1. 根据本 `SKILL.md` 的实际路径确定 Skill 目录，不要假设当前工作目录，也不要写死 OpenCode 或 Codex 的安装路径。
2. 在做行情或投资分析前先运行所需查询，标注数据时间、代码和数据源；查询失败时不要用记忆或旧结果替代实时数据。
3. 只调用回答问题所需的子命令，避免无目的地拉取全市场或全历史数据。
4. 区分原始数据、计算结果和判断。涉及投资观点时说明不确定性，不把分析写成收益承诺。
5. 缺少依赖时先说明需要安装 `requests` 和 `akshare`；不要在未获得授权时擅自修改用户环境。

以下示例中的 `SKILL_DIR` 表示本文件所在目录：

```bash
SKILL_DIR="<akshare-stock 的实际目录>"

# A 股或美股历史 K 线
python3 "$SKILL_DIR/scripts/akdata.py" kline 600519 daily --adjust qfq --max-rows 60
python3 "$SKILL_DIR/scripts/akdata.py" kline QQQ daily --start 20250101 --max-rows 60

# 单只实时行情
python3 "$SKILL_DIR/scripts/akdata.py" quote 600519
python3 "$SKILL_DIR/scripts/akdata.py" quote QQQ

# A 股全市场快照、股票列表和指数
python3 "$SKILL_DIR/scripts/akdata.py" spot --sort pct_chg --top 20
python3 "$SKILL_DIR/scripts/akdata.py" list --max-rows 50
python3 "$SKILL_DIR/scripts/akdata.py" index sh000001 --max-rows 60

# 财务、资金流、龙虎榜和新闻
python3 "$SKILL_DIR/scripts/akdata.py" financial 600519 --max-rows 20
python3 "$SKILL_DIR/scripts/akdata.py" indicator 600519 --max-rows 20
python3 "$SKILL_DIR/scripts/akdata.py" fundflow 600519
python3 "$SKILL_DIR/scripts/akdata.py" lhb --max-rows 50
python3 "$SKILL_DIR/scripts/akdata.py" news 600519 --max-rows 20
```

## 代码与参数

- A 股使用 6 位数字，如 `600519`、`000001`；美股使用字母代码，如 `QQQ`、`AAPL`。
- K 线周期支持 `daily/weekly/monthly/1/5/15/30/60`；分钟周期和复权能力受上游接口限制。
- `--adjust` 支持 `qfq`、`hfq` 或空值，默认为前复权。
- `--max-rows 0` 表示不截断。除非用户明确需要，优先保留默认上限，避免把大量 JSON 塞进上下文。
- 成功输出为 `{"ok": true, "rows": N, "data": [...]}`；失败输出为 `{"ok": false, "msg": "..."}`。

## 数据源与降级

- A 股 K 线优先使用东财接口，失败时尝试新浪；A 股实时行情和市场快照使用腾讯。
- 美股日 K 与实时行情使用新浪接口。
- 财务、资金流、龙虎榜、新闻与指数由脚本中对应的东财、腾讯或新浪接口提供。
- 第三方字段、访问限制和可用性可能变化。若结果为空、字段缺失或多次请求失败，应把它作为数据源问题报告，而不是据此推导市场结论。

常见分析顺序可以是“实时行情 → K 线 → 财务/指标 → 资金流 → 新闻”，但应根据用户的问题裁剪，不必机械执行全部步骤。
