"""
国内株式 高配当・低PBR・安定スクリーナー（yfinance版・東証プライム全銘柄対応）
JPXから東証プライム上場銘柄リストを動的取得し、全銘柄をスクリーニング
"""

import os, io, json, time, logging
from datetime import datetime
from pathlib import Path
import yfinance as yf
import pandas as pd
import requests

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
log = logging.getLogger(__name__)

FILTERS = {
    "min_yield":        float(os.environ.get("MIN_YIELD",   "2.0")),
    "max_pbr":          float(os.environ.get("MAX_PBR",     "99.0")),
    "min_roe":          float(os.environ.get("MIN_ROE",     "0.0")),
    "min_equity_ratio": float(os.environ.get("MIN_EQUITY",  "0.0")),
    "min_div_years":    int(os.environ.get("MIN_DIV_YEARS", "1")),
    "max_payout_ratio": float(os.environ.get("MAX_PAYOUT",  "99.0")),
}

OUTPUT_PATH = Path("public/data/results.json")

SECTOR_MAP = {
    "Technology":"テクノロジー","Industrials":"産業機械","Consumer Cyclical":"一般消費財",
    "Financial Services":"金融サービス","Healthcare":"医薬品・医療",
    "Communication Services":"通信・メディア","Consumer Defensive":"生活必需品",
    "Basic Materials":"素材・化学","Energy":"エネルギー","Real Estate":"不動産",
    "Utilities":"公益事業","Banks":"銀行業","Insurance":"保険業",
}
FIN_SECTORS = {"Financial Services","Banks","Insurance"}

# ─────────────────────────────────────────
# JPXから東証プライム銘柄リストを取得
# ─────────────────────────────────────────
def fetch_prime_codes():
    """JPXの上場銘柄一覧CSVからプライム市場の4桁コードを取得"""
    url = "https://www.jpx.co.jp/markets/statistics-equities/misc/tvdivq0000001vg2-att/data_j.xls"
    log.info("JPXから東証プライム銘柄リストを取得中...")
    try:
        r = requests.get(url, timeout=30, headers={"User-Agent": "Mozilla/5.0"})
        r.raise_for_status()
        df = pd.read_excel(io.BytesIO(r.content), dtype=str)
        # カラム名を確認して市場区分でフィルター
        log.info(f"カラム: {list(df.columns)}")
        # 市場区分カラムを特定
        mkt_col = next((c for c in df.columns if "市場" in str(c) or "Market" in str(c) or "市場・商品区分" in str(c)), None)
        code_col = next((c for c in df.columns if "コード" in str(c) or "Code" in str(c)), None)
        if mkt_col and code_col:
            prime = df[df[mkt_col].str.contains("プライム", na=False)]
            codes = prime[code_col].str[:4].dropna().unique().tolist()
            codes = [c for c in codes if c.isdigit() and len(c) == 4]
            log.info(f"東証プライム銘柄数: {len(codes)}")
            return sorted(codes)
        else:
            log.warning(f"カラムが見つかりません。フォールバック使用。cols={list(df.columns)[:10]}")
    except Exception as e:
        log.warning(f"JPXリスト取得失敗: {e} → フォールバックリストを使用")
    return get_fallback_codes()

def get_fallback_codes():
    """JPX取得失敗時のフォールバック（主要プライム銘柄）"""
    log.info("フォールバックリストを使用（約300銘柄）")
    # 業種別に幅広くカバー
    codes = []
    # 輸送機器
    codes += ["7203","7267","7201","7202","7205","7211","7261","7269","7270","7272","7282","7296","7731","7733"]
    # 電機・精密
    codes += ["6758","6861","6954","6971","6981","6902","6952","6762","6752","6503","6504","6506","6645","6674","6841","6857","6367","6098","6301","6302","6326","6361","6501","6702","7011","7012","7013","7741"]
    # 情報・通信
    codes += ["9432","9433","9434","4689","3659","4755","2432","3668","4751","6178","9984","4552"]
    # 商社・卸売
    codes += ["8058","8031","8001","8002","8053","8015","9107","2768","8136"]
    # 金融・銀行
    codes += ["8306","8316","8411","8308","8309","8355","8354","8359","8361","8366","8368","8377","8379","8380","8381","8385","8386","8387","8388","8393"]
    # 証券・保険・その他金融
    codes += ["8591","8766","8750","8795","8601","8604","8628","8630","8725","8729","8739","8253","8267"]
    # 不動産
    codes += ["8801","8802","8804","8830","3289","3231","3003","8803","1878","1925","1928","1942"]
    # 建設
    codes += ["1801","1802","1803","1804","1805","1806","1808","1812","1815","1821","1824","1833","1963","6366","1721"]
    # 食品・飲料
    codes += ["2502","2503","2531","2801","2802","2871","2002","2269","2281","2282","2264","2290","2295","2212","2579","2914","2587","2593"]
    # 医薬品
    codes += ["4502","4503","4506","4507","4519","4523","4543","4568","4151","4188","4183","4452","4631","4004","4005","4021","4042","4063","4208"]
    # 素材・化学・鉄鋼
    codes += ["5401","5411","5714","5802","5803","3407","5901","5101","5110","5202","5301","5332","5333","5631","5713","5706","5707","5741","5842"]
    # エネルギー・資源
    codes += ["1605","5020","5019","1662","5021","5001","5002"]
    # 小売
    codes += ["2651","2670","2678","2685","2730","2778","3099","8270","8273","8282","8905","9843","9983","2670","2780","3086","3087","3088","3092","3097","7532","7533","7550","7581","7751","9766"]
    # 公共・インフラ・交通
    codes += ["9001","9005","9006","9008","9009","9020","9021","9022","9041","9044","9045","9048","9064","9101","9104","9531","9532","9706","9726"]
    # サービス・その他
    codes += ["2413","4324","4385","6028","9602","3436","5009","9005","2914","4661","3382","4519","6954"]
    # 重工・機械
    codes += ["7004","7011","7012","7013","6113","6305","6312","6315","6370","6383","6471","6472","6473","7003","7014"]
    return sorted(set(c for c in codes if c.isdigit() and len(c) == 4))

