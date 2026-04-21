"""
国内株式 高配当・低PBR・安定スクリーナー（yfinance版・改善版）
"""

import os, json, time, logging
from datetime import datetime
from pathlib import Path
import yfinance as yf

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
log = logging.getLogger(__name__)

FILTERS = {
    "min_yield":        float(os.environ.get("MIN_YIELD",   "2.5")),
    "max_pbr":          float(os.environ.get("MAX_PBR",     "1.2")),
    "min_roe":          float(os.environ.get("MIN_ROE",     "3.0")),
    "min_equity_ratio": float(os.environ.get("MIN_EQUITY",  "20.0")),
    "min_div_years":    int(os.environ.get("MIN_DIV_YEARS", "2")),
    "max_payout_ratio": float(os.environ.get("MAX_PAYOUT",  "85.0")),
}

OUTPUT_PATH = Path("public/data/results.json")

CODES = [
    "7203","6758","9432","9984","8306","6861","7974","9433","6367","4063",
    "9022","8316","9020","6098","8035","4519","2914","6501","7267","6702",
    "8058","8031","7741","4543","9021","8411","6954","3382","4661","8002",
    "8053","8001","9107","8591","8766","8750","8601","8308","8309","8253",
    "9434","4689","3659","4188","4183","3407","4004","5401","5411","5802",
    "1605","5020","8830","3289","8801","8802","1801","1802","6301","6302",
    "6326","6503","6645","6752","6762","6902","6952","6971","6981","7011",
    "7731","7201","7202","7261","7269","7270","2002","2503","2531","2802",
    "4502","4503","4523","4568","2651","8267","9843","9983","7751","9101",
    "9104","9531","5714","5803","4452","9005","9006","9041","9044","1928",
    "2413","4324","6178","9602","3436","4042","5009","5101","5202","5301",
    "5332","6113","8355","2768","9064","2432","4755","6028","3231","8795",
    "7186","7004","7012","7013","6504","6506","6841","6857","6674","7733",
    "7762","7205","7211","7272","2269","2281","2282","2502","2801","2871",
    "4506","4507","2670","2678","2685","2730","2778","3099","8270","8273",
    "8282","8905","9726","9706","9532","4385","6366","1963","1721","9064",
]
CODES = sorted(set(c for c in CODES if c.isdigit() and len(c) == 4))

SECTOR_MAP = {
    "Technology":"テクノロジー","Industrials":"産業機械","Consumer Cyclical":"一般消費財",
    "Financial Services":"金融サービス","Healthcare":"医薬品・医療",
    "Communication Services":"通信・メディア","Consumer Defensive":"生活必需品",
    "Basic Materials":"素材・化学","Energy":"エネルギー","Real Estate":"不動産",
    "Utilities":"公益事業","Banks":"銀行業","Insurance":"保険業",
}
FIN_SECTORS = {"Financial Services","Banks","Insurance"}

def safe_float(v, default=0.0):
    try:
        f = float(v)
        return f if f == f else default
    except Exception:
        return default

def count_div_years(ticker_obj):
    try:
        divs = ticker_obj.dividends
        if divs.empty:
            return 0
        years = sorted(divs.index.year.unique(), reverse=True)
        count = 0
        for yr in range(datetime.today().year, datetime.today().year - 25, -1):
            if yr in years:
                count += 1
            else:
                break
        return count
    except Exception:
        return 0

def calc_score(s):
    return round(
        min(s["dividendYield"] / 6 * 30, 30) +
        max(0, (1.5 - s["pbr"]) / 1.5 * 25) +
        min(s["roe"] / 15 * 20, 20) +
        min(s["continuousDividendYears"] / 20 * 15, 15) +
        (10 if s["isFinancial"] else min(s["equityRatio"] / 60 * 10, 10))
    )

