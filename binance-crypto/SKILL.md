---
name: binance-crypto
description: 查询和分析 Binance 公开现货市场数据，包括实时价格、24 小时统计、K 线、订单簿与最近成交。当用户询问币价、BTC/ETH 等现货行情或需要基于 Binance 数据做市场分析时使用；不用于账户、合约或下单操作。
---

# Binance 现货市场数据

使用 `scripts/binance.py` 查询 Binance 公开现货 API，无需 API Key。脚本输出统一 JSON，适合继续计算或整理成自然语言结论。

## 执行原则

1. 根据本 `SKILL.md` 的实际路径确定 Skill 目录，不要假设当前工作目录，也不要写死 OpenCode 或 Codex 的安装路径。
2. 只查询回答当前问题所需的数据。分析行情时优先获取最新数据；调用失败就说明失败原因，不要用记忆中的价格冒充实时结果。
3. 在回答中写清交易对、数据时间和数据范围。用户只写 `BTC` 时，脚本默认查询 `BTCUSDT`。
4. 把市场分析与事实数据分开表达，不给出确定收益承诺。此 Skill 不读取账户、不访问私钥，也不执行交易。

以下示例中的 `SKILL_DIR` 表示本文件所在目录：

```bash
SKILL_DIR="<binance-crypto 的实际目录>"

# 单币实时价格
python3 "$SKILL_DIR/scripts/binance.py" price BTC

# 24 小时涨跌、高低点、成交量与成交额
python3 "$SKILL_DIR/scripts/binance.py" ticker BTC

# 历史 K 线；单次最多 1000 根
python3 "$SKILL_DIR/scripts/binance.py" kline BTC daily --max-rows 50
python3 "$SKILL_DIR/scripts/binance.py" kline ETH 4h --start 2026-01-01 --max-rows 100

# 订单簿汇总；--full 展开每一档
python3 "$SKILL_DIR/scripts/binance.py" depth BTC --limit 20

# 最近成交
python3 "$SKILL_DIR/scripts/binance.py" trades BTC --limit 20

# 全部现货交易对价格，可按关键字过滤
python3 "$SKILL_DIR/scripts/binance.py" prices -q USDT --max-rows 100
```

## 参数与输出

- 交易对可写基础币种 `BTC`，或完整交易对 `BTCUSDT`、`ETHBTC`。基础币种默认补全为 `USDT` 交易对。
- K 线周期支持 `1m/3m/5m/15m/30m/1h/2h/4h/6h/8h/12h/1d/3d/1w/1M`，也接受 `hourly/daily/weekly/monthly`。
- `--start` 和 `--end` 接受 `YYYYMMDD` 或 `YYYY-MM-DD`，按 UTC 解析。
- 成功输出为 `{"ok": true, "rows": N, "data": [...]}`；失败输出为 `{"ok": false, "msg": "..."}`，同时使用非零退出码。
- K 线时间会转换为运行机器的本地时区。回答跨时区问题时，应显式说明这一点。

## 数据源边界

脚本先访问 `api.binance.com`，失败时尝试 Binance 的公共数据端点 `data-api.binance.vision`，并对每个端点做有限重试。公共 API 的可用性、地区限制、交易对数量和限频规则都可能变化；不要在 Skill 文档中把某个固定数量或限频值当作长期保证。
