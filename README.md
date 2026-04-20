# 📊 StockScreener JP — セットアップガイド

高配当・低PBR・安定株の自動スクリーニングシステム

---

## システム構成

```
[J-Quants API (JPX公式)]
         ↓ Python スクリプト
[GitHub Actions (毎週月曜 07:00 JST)]
         ↓ results.json をコミット
[GitHub リポジトリ]
         ↓ 自動デプロイ
[Vercel ダッシュボード]
```

---

## 初期セットアップ（30分）

### 1. J-Quants アカウント登録（無料）
1. https://jpx-jquants.com/ にアクセス
2. 無料プランでサインアップ
3. メールアドレスとパスワードをメモ

### 2. GitHubリポジトリの作成
```bash
git init stock-screener
cd stock-screener
# このプロジェクトのファイルをすべてコピー
git add .
git commit -m "init"
gh repo create stock-screener --public --push
```

### 3. GitHub Secrets の設定
GitHubリポジトリ → Settings → Secrets and variables → Actions → New repository secret

| Secret名          | 値                      |
|-------------------|------------------------|
| JQUANTS_MAIL      | J-Quantsのメールアドレス |
| JQUANTS_PASSWORD  | J-Quantsのパスワード    |

### 4. Vercelにデプロイ
1. https://vercel.com/ でGitHubアカウントと連携
2. 「New Project」→ このリポジトリを選択
3. Framework: `Create React App` または `Vite`
4. 「Deploy」ボタンを押すだけ

---

## 動作確認

### 手動でスクリーナーを動かす
GitHub → Actions タブ → 「株式スクリーニング 自動実行」→ 「Run workflow」

### ローカルで動かす
```bash
pip install requests pandas
export JQUANTS_MAIL="your@email.com"
export JQUANTS_PASSWORD="yourpassword"
python screener.py
```

---

## スクリーニング条件のカスタマイズ

`screener.py` の `FILTERS` 変数を編集：

```python
FILTERS = {
    "min_yield":        3.5,   # 配当利回り最低(%)
    "max_pbr":          1.0,   # PBR上限(倍)
    "min_roe":          5.0,   # ROE最低(%)
    "min_equity_ratio": 25.0,  # 自己資本比率最低(%) ※金融株は除外
    "min_div_years":    3,     # 連続配当年数最低
    "max_payout_ratio": 80.0,  # 配当性向上限(%)
}
```

---

## ファイル構成

```
stock-screener/
├── screener.py                   # スクリーニングロジック
├── .github/
│   └── workflows/
│       └── screener.yml          # 自動実行スケジュール
├── public/
│   └── data/
│       └── results.json          # スクリーニング結果（自動更新）
└── src/
    └── App.jsx                   # ダッシュボード（React）
```

---

## 注意事項

- J-Quants 無料プランはデータに一部制限あり（直近2年分等）
- API の利用規約に従い商用利用不可
- 本システムは情報提供を目的としており、投資助言ではありません
