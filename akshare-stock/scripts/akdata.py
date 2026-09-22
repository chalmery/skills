#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
akdata.py - 股票数据 CLI（仅保留实测可用的接口）
数据来自公开行情接口，输出统一为 JSON，便于 Agent 解析。

用法:
  python3 akdata.py kline   600519 daily --adjust qfq --start 20250101          # A股K线
  python3 akdata.py kline   QQQ daily --start 20250101                          # 美股K线
  python3 akdata.py quote   600519      # A股实时行情(腾讯)
  python3 akdata.py quote   QQQ         # 美股实时行情(腾讯)
  python3 akdata.py spot    --top 20    # 全市场快照(腾讯)
  python3 akdata.py list                # A股股票列表(东财)
  python3 akdata.py financial 600519    # 财务摘要(东财)
  python3 akdata.py fundflow 600519     # 个股资金流(新浪)
  python3 akdata.py lhb     --start 20260101                  # 龙虎榜(东财)
  python3 akdata.py news    600519      # 个股新闻(东财)
  python3 akdata.py index   sh000001    # 指数日线(新浪)
  python3 akdata.py indicator 600519    # 财务分析指标(新浪)
"""

import argparse
import contextlib
import datetime as dt
import io
import json
import re
import sys
import time

import requests

# 东财K线主域名 push2his.eastmoney.com 不通，使用可用的 20 子域
EM_KLINE_HOST = "https://20.push2his.eastmoney.com"
UA = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)"}


def _date_days_ago(days):
    """返回相对今天的 YYYYMMDD 日期，避免默认查询区间随时间失效。"""
    return (dt.date.today() - dt.timedelta(days=days)).strftime("%Y%m%d")


def _quiet(fn):
    """抑制 akshare 内部 tqdm 进度条(stderr), 保证输出干净."""
    with contextlib.redirect_stderr(io.StringIO()):
        return fn()


def _ak(fn, label=""):
    """调用 akshare 接口: 抑制 tqdm 进度条 + 网络重试."""
    return _retry(lambda: _quiet(fn), label=label)


def _retry(fn, attempts=4, delay=2.0, label=""):
    """网络接口重试."""
    last: BaseException = ConnectionError("unknown")
    for i in range(attempts):
        try:
            return fn()
        except Exception as e:
            last = e
            if i < attempts - 1:
                time.sleep(delay)
    raise last


def _emit(df, max_rows=None):
    """DataFrame -> stdout, 统一 JSON 输出."""
    if df is None or len(df) == 0:
        print(json.dumps({"ok": False, "msg": "无数据", "rows": 0}, ensure_ascii=False))
        return
    if max_rows and len(df) > max_rows:
        df = df.tail(max_rows)
    df = df.where(df.notna(), None)
    records = df.to_dict(orient="records")
    print(json.dumps({"ok": True, "rows": len(records), "data": records}, ensure_ascii=False, default=str))


def _fail(msg):
    print(json.dumps({"ok": False, "msg": msg}, ensure_ascii=False))


def _load_ak():
    try:
        import akshare as ak
        return ak
    except ImportError:
        _fail("akshare 未安装，请先执行: pip3 install --user akshare")
        sys.exit(1)


def _is_us(symbol):
    """6位纯数字=A股, 字母=美股(如 QQQ/AAPL/TSLA)."""
    return not re.fullmatch(r"\d{6}", symbol)


def _secid(symbol):
    """转东财 secid: A股 1.xxx(沪)/0.xxx(深), 美股 105.XXX."""
    if _is_us(symbol):
        return f"105.{symbol.upper()}"
    return f"1.{symbol}" if symbol[0] in "569" else f"0.{symbol}"


# ---------- K线 ----------

def _em_kline(symbol, period, start, end, adjust):
    """东财 K线(20.push2his 子域). 支持 A股/美股, 日/周/月/分钟, 复权."""
    klt = {"daily": 101, "weekly": 102, "monthly": 103, "1": 1, "5": 5, "15": 15, "30": 30, "60": 60}[period]
    fqt = {"": 0, "qfq": 1, "hfq": 2}[adjust]
    params = {
        "secid": _secid(symbol),
        "fields1": "f1,f2,f3,f4,f5,f6",
        "fields2": "f51,f52,f53,f54,f55,f56,f57",  # 日期,开,收,高,低,量,额
        "klt": klt, "fqt": fqt,
        "beg": start.replace("-", ""), "end": end.replace("-", ""),
    }
    r = requests.get(f"{EM_KLINE_HOST}/api/qt/stock/kline/get", params=params, headers=UA, timeout=15)
    data = r.json().get("data")
    if not data or not data.get("klines"):
        raise ValueError("东财K线无数据")
    rows = []
    for line in data["klines"]:
        p = line.split(",")
        rows.append({"date": p[0], "open": float(p[1]), "close": float(p[2]),
                     "high": float(p[3]), "low": float(p[4]),
                     "volume": float(p[5]), "amount": float(p[6])})
    import pandas as pd
    return pd.DataFrame(rows)


def _sina_kline(ak, symbol, start, end):
    """新浪日线降级(仅 A股, 前缀 sh/sz)."""
    prefix = "sh" if symbol.startswith(("6", "9", "5")) else "sz"
    df = _ak(lambda: ak.stock_zh_a_daily(
        symbol=f"{prefix}{symbol}",
        start_date=start.replace("-", ""), end_date=end.replace("-", "")), label="新浪K线")
    df = df.rename(columns={"day": "date"})[["date", "open", "high", "low", "close", "volume", "amount"]]
    return df


def _sina_us_kline(symbol, start, end):
    """美股日K(新浪 US_MinKService, 2001年至今, 稳定). 代码小写."""
    url = ("https://stock.finance.sina.com.cn/usstock/api/jsonp.php/"
           f"var%20_=/US_MinKService.getDailyK?symbol={symbol.lower()}")
    r = requests.get(url, headers={**UA, "Referer": "https://finance.sina.com.cn"}, timeout=15)
    text = r.text
    import json as _json
    data = _json.loads(text[text.find("([") + 1: text.rfind("])") + 1])
    import pandas as pd
    df = pd.DataFrame(data)
    df = df.rename(columns={"d": "date", "o": "open", "h": "high", "l": "low",
                            "c": "close", "v": "volume", "a": "amount"})
    for col in ("open", "high", "low", "close", "volume", "amount"):
        df[col] = df[col].astype(float)
    s, e = start.replace("-", ""), end.replace("-", "")
    if s:
        df = df[df["date"].astype(str) >= f"{s[:4]}-{s[4:6]}-{s[6:]}"]
    if e:
        df = df[df["date"].astype(str) <= f"{e[:4]}-{e[4:6]}-{e[6:]}"]
    return df[["date", "open", "high", "low", "close", "volume", "amount"]]


def cmd_kline(ak, args):
    """历史K线: A股=东财(20子域, 失败降级新浪), 美股=新浪(稳定)."""
    try:
        if _is_us(args.symbol):
            df = _retry(lambda: _sina_us_kline(args.symbol, args.start, args.end), label="新浪美股K线")
            _emit(df, args.max_rows)
            return
        try:
            df = _retry(lambda: _em_kline(args.symbol, args.period, args.start, args.end, args.adjust),
                        label="东财K线")
        except Exception:
            df = _sina_kline(ak, args.symbol, args.start, args.end)
        _emit(df, args.max_rows)
    except Exception as e:
        _fail(f"kline 失败: {e}")


# ---------- 实时行情(腾讯, 通) ----------

def _tx_quote_fields(symbol):
    """腾讯 A股实时行情原始字段(仅A股, sh/sz前缀)."""
    code = ("sh" if symbol.startswith(("6", "9", "5")) else "sz") + symbol
    r = requests.get(f"https://qt.gtimg.cn/q={code}", headers=UA, timeout=15)
    r.encoding = "gbk"
    line = r.text.split('"')[1]
    return line.split("~")


def _sina_us_quote_fields(symbol):
    """新浪美股实时行情原始字段(逗号分隔, 稳定). 代码小写."""
    r = requests.get(f"https://hq.sinajs.cn/list=gb_{symbol.lower()}",
                     headers={**UA, "Referer": "https://finance.sina.com.cn"}, timeout=15)
    r.encoding = "gbk"
    return r.text.split('"')[1].split(",")


def cmd_quote(ak, args):
    """单只实时行情: A股=腾讯, 美股=新浪."""
    try:
        if _is_us(args.symbol):
            f = _retry(lambda: _sina_us_quote_fields(args.symbol), label="新浪美股行情")
            if len(f) < 2 or not f[0]:
                _fail(f"quote: 未找到美股 {args.symbol}（新浪代码需小写）")
                return
            items = [
                ("名称", f[0]), ("最新价", f[1]), ("涨跌幅%", f[2]), ("时间", f[3]), ("涨跌额", f[4]),
                ("今开", f[5]), ("最高", f[6]), ("最低", f[7]),
                ("52周最高", f[8]), ("52周最低", f[9]),
                ("成交量", f[10]), ("总市值(美元)", f[12]), ("市盈率", f[14] if f[14] not in ("", "--") else "N/A"),
                ("总股本", f[19]), ("均价", f[21]), ("昨收", f[26]), ("成交额(美元)", f[30]),
            ]
        else:
            f = _retry(lambda: _tx_quote_fields(args.symbol), label="腾讯行情")
            items = [
                ("名称", f[1]), ("代码", f[2]), ("最新价", f[3]), ("昨收", f[4]), ("今开", f[5]),
                ("成交量(手)", f[6]), ("时间", f[30]), ("涨跌", f[31]), ("涨跌幅%", f[32]),
                ("最高", f[33]), ("最低", f[34]), ("换手率%", f[38]), ("市盈率TTM", f[39]),
                ("振幅%", f[43]), ("流通市值(亿)", f[44]), ("总市值(亿)", f[45]),
                ("市净率", f[46]), ("涨停", f[47]), ("跌停", f[48]), ("量比", f[49]),
                ("市盈率(动)", f[52]), ("市盈率(静)", f[53]),
            ]
        import pandas as pd
        df = pd.DataFrame([{"item": k, "value": v} for k, v in items])
        _emit(df)
    except Exception as e:
        _fail(f"quote 失败: {e}")


# ---------- 其余 akshare 接口(实测可用) ----------

def cmd_spot(ak, args):
    """全市场实时快照(腾讯, 稳定). 拼音列名映射为中文, 支持排序过滤."""
    col_map = {
        "code": "代码", "name": "名称", "zxj": "最新价", "zdf": "涨跌幅",
        "zd": "涨跌额", "volume": "成交量", "zdf_d5": "5日涨跌幅", "zdf_d10": "10日涨跌幅",
        "zdf_d20": "20日涨跌幅", "zdf_d60": "60日涨跌幅", "zdf_w52": "52周涨跌幅",
        "zdf_y": "年初至今涨跌幅", "zf": "振幅", "turnover": "换手率",
        "pe_ttm": "市盈率TTM", "pn": "市净率", "ltsz": "流通市值(亿)", "zsz": "总市值(亿)",
        "zljlr": "主力净流入", "zllc": "主力流出", "zllr": "主力流入",
    }
    try:
        df = _ak(lambda: ak.stock_zh_a_spot_tx(), label="腾讯快照")
    except Exception as e:
        _fail(f"spot 失败(腾讯数据源不可用): {e}")
        return
    df = df.rename(columns=col_map)
    sort_map = {"pct_chg": "涨跌幅", "amount": "主力净流入", "volume": "成交量",
                "price": "最新价", "turnover": "换手率"}
    if args.sort in sort_map and sort_map[args.sort] in df.columns:
        df = df.sort_values(sort_map[args.sort], ascending=False)
    if args.top:
        df = df.head(args.top)
    _emit(df)


def cmd_list(ak, args):
    """A股全部股票列表(东财)."""
    try:
        df = _ak(lambda: ak.stock_info_a_code_name(), label="股票列表")
        _emit(df, args.max_rows)
    except Exception as e:
        _fail(f"list 失败: {e}")


def cmd_financial(ak, args):
    """财务摘要(东财)."""
    try:
        df = _ak(lambda: ak.stock_financial_abstract(symbol=args.symbol), label="财务摘要")
        _emit(df, args.max_rows)
    except Exception as e:
        _fail(f"financial 失败: {e}")


def cmd_fundflow(ak, args):
    """个股资金流(新浪, 稳定). 返回全市场即时资金流, 取目标个股."""
    try:
        df = _ak(lambda: ak.stock_fund_flow_individual(symbol="即时"), label="资金流")
        code = args.symbol.zfill(6)
        row = df[df["股票代码"].astype(str).str.zfill(6) == code]
        if len(row) == 0:
            _fail(f"fundflow: 未找到 {args.symbol}，请检查代码")
            return
        _emit(row, args.max_rows)
    except Exception as e:
        _fail(f"fundflow 失败: {e}")


def cmd_lhb(ak, args):
    """龙虎榜(东财)."""
    try:
        df = _ak(lambda: ak.stock_lhb_detail_em(start_date=args.start, end_date=args.end), label="龙虎榜")
        _emit(df, args.max_rows)
    except Exception as e:
        _fail(f"lhb 失败: {e}")


def cmd_news(ak, args):
    """个股新闻(东财财经号)."""
    try:
        df = _ak(lambda: ak.stock_news_em(symbol=args.symbol), label="个股新闻")
        _emit(df, args.max_rows)
    except Exception as e:
        _fail(f"news 失败: {e}")


def cmd_index(ak, args):
    """指数历史日线(新浪). symbol: sh000001 / sz399001 / sz399006."""
    try:
        df = _ak(lambda: ak.stock_zh_index_daily(symbol=args.symbol), label="指数日线")
        if args.start:
            df = df[df["date"].astype(str) >= f"{args.start[:4]}-{args.start[4:6]}-{args.start[6:]}"]
        if args.end:
            df = df[df["date"].astype(str) <= f"{args.end[:4]}-{args.end[4:6]}-{args.end[6:]}"]
        _emit(df, args.max_rows)
    except Exception as e:
        _fail(f"index 失败: {e}")


def cmd_indicator(ak, args):
    """财务分析指标(新浪): 每股收益/净资产/利润率/偿债能力等. 数据正序(老在前)."""
    try:
        df = _ak(lambda: ak.stock_financial_analysis_indicator(symbol=args.symbol), label="财务指标")
        if args.max_rows and len(df) > args.max_rows:
            df = df.tail(args.max_rows)
        _emit(df)
    except Exception as e:
        _fail(f"indicator 失败: {e}")


# ---------- 入口 ----------

def main():
    p = argparse.ArgumentParser(prog="akdata", description="股票数据 CLI (仅保留可用接口, A股+美股)")
    sub = p.add_subparsers(dest="cmd", required=True)

    def add_common(sp):
        sp.add_argument("--max-rows", type=int, default=50, help="最大输出行数(默认50, 0=全部)")

    sp = sub.add_parser("kline", help="历史K线(A股/美股, 东财主源)")
    sp.add_argument("symbol", help="6位数字=A股(600519), 字母=美股(QQQ/AAPL)")
    sp.add_argument("period", choices=["daily", "weekly", "monthly", "1", "5", "15", "30", "60"])
    sp.add_argument("--adjust", choices=["", "qfq", "hfq"], default="qfq", help="复权方式")
    sp.add_argument("--start", default=_date_days_ago(365))
    sp.add_argument("--end", default=_date_days_ago(0))
    add_common(sp)

    sp = sub.add_parser("quote", help="单只实时行情(腾讯, A股/美股)")
    sp.add_argument("symbol", help="6位数字=A股(600519), 字母=美股(QQQ)")
    add_common(sp)

    sp = sub.add_parser("spot", help="全市场实时快照/涨幅榜(腾讯)")
    sp.add_argument("--top", type=int, default=20)
    sp.add_argument("--sort", default="pct_chg", choices=["pct_chg", "amount", "volume", "price", "turnover"])
    add_common(sp)

    sp = sub.add_parser("list", help="A股股票列表(东财)")
    add_common(sp)

    sp = sub.add_parser("financial", help="财务摘要(东财)")
    sp.add_argument("symbol")
    add_common(sp)

    sp = sub.add_parser("fundflow", help="个股资金流(新浪)")
    sp.add_argument("symbol")
    add_common(sp)

    sp = sub.add_parser("lhb", help="龙虎榜(东财)")
    sp.add_argument("--start", default=_date_days_ago(30))
    sp.add_argument("--end", default=_date_days_ago(0))
    add_common(sp)

    sp = sub.add_parser("news", help="个股新闻(东财)")
    sp.add_argument("symbol")
    add_common(sp)

    sp = sub.add_parser("index", help="指数历史日线(新浪)")
    sp.add_argument("symbol", default="sh000001", nargs="?")
    sp.add_argument("--start", default="")
    sp.add_argument("--end", default="")
    add_common(sp)

    sp = sub.add_parser("indicator", help="财务分析指标(新浪)")
    sp.add_argument("symbol")
    add_common(sp)

    args = p.parse_args()
    ak = _load_ak()
    getattr(sys.modules[__name__], f"cmd_{args.cmd}")(ak, args)


if __name__ == "__main__":
    main()
