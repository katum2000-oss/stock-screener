"""
国内株式 高配当・低PBR・安定スクリーナー
J-Quants API (JPX公式) を使用して毎週自動スクリーニング

必要な環境変数:
  JQUANTS_REFRESH_TOKEN - J-QuantsダッシュボードのRefresh Token
"""

import os
import json
import time
import logging
from datetime import datetime, timedelta
from pathlib import Path

import requests
import pandas as pd

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
log = logging.getLogger(__name__)

# ─────────────────────────────────────────
# スクリーニング条件（GitHub Actionsの環境変数で上書き可能）
# ─────────────────────────────────────────
FILTERS = {
    "min_yield":         float(os.environ.get("MIN_YIELD",   "3.5")),  # 配当利回り最低(%)
    "max_pbr":           float(os.environ.get("MAX_PBR",     "1.0")),  # PBR上限(倍)
    "min_roe":           float(os.environ.get("MIN_ROE",     "5.0")),  # ROE最低(%)
    "min_equity_ratio":  float(os.environ.get("MIN_EQUITY",  "25.0")), # 自己資本比率最低(%)
    "min_div_years":     int(os.environ.get("MIN_DIV_YEARS", "3")),    # 連続配当年数最低
    "max_payout_ratio":  float(os.environ.get("MAX_PAYOUT",  "80.0")), # 配当性向上限(%)
}

# 金融セクターは自己資本比率基準を除外（業種特性が異なるため）
FINANCIAL_SECTORS = {"銀行業", "証券業、商品先物取引業", "その他金融業", "保険業"}

OUTPUT_PATH = Path("public/data/results.json")


# ─────────────────────────────────────────
# J-Quants API クライアント
# ─────────────────────────────────────────
class JQuantsClient:
    BASE = "https://api.jquants.com/v1"

    def __init__(self):
        self.id_token = self._get_id_token()

def _get_id_token(self):
    mail = os.environ["JQUANTS_MAIL"]
    pw   = os.environ["JQUANTS_PASSWORD"]
    log.info("J-Quants API: 認証中...")
    r = requests.post(f"{self.BASE}/token/auth_user",
                      json={"mailaddress": mail, "password": pw}, timeout=15)
    r.raise_for_status()
    refresh = r.json()["refreshToken"]
    r = requests.post(f"{self.BASE}/token/auth_refresh",
                      params={"refreshtoken": refresh}, timeout=15)
    r.raise_for_status()
    log.info("認証成功")
    return r.json()["idToken"]

    def _get(self, path, params=None):
        headers = {"Authorization": f"Bearer {self.id_token}"}
        r = requests.get(f"{self.BASE}{path}", headers=headers,
                         params=params or {}, timeout=20)
        if r.status_code == 429:   # Rate limit
            log.warning("Rate limit hit - 60秒待機")
            time.sleep(60)
            return self._get(path, params)
        r.raise_for_status()
        return r.json()

    def get_listed_stocks(self):
        """東証上場銘柄一覧"""
        data = self._get("/listed/info")
        return pd.DataFrame(data.get("info", []))

    def get_fins(self, code):
        """最新財務情報 (BPS/EPS/自己資本比率)"""
        data = self._get("/fins/statements", {"code": code})
        df = pd.DataFrame(data.get("statements", []))
        if df.empty:
            return None
        df["DisclosedDate"] = pd.to_datetime(df["DisclosedDate"], errors="coerce")
        return df.sort_values("DisclosedDate", ascending=False).iloc[0]

    def get_price(self, code):
        """直近終値"""
        to_dt   = datetime.today()
        from_dt = to_dt - timedelta(days=10)
        data = self._get("/markets/prices/daily_quotes", {
            "code": code,
            "from": from_dt.strftime("%Y-%m-%d"),
            "to":   to_dt.strftime("%Y-%m-%d"),
        })
        df = pd.DataFrame(data.get("daily_quotes", []))
        if df.empty:
            return None
        df["Date"] = pd.to_datetime(df["Date"], errors="coerce")
        return float(df.sort_values("Date", ascending=False).iloc[0]["Close"])

    def get_dividends(self, code):
        """配当履歴"""
        data = self._get("/fins/dividend", {"code": code})
        df = pd.DataFrame(data.get("dividend", []))
        if df.empty:
            return None
        df["RecordDate"] = pd.to_datetime(df["RecordDate"], errors="coerce")
        return df


# ─────────────────────────────────────────
# スクリーニング
# ─────────────────────────────────────────
def count_consecutive_div_years(div_df) -> int:
    """配当が途切れずに続いている年数を返す"""
    if div_df is None or div_df.empty:
        return 0
    years = sorted(div_df["RecordDate"].dt.year.dropna().unique(), reverse=True)
    count = 0
    for yr in range(datetime.today().year, datetime.today().year - 30, -1):
        if yr in years:
            count += 1
        else:
            break
    return count