def screen():
    results = []
    total = len(CODES)
    log.info(f"対象銘柄数: {total}")

    for i, code in enumerate(CODES):
        if i % 20 == 0:
            log.info(f"[{i}/{total}] 処理中...")
        try:
            t    = yf.Ticker(f"{code}.T")
            info = t.info

            price = safe_float(info.get("currentPrice") or info.get("regularMarketPrice"))
            if price <= 0:
                continue

            pbr       = safe_float(info.get("priceToBook"))
            per       = safe_float(info.get("trailingPE"))
            roe       = safe_float(info.get("returnOnEquity")) * 100
            payout    = safe_float(info.get("payoutRatio")) * 100
            div_rate  = safe_float(info.get("dividendRate"))
            sector_en = info.get("sector") or ""
            sector    = SECTOR_MAP.get(sector_en, sector_en or "その他")
            name      = (info.get("shortName") or info.get("longName") or code)[:20]
            fin       = sector_en in FIN_SECTORS

            # 配当利回り（yfinanceは小数で返す: 0.04 = 4%）
            dy_raw = safe_float(info.get("dividendYield"))
            if dy_raw <= 0:
                # dividendRate と price から計算
                if div_rate > 0 and price > 0:
                    div_yield = div_rate / price * 100
                else:
                    continue
            elif dy_raw > 1.0:
                div_yield = dy_raw        # すでに%表示
            else:
                div_yield = dy_raw * 100  # 小数→%変換

            # 異常値除外
            if div_yield > 20.0 or div_yield <= 0:
                continue

            # 自己資本比率（概算）
            total_assets = safe_float(info.get("totalAssets"))
            book_val     = safe_float(info.get("bookValue"))
            shares       = safe_float(info.get("sharesOutstanding"))
            equity_ratio = (book_val * shares / total_assets * 100) if total_assets > 0 else 0

            if pbr <= 0 or roe == 0:
                continue

            div_years = count_div_years(t)

            # フィルター
            if div_yield  < FILTERS["min_yield"]:                     continue
            if pbr        > FILTERS["max_pbr"]:                       continue
            if roe        < FILTERS["min_roe"]:                       continue
            if not fin and equity_ratio < FILTERS["min_equity_ratio"]: continue
            if div_years  < FILTERS["min_div_years"]:                 continue
            if payout > 0 and payout > FILTERS["max_payout_ratio"]:   continue
            if per > 0 and per > 35:                                  continue

            row = {
                "code":                  code,
                "name":                  name,
                "sector":                sector,
                "price":                 round(price),
                "dividendYield":         round(div_yield, 2),
                "annualDividend":        round(div_rate, 1),
                "pbr":                   round(pbr, 2),
                "per":                   round(per, 1),
                "roe":                   round(roe, 1),
                "equityRatio":           round(equity_ratio, 1),
                "payoutRatio":           round(payout, 1),
                "continuousDividendYears": div_years,
                "isFinancial":           fin,
            }
            row["score"] = calc_score(row)
            results.append(row)
            log.info(f"  ✓ {code} {name[:12]:12s} 利回り:{div_yield:.1f}% PBR:{pbr:.2f} スコア:{row['score']}")

        except Exception as e:
            log.debug(f"{code}: スキップ ({e})")
        finally:
            time.sleep(0.4)

    results.sort(key=lambda x: x["score"], reverse=True)
    log.info(f"\n=== 完了: {len(results)} 銘柄ヒット ===")
    return results

def main():
    log.info("=== 高配当・低PBR スクリーナー 開始 ===")
    stocks  = screen()
    payload = {
        "updatedAt": datetime.now().strftime("%Y/%m/%d %H:%M JST"),
        "filters":   FILTERS,
        "count":     len(stocks),
        "stocks":    stocks,
    }
    OUTPUT_PATH.parent.mkdir(parents=True, exist_ok=True)
    with open(OUTPUT_PATH, "w", encoding="utf-8") as f:
        json.dump(payload, f, ensure_ascii=False, indent=2)
    log.info(f"結果を {OUTPUT_PATH} に保存（{len(stocks)}銘柄）")

if __name__ == "__main__":
    main()