# ─────────────────────────────────────────
# ユーティリティ
# ─────────────────────────────────────────
def safe_float(v, default=0.0):
    try:
        f = float(v)
        return f if f == f else default
    except Exception:
        return default

def nv(v):
    try:
        f = float(v)
        return None if f != f else f
    except Exception:
        return None

def get_div_yield(info, price):
    dy = safe_float(info.get("dividendYield"))
    if 0 < dy <= 1.0:
        val = dy * 100
        if 0 < val <= 10.0: return val
    elif 1.0 < dy <= 10.0:
        return dy
    dr = safe_float(info.get("dividendRate"))
    if dr > 0 and price > 0:
        val = dr / price * 100
        if 0 < val <= 10.0: return val
    tr = safe_float(info.get("trailingAnnualDividendRate"))
    if tr > 0 and price > 0:
        val = tr / price * 100
        if 0 < val <= 10.0: return val
    return 0.0

def count_div_years(divs):
    if divs is None or divs.empty: return 0
    years = sorted(divs.index.year.unique(), reverse=True)
    count = 0
    for yr in range(datetime.today().year, datetime.today().year - 25, -1):
        if yr in years: count += 1
        else: break
    return count

def get_history(t):
    h = {"years":[],"revenue":[],"operatingIncome":[],"eps":[],"dividend":[],"roe":[],"equityRatio":[]}
    try:
        fins = t.financials
        if fins is not None and not fins.empty:
            cols = sorted(fins.columns)[-5:]
            h["years"] = [str(c.year) for c in cols]
            rev_key = next((k for k in fins.index if "Revenue" in k and "Total" in k), None)
            op_key  = next((k for k in fins.index if "Operating" in k and "Income" in k), None)
            eps_key = next((k for k in fins.index if "EPS" in k or "Earnings Per Share" in k), None)
            for c in cols:
                h["revenue"].append(round(nv(fins.loc[rev_key,c])/1e9,1) if rev_key and nv(fins.loc[rev_key,c]) else None)
                h["operatingIncome"].append(round(nv(fins.loc[op_key,c])/1e9,1) if op_key and nv(fins.loc[op_key,c]) else None)
                h["eps"].append(round(nv(fins.loc[eps_key,c]),1) if eps_key and nv(fins.loc[eps_key,c]) else None)
    except Exception: pass
    try:
        divs = t.dividends
        if not divs.empty and h["years"]:
            by_year = divs.groupby(divs.index.year).sum()
            h["dividend"] = [round(float(by_year.get(int(y),0)),1) for y in h["years"]]
    except Exception: pass
    try:
        bs = t.balance_sheet
        if bs is not None and not bs.empty and h["years"]:
            eq_key = next((k for k in bs.index if "Stockholder" in k or "Common Stock Equity" in k), None)
            ta_key = next((k for k in bs.index if "Total Assets" in k), None)
            ni_key = next((k for k in bs.index if "Net Income" in k), None)
            bs_cols = {str(c.year):c for c in bs.columns}
            for y in h["years"]:
                c = bs_cols.get(y)
                if c is None: h["roe"].append(None); h["equityRatio"].append(None); continue
                eq = nv(bs.loc[eq_key,c]) if eq_key else None
                ta = nv(bs.loc[ta_key,c]) if ta_key else None
                h["equityRatio"].append(round(eq/ta*100,1) if eq and ta and ta>0 else None)
                try:
                    f = t.financials
                    fc = {str(col.year):col for col in f.columns}
                    fc2 = fc.get(y)
                    ni = nv(f.loc[ni_key,fc2]) if ni_key and fc2 and ni_key in f.index else None
                except Exception:
                    ni = None
                h["roe"].append(round(ni/eq*100,1) if ni and eq and eq>0 else None)
    except Exception: pass
    return h