def calc_score(row) -> int:
    """総合スコア (0-100)"""
    y   = min(row["dividendYield"]           / 6    * 30, 30)
    p   = max(0, (1.5 - row["pbr"])          / 1.5  * 25)
    r   = min(row["roe"]                      / 15   * 20, 20)
    yr  = min(row["continuousDividendYears"]  / 20   * 15, 15)
    eq  = 10 if row["isFinancial"] else min(row["equityRatio"] / 60 * 10, 10)
    return round(y + p + r + yr + eq)


def screen(client: JQuantsClient) -> list:
    log.info("銘柄一覧を取得中...")
    stocks = client.get_listed_stocks()

    # プライム・スタンダードのみ（コード末尾0で通常株を絞る）
    stocks = stocks[stocks["Code"].str.endswith("0")]
    log.info(f"対象銘柄数: {len(stocks)}")

    results = []
    for idx, (_, s) in enumerate(stocks.iterrows()):
        code = s["Code"]
        if idx % 50 == 0:
            log.info(f"[{idx}/{len(stocks)}] 処理中...")
        try:
            fins  = client.get_fins(code)
            price = client.get_price(code)
            divs  = client.get_dividends(code)

            if fins is None or price is None or price <= 0:
                continue

            bps          = float(fins.get("BookValuePerShare", 0) or 0)
            eps          = float(fins.get("EarningsPerShare",  0) or 0)
            equity_ratio = float(fins.get("EquityToAssetRatio", 0) or 0) * 100  # 小数→%

            if bps <= 0 or eps <= 0:
                continue

            pbr = price / bps
            per = price / eps
            roe = eps   / bps * 100

            # 年間配当
            annual_div = 0.0
            if divs is not None and not divs.empty:
                recent = divs[divs["RecordDate"] >= pd.Timestamp.today() - pd.DateOffset(years=1)]
                annual_div = recent["DividendPerShare"].astype(float).sum()

            if annual_div <= 0:
                continue

            div_yield    = annual_div / price * 100
            payout_ratio = annual_div / eps   * 100 if eps > 0 else 999
            div_years    = count_consecutive_div_years(divs)
            sector       = s.get("Sector17CodeName") or s.get("Sector33CodeName") or "不明"
            is_fin       = sector in FINANCIAL_SECTORS

            # ─── フィルター適用 ───
            if div_yield    < FILTERS["min_yield"]:        continue
            if pbr          > FILTERS["max_pbr"]:          continue
            if roe          < FILTERS["min_roe"]:          continue
            if not is_fin and equity_ratio < FILTERS["min_equity_ratio"]: continue
            if div_years    < FILTERS["min_div_years"]:    continue
            if payout_ratio > FILTERS["max_payout_ratio"]: continue
            if per          > 30:                          continue  # 極端な高PER除外

            row = {
                "code":                  code[:4],          # 4桁表示
                "name":                  s.get("CompanyNameEnglish") or s.get("CompanyName", code),
                "sector":                sector,
                "price":                 round(price, 0),
                "dividendYield":         round(div_yield,    2),
                "annualDividend":        round(annual_div,   1),
                "pbr":                   round(pbr,          2),
                "per":                   round(per,          1),
                "roe":                   round(roe,          1),
                "equityRatio":           round(equity_ratio, 1),
                "payoutRatio":           round(payout_ratio, 1),
                "continuousDividendYears": div_years,
                "isFinancial":           is_fin,
            }
            row["score"] = calc_score(row)
            results.append(row)
            time.sleep(0.15)   # API負荷対策

        except Exception as e:
            log.debug(f"{code}: スキップ ({e})")
            continue

    results.sort(key=lambda x: x["score"], reverse=True)
    log.info(f"スクリーニング完了 → {len(results)} 銘柄ヒット")
    return results


# ─────────────────────────────────────────
# エントリーポイント
# ─────────────────────────────────────────
def main():
    client  = JQuantsClient()
    stocks  = screen(client)

    payload = {
        "updatedAt": datetime.now().strftime("%Y/%m/%d %H:%M JST"),
        "filters":   FILTERS,
        "count":     len(stocks),
        "stocks":    stocks,
    }

    OUTPUT_PATH.parent.mkdir(parents=True, exist_ok=True)
    with open(OUTPUT_PATH, "w", encoding="utf-8") as f:
        json.dump(payload, f, ensure_ascii=False, indent=2)

    log.info(f"結果を {OUTPUT_PATH} に保存しました（{len(stocks)}銘柄）")


if __name__ == "__main__":
    main()
