#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
binance.py - 加密货币数据 CLI（币安公开 API，无需密钥）
数据来自 Binance 公开现货 API，输出统一为 JSON，便于 Agent 解析。

用法:
  python3 binance.py price   BTCUSDT                  # 单币实时价格
  python3 binance.py prices                          # 全部币种价格
  python3 binance.py ticker  BTCUSDT                  # 24小时统计(涨跌幅/高低/量额)
  python3 binance.py kline   BTCUSDT daily --start 20260101                 # 历史K线
  python3 binance.py kline   BTCUSDT 1h  --max-rows 100                      # 分钟/小时K线
  python3 binance.py depth   BTCUSDT --limit 20       # 订单簿深度(买一卖一/买卖盘)
  python3 binance.py trades  BTCUSDT --limit 10       # 最近成交
"""

import argparse
import datetime as dt
import json
import sys
import time
from typing import NoReturn

import requests

# 主源 + 备用镜像(公共数据, 无地区限制)。主源失败自动降级。
HOSTS = ["https://api.binance.com", "https://data-api.binance.vision"]
UA = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)"}

INTERVALS = ["1m", "3m", "5m", "15m", "30m", "1h", "2h", "4h", "6h", "8h", "12h",
             "1d", "3d", "1w", "1M"]
ALIAS = {"daily": "1d", "weekly": "1w", "monthly": "1M", "hourly": "1h"}

_session = requests.Session()


def _api(path, params=None, attempts=3, delay=1.0):
    """请求币安 API: 主源失败自动降级镜像, 内置重试."""
    last: BaseException = ConnectionError("unknown")
    for host in HOSTS:
        for i in range(attempts):
            try:
                r = _session.get(f"{host}{path}", params=params, headers=UA, timeout=15)
                if r.status_code == 200:
                    return r.json()
                last = ValueError(f"HTTP {r.status_code}: {r.text[:200]}")
            except Exception as e:
                last = e
            if i < attempts - 1:
                time.sleep(delay)
    raise last


def _fail(msg) -> NoReturn:
    print(json.dumps({"ok": False, "msg": msg}, ensure_ascii=False))
    sys.exit(1)


def _emit(records, max_rows=None):
    """records(list[dict]) -> stdout, 统一 JSON 输出."""
    if not records:
        _fail("无数据")
    if max_rows and len(records) > max_rows:
        records = records[-max_rows:]
    print(json.dumps({"ok": True, "rows": len(records), "data": records},
                     ensure_ascii=False, default=str))


def _ts2str(ms):
    return dt.datetime.fromtimestamp(ms / 1000).strftime("%Y-%m-%d %H:%M:%S")


_QUOTES = ("USDT", "USDC", "FDUSD", "BUSD", "BTC", "ETH", "BNB", "TRY", "EUR")


def _norm_symbol(symbol):
    """BTC -> BTCUSDT, 已是完整交易对(如 BTCUSDT/ETHBTC)则原样返回."""
    s = symbol.strip().upper()
    for q in _QUOTES:
        if s.endswith(q) and len(s) > len(q):
            return s
    return f"{s}USDT"


def _norm_interval(iv):
    if iv in INTERVALS:
        return iv
    if iv in ALIAS:
        return ALIAS[iv]
    _fail(f"interval 无效: {iv}，可选 {INTERVALS} 或 daily/weekly/monthly/hourly")


def _fmt_date(d):
    """'20260801' / '2026-08-01' -> 毫秒时间戳(UTC)."""
    d = d.replace("-", "")
    return int(dt.datetime.strptime(d, "%Y%m%d").replace(tzinfo=dt.timezone.utc).timestamp() * 1000)


# ---------- 子命令 ----------

def cmd_price(args):
    """单币实时价格."""
    try:
        d = _api("/api/v3/ticker/price", {"symbol": _norm_symbol(args.symbol)})
    except Exception as e:
        _fail(f"price 失败: {e}")
    _emit([{"symbol": d["symbol"], "price": float(d["price"])}])


def cmd_prices(args):
    """全部币种价格(约 400+ 交易对)."""
    try:
        data = _api("/api/v3/ticker/price")
    except Exception as e:
        _fail(f"prices 失败: {e}")
    rows = [{"symbol": d["symbol"], "price": float(d["price"])} for d in data]
    if args.q:
        q = args.q.upper()
        rows = [r for r in rows if q in r["symbol"]]
    _emit(rows, args.max_rows)


def cmd_ticker(args):
    """24小时统计: 涨跌幅/最高最低/成交量额."""
    try:
        d = _api("/api/v3/ticker/24hr", {"symbol": _norm_symbol(args.symbol)})
    except Exception as e:
        _fail(f"ticker 失败: {e}")
    rows = [{
        "symbol": d["symbol"],
        "last_price": float(d["lastPrice"]),
        "price_change": float(d["priceChange"]),
        "price_change_pct": float(d["priceChangePercent"]),
        "high_24h": float(d["highPrice"]),
        "low_24h": float(d["lowPrice"]),
        "volume_24h": float(d["volume"]),
        "quote_volume_24h": float(d["quoteVolume"]),
        "open_price": float(d["openPrice"]),
        "prev_close": float(d["prevClosePrice"]),
        "trade_count": int(d["count"]),
        "time": _ts2str(d["closeTime"]),
    }]
    _emit(rows)


def cmd_kline(args):
    """历史K线. 单次最多 1000 根, 需要更多请分段拉取."""
    symbol = _norm_symbol(args.symbol)
    iv = _norm_interval(args.interval)
    params = {"symbol": symbol, "interval": iv, "limit": min(args.limit, 1000)}
    if args.start:
        params["startTime"] = _fmt_date(args.start)
    if args.end:
        params["endTime"] = _fmt_date(args.end)
    try:
        data = _api("/api/v3/klines", params)
    except Exception as e:
        _fail(f"kline 失败: {e}")
    if not data:
        _fail("kline: 无数据(可能区间过旧或超出可查范围)")
    rows = [{
        "open_time": _ts2str(k[0]),
        "open": float(k[1]),
        "high": float(k[2]),
        "low": float(k[3]),
        "close": float(k[4]),
        "volume": float(k[5]),
        "close_time": _ts2str(k[6]),
        "quote_volume": float(k[7]),
        "trades": int(k[8]),
    } for k in data]
    _emit(rows, args.max_rows)


def cmd_depth(args):
    """订单簿深度: 最优买卖价 + 前 N 档买卖盘."""
    symbol = _norm_symbol(args.symbol)
    try:
        d = _api("/api/v3/depth", {"symbol": symbol, "limit": min(args.limit, 1000)})
    except Exception as e:
        _fail(f"depth 失败: {e}")
    bids, asks = d["bids"], d["asks"]
    summary = {
        "symbol": symbol,
        "best_bid": float(bids[0][0]) if bids else None,
        "best_bid_qty": float(bids[0][1]) if bids else None,
        "best_ask": float(asks[0][0]) if asks else None,
        "best_ask_qty": float(asks[0][1]) if asks else None,
        "bid_depth_total": sum(float(b[1]) for b in bids),
        "ask_depth_total": sum(float(a[1]) for a in asks),
    }
    rows = [summary]
    if args.full:
        rows += [{"side": "bid", "price": float(b[0]), "qty": float(b[1])} for b in bids]
        rows += [{"side": "ask", "price": float(a[0]), "qty": float(a[1])} for a in asks]
    _emit(rows)


def cmd_trades(args):
    """最近成交记录(按时间正序)."""
    symbol = _norm_symbol(args.symbol)
    try:
        data = _api("/api/v3/trades", {"symbol": symbol, "limit": min(args.limit, 1000)})
    except Exception as e:
        _fail(f"trades 失败: {e}")
    rows = [{
        "time": _ts2str(t["time"]),
        "price": float(t["price"]),
        "qty": float(t["qty"]),
        "is_buyer_maker": bool(t["isBuyerMaker"]),
    } for t in data]
    _emit(rows)


# ---------- 入口 ----------

def main():
    p = argparse.ArgumentParser(prog="binance", description="加密货币数据 CLI (币安公开 API)")
    sub = p.add_subparsers(dest="cmd", required=True)

    sp = sub.add_parser("price", help="单币实时价格")
    sp.add_argument("symbol", help="BTC 或 BTCUSDT")

    sp = sub.add_parser("prices", help="全部币种价格")
    sp.add_argument("-q", "--q", default="", help="过滤关键字, 如 USDT")
    sp.add_argument("--max-rows", type=int, default=0, help="最大输出行数(默认全部)")

    sp = sub.add_parser("ticker", help="24小时统计")
    sp.add_argument("symbol")

    sp = sub.add_parser("kline", help="历史K线(单次最多1000根)")
    sp.add_argument("symbol")
    sp.add_argument("interval", help="1m/5m/15m/30m/1h/4h/1d/1w/1M 或 daily/weekly/monthly")
    sp.add_argument("--start", default="", help="起始日期 YYYYMMDD 或 YYYY-MM-DD")
    sp.add_argument("--end", default="", help="结束日期")
    sp.add_argument("--limit", type=int, default=1000, help="单次拉取根数(上限1000)")
    sp.add_argument("--max-rows", type=int, default=50, help="最大输出行数(默认50, 0=全部)")

    sp = sub.add_parser("depth", help="订单簿深度")
    sp.add_argument("symbol")
    sp.add_argument("--limit", type=int, default=5, help="买卖盘档位数(上限1000)")
    sp.add_argument("--full", action="store_true", help="展开输出每档买卖盘")

    sp = sub.add_parser("trades", help="最近成交")
    sp.add_argument("symbol")
    sp.add_argument("--limit", type=int, default=20)

    args = p.parse_args()
    getattr(sys.modules[__name__], f"cmd_{args.cmd}")(args)


if __name__ == "__main__":
    main()
