# Binance 加密货币数据

基于币安公开 API 的加密货币行情工具(无需密钥)。所有数据通过 `scripts/binance.py` 获取,输出统一为 JSON(`{"ok": bool, "rows": int, "data": [...]}`)。

## 使用前提

需要 `requests`(一般已装)。脚本纯标准库 + requests,不依赖 akshare。

## 命令清单

脚本位置:`scripts/binance.py`(本 skill 目录下),统一用 `python3` 执行。

```
# 单币实时价格(BTC 自动补全为 BTCUSDT)
python3 scripts/binance.py price BTC

# 全部币种价格(约 400+ 交易对, 支持过滤)
python3 scripts/binance.py prices [-q 关键字] [--max-rows N]

# 24小时统计: 现价/涨跌幅/24h高低/成交量额/成交笔数
python3 scripts/binance.py ticker BTC

# 历史K线(单次最多 1000 根, 可指定区间)
python3 scripts/binance.py kline BTC daily  [--start 20260801] [--end 20260829] [--max-rows 50]
python3 scripts/binance.py kline ETH 1h     [--limit 1000] [--max-rows 100]

# 订单簿深度: 最优买卖价 + 挂单深度总量(默认只输出汇总, --full 展开每档)
python3 scripts/binance.py depth BTC [--limit 5] [--full]

# 最近成交记录(时间正序)
python3 scripts/binance.py trades BTC [--limit 20]
```

## 使用规范

1. **币种代码格式**：可写 `BTC`(自动补全为 `BTCUSDT`)或完整交易对 `BTCUSDT` / `ETHBTC`。默认计价币为 USDT。支持 BTC/USDT 以外的币对如 `BTCETH`、`BNBUSDT`。
2. **K线周期**：`1m/3m/5m/15m/30m/1h/2h/4h/6h/8h/12h/1d/3d/1w/1M`,也接受别名 `daily/weekly/monthly/hourly`。
3. **默认 `--max-rows 50`**：K线默认截取最近 50 根;`prices` 默认全部,量大时建议加 `-q` 或 `--max-rows`。
4. **时间格式**：`--start/--end` 接受 `YYYYMMDD` 或 `YYYY-MM-DD`(按 UTC 计算)。
5. **字段说明**：
   - `price`：`symbol/price`。
   - `ticker`：`last_price/price_change/price_change_pct/high_24h/low_24h/volume_24h/quote_volume_24h/open_price/prev_close/trade_count/time`。
   - `kline`：`open_time/open/high/low/close/volume/close_time/quote_volume/trades`(时间已转本地时区)。
   - `depth`：`best_bid/best_bid_qty/best_ask/best_ask_qty/bid_depth_total/ask_depth_total`,加 `--full` 展开每档买卖盘。
   - `trades`：`time/price/qty/is_buyer_maker`。
6. **数据源与稳定性**：主源 `api.binance.com` 失败自动降级到公共数据镜像 `data-api.binance.vision`(无地区限制),内置重试(3 次/源)。若返回 `"ok": false` 且 msg 含 "HTTP 400 Invalid symbol",说明币种代码错误;网络问题稍后重试即可。
7. **限速注意**：公共 API 限频约 1200 权重/分钟,K线单次最多 1000 根,长区间历史需分段拉取。

## 分析建议

- 快速看盘：`price` → `ticker`(24h 强弱)→ `depth`(盘口支撑压力)。
- 趋势分析：`kline daily`(日线)→ `kline 4h/1h`(短期结构)→ `trades`(盘口活跃度)。
- 多币对比：`prices -q USDT --max-rows 0` 全量快照后按涨跌幅排序。
- 注意：币安为现货撮合价,与合约价格可能存在小幅基差;重大行情时深度数据波动剧烈。