def calc_score(s):
    pbr_score = max(0,(2.0-s["pbr"])/2.0*25) if s["pbr"]>0 else 5
    roe_score  = min(s["roe"]/15*20,20) if s["roe"]>0 else 5
    return round(
        min(s["dividendYield"]/6*30,30) + pbr_score + roe_score +
        min(s["continuousDividendYears"]/20*15,15) +
        (10 if s["isFinancial"] else min(s["equityRatio"]/60*10,10))
    )

# ─────────────────────────────────────────
# スクリーニング本体
# ─────────────────────────────────────────
def screen(codes):
    results = []
    skipped_no_price = skipped_no_div = skipped_filter = skipped_error = 0
    total = len(codes)
    log.info(f"スクリーニング開始: {total}銘柄")

    for i, code in enumerate(codes):
        if i % 50 == 0:
            log.info(f"[{i}/{total}] 処理中... ヒット:{len(results)}件")
        try:
            t    = yf.Ticker(f"{code}.T")
            info = t.info

            price = safe_float(info.get("currentPrice") or info.get("regularMarketPrice"))
            if price <= 0: skipped_no_price += 1; continue

            div_yield = get_div_yield(info, price)
            if div_yield <= 0: skipped_no_div += 1; continue

            pbr      = safe_float(info.get("priceToBook"))
            per      = safe_float(info.get("trailingPE"))
            roe      = safe_float(info.get("returnOnEquity")) * 100
            payout   = safe_float(info.get("payoutRatio")) * 100
            div_rate = safe_float(info.get("dividendRate") or info.get("trailingAnnualDividendRate"))
            sector_en= info.get("sector") or ""
            sector   = SECTOR_MAP.get(sector_en, sector_en or "その他")
            name     = (info.get("shortName") or info.get("longName") or code)[:20]
            fin      = sector_en in FIN_SECTORS

            total_assets = safe_float(info.get("totalAssets"))
            book_val     = safe_float(info.get("bookValue"))
            shares       = safe_float(info.get("sharesOutstanding"))
            equity_ratio = (book_val*shares/total_assets*100) if total_assets>0 and book_val>0 and shares>0 else 0

            divs      = t.dividends
            div_years = count_div_years(divs)

            if div_yield  < FILTERS["min_yield"]:      skipped_filter += 1; continue
            if div_years  < FILTERS["min_div_years"]:  skipped_filter += 1; continue

            history = get_history(t)

            row = {
                "code": code, "name": name, "sector": sector,
                "price": round(price),
                "dividendYield": round(div_yield,2),
                "annualDividend": round(div_rate,1),
                "pbr": round(pbr,2), "per": round(per,1),
                "roe": round(roe,1), "equityRatio": round(equity_ratio,1),
                "payoutRatio": round(payout,1),
                "continuousDividendYears": div_years,
                "isFinancial": fin,
                "history": history,
            }
            row["score"] = calc_score(row)
            results.append(row)

        except Exception as e:
            skipped_error += 1
            log.debug(f"{code}: エラー ({e})")
        finally:
            time.sleep(0.3)

    log.info(f"--- 統計 --- 株価なし:{skipped_no_price} 配当なし:{skipped_no_div} フィルター除外:{skipped_filter} エラー:{skipped_error} ヒット:{len(results)}")
    results.sort(key=lambda x: x["score"], reverse=True)
    return results

def main():
    log.info("=== 高配当・低PBR スクリーナー（東証プライム全銘柄版）開始 ===")
    codes   = fetch_prime_codes()
    log.info(f"対象: {len(codes)}銘柄")
    stocks  = screen(codes)
    payload = {
        "updatedAt": datetime.now().strftime("%Y/%m/%d %H:%M JST"),
        "filters": FILTERS, "count": len(stocks), "stocks": stocks,
    }
    OUTPUT_PATH.parent.mkdir(parents=True, exist_ok=True)
    with open(OUTPUT_PATH, "w", encoding="utf-8") as f:
        json.dump(payload, f, ensure_ascii=False, indent=2)
    log.info(f"完了: {len(stocks)}銘柄を {OUTPUT_PATH} に保存")

if __name__ == "__main__":
    main()
