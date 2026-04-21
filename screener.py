
"""
国内株式 高配当・低PBR・安定スクリーナー（yfinance版・完全無料）
Yahoo Finance からデータ取得 - APIキー不要

必要な環境変数: なし（完全無料）
"""

import json
import time
import logging
from datetime import datetime
from pathlib import Path

import yfinance as yf
import pandas as pd

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
log = logging.getLogger(__name__)

# ─────────────────────────────────────────
# スクリーニング条件
# ─────────────────────────────────────────
import os
FILTERS = {
    "min_yield":        float(os.environ.get("MIN_YIELD",   "3.5")),
    "max_pbr":          float(os.environ.get("MAX_PBR",     "1.0")),
    "min_roe":          float(os.environ.get("MIN_ROE",     "5.0")),
    "min_equity_ratio": float(os.environ.get("MIN_EQUITY",  "25.0")),
    "min_div_years":    int(os.environ.get("MIN_DIV_YEARS", "3")),
    "max_payout_ratio": float(os.environ.get("MAX_PAYOUT",  "80.0")),
}

OUTPUT_PATH = Path("public/data/results.json")

# ─────────────────────────────────────────
# 対象銘柄リスト（TOPIX100 + 主要高配当株）
# ─────────────────────────────────────────
CODES = [
    # TOPIX Core30
    "7203","6758","9432","9984","8306","6861","7974","9433","6367","4063",
    "9022","8316","9020","6098","8035","4519","2914","6501","7267","6702",
    "8058","8031","7741","4543","9021","8411","6954","3382","4661","8002",
    # 商社・卸売
    "8053","8001","9470","2768","8015","9107",
    # 金融・保険・銀行
    "8591","8766","8750","8795","8601","7186","8308","8309","8355","8253",
    # 通信・IT
    "9434","4689","3659","4755","2432",
    # 素材・化学
    "4188","4183","3407","4004","4005","4021","4208",
    # 鉄鋼・非鉄
    "5401","5411","5714","5802","5803","5901",
    # エネルギー・資源
    "1605","5020","5019","1662",
    # 不動産
    "8830","3289","8801","8802","8804","3231",
    # 建設・インフラ
    "1801","1802","1803","1721","1963","6366",
    # 電機・機械
    "6301","6302","6326","6361","6503","6504","6506","6645","6674","6752",
    "6753","6762","6770","6841","6857","6902","6952","6971","6981","7004",
    "7011","7012","7013","7731","7733","7762",
    # 自動車・輸送機器
    "7201","7202","7205","7211","7261","7269","7270","7272",
    # 食品・飲料
    "2002","2269","2281","2282","2502","2503","2531","2801","2802","2871",
    # 医薬品
    "4502","4503","4506","4507","4523","4568",
    # 小売
    "2651","2670","2678","2685","2730","2778","3099","8267","8270","8273",
    "8282","8905","9843","9983",
    # サービス・その他
    "2413","4324","4385","6028","6178","7751","7752","9602","9681","9726",
    # 高配当で有名な銘柄
    "1928","3436","4042","4452","4631","5009","5021","5101","5110","5202",
    "5301","5332","5333","5631","6113","6盤","7313","7762","8053","9005",
    "9006","9008","9009","9041","9044","9045","9048","9064","9101","9104",
    "9706","9531","9532",
]

# 重複除去・無効コード除去
CODES = sorted(set(c for c in CODES if c.isdigit() and len(c) == 4))

FINANCIAL_SECTORS = {
    "Financial Services","Banks","Insurance",
    "銀行","証券","金融","保険"
}

SECTOR_MAP_JA = {
    "Technology": "テクノロジー", "Industrials": "産業機械", "Consumer Cyclical": "一般消費財",
    "Financial Services": "金融サービス", "Healthcare": "医薬品・医療", "Communication Services": "通信・メディア",
    "Consumer Defensive": "生活必需品", "Basic Materials": "素材・化学", "Energy": "エネルギー",
    "Real Estate": "不動産", "Utilities": "公益事業", "Banks": "銀行業", "Insurance": "保険業",
}

def is_financial(sector):
    return any(f.lower() in (sector or "").lower() for f in FINANCIAL_SECTORS)

def count_div_years(ticker_obj):
    """連続配当年数を推定（Yahoo Financeの配当履歴から）"""
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

    for i, code in enumerate(CODES):
        if i % 20 == 0:
            log.info(f"[{i}/{total}] 処理中...")
        try:
            t = yf.Ticker(f"{code}.T")
            info = t.info

            # 基本データ取得
            price = info.get("currentPrice") or info.get("regularMarketPrice") or 0
            if price <= 0:
                continue

            pbr          = info.get("priceToBook")
            per          = info.get("trailingPE")
            roe_raw      = info.get("returnOnEquity")
            div_yield_raw= info.get("dividendYield")
            div_rate     = info.get("dividendRate") or 0
            payout_raw   = info.get("payoutRatio")
            name         = info.get("shortName") or info.get("longName") or code
            sector_en    = info.get("sector") or ""
            sector       = SECTOR_MAP_JA.get(sector_en, sector_en or "その他")

            # None チェック
            if pbr is None or roe_raw is None or div_yield_raw is None:
                continue

            roe         = roe_raw * 100
            div_yield   = div_yield_raw * 100
            payout_ratio= (payout_raw or 0) * 100

            # 自己資本比率（概算）
            total_assets = info.get("totalAssets") or 0
            book_val     = info.get("bookValue") or 0
            shares       = info.get("sharesOutstanding") or 0
            equity       = book_val * shares
            equity_ratio = (equity / total_assets * 100) if total_assets > 0 else 0

            fin = is_financial(sector_en)
            div_years = count_div_years(t)

            # ─── フィルター ───
            if div_yield    < FILTERS["min_yield"]:                     continue
            if pbr          > FILTERS["max_pbr"]:                       continue
            if roe          < FILTERS["min_roe"]:                       continue
            if not fin and equity_ratio < FILTERS["min_equity_ratio"]:  continue
            if div_years    < FILTERS["min_div_years"]:                 continue
            if payout_ratio > FILTERS["max_payout_ratio"] and payout_ratio > 0: continue
            if per is not None and per > 30:                            continue

            row = {
                "code":                  code,
                "name":                  name[:20],
                "sector":                sector,
                "price":                 round(price),
                "dividendYield":         round(div_yield, 2),
                "annualDividend":        round(div_rate, 1),
                "pbr":                   round(pbr, 2),
                "per":                   round(per, 1) if per else 0,
                "roe":                   round(roe, 1),
                "equityRatio":           round(equity_ratio, 1),
                "payoutRatio":           round(payout_ratio, 1),
                "continuousDividendYears": div_years,
                "isFinancial":           fin,
            }
            row["score"] = calc_score(row)
            results.append(row)
            log.info(f"  ✓ {code} {name[:15]} 利回り:{div_yield:.1f}% PBR:{pbr:.2f} スコア:{row['score']}")

        except Exception as e:
            log.debug(f"{code}: スキップ ({e})")
        finally:
            time.sleep(0.3)   # Yahoo Finance 負荷対策

    results.sort(key=lambda x: x["score"], reverse=True)
    log.info(f"スクリーニング完了 → {len(results)} 銘柄ヒット")
    return results

def main():
    log.info("=== 高配当・低PBR スクリーナー (yfinance版) 開始 ===")
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
