# scripts/ — 文献収集スクリプト

## 使い方

`collect.py` は Claude Code が自動的に実行します。ユーザーが直接このスクリプトを呼び出す必要はありません。

初回セットアップ時に Claude が質問を通じて `scripts/collect_config.yaml` に設定を書き込み、その後自動実行します。

---

## セットアップ — Mac

Mac には Python 3 が使える状態になっていることがほとんどです。
ターミナルを開いてプロジェクトフォルダに移動してから実行してください。

**ターミナルの開き方**: Spotlight (⌘ + スペース) → 「ターミナル」と入力 → Enter

```bash
pip install -r scripts/requirements.txt
```

---

## セットアップ — Windows (初めての方向け手順)

### Step 1 — Python のインストール

Python は Microsoft Store から無料でインストールできます。プログラミングの知識は不要です。

1. キーボードの **Windows キー** を押してスタートメニューを開く
2. 「**Microsoft Store**」と入力して開く
3. 検索ボックスに「**Python**」と入力
4. 「**Python 3.x**」(数字が一番大きいもの) を選んで「入手」をクリック
5. インストールが完了したら、コマンドプロンプトを**一度閉じて開き直す**

> コマンドプロンプトの開き方: Windows キー → 「cmd」と入力 → Enter

### Step 2 — インストール確認

コマンドプロンプトで以下を入力して Enter:

```
python --version
```

`Python 3.xx.x` のように表示されれば成功です。

### Step 3 — 依存パッケージのインストール

テンプレートのフォルダに移動してから実行します。

```
cd テンプレートフォルダのパス
pip install -r scripts\requirements.txt
```

---

## 設定ファイル

`scripts/collect_config.yaml` に収集設定が保存されます。Claude が自動で書き込みますが、直接編集しても構いません。

```yaml
query: "検索キーワード"
max_results: 20
email: "your-email@example.com"
```

---

## 出力先

| 出力 | 場所 |
|---|---|
| PDF ファイル | `references/pdfs/{PMID}.pdf` |
| refs.yaml 登録 | `references/refs.yaml` (自動追記) |
| 評価プロンプト | Mac: `/tmp/eval_prompts/` / Windows: `%TEMP%\eval_prompts\` |

---

## 無料 PDF が取得できなかった場合

完了後に一覧表示される PMID を以下の方法で入手し、
`references/pdfs/{PMID}.pdf` という名前で保存してください。

- **大学・病院のネットワーク経由でアクセス** — 機関契約で有料論文も無料でダウンロードできることが多い
- PubMed Central (PMC) で PMID を検索
- ResearchGate で著者名を検索
- 著者に直接メールで reprint を依頼

---

## 注意事項

- API のレート制限により、1件あたり約 0.4 秒のウェイトを入れています
- `refs.yaml` のタグは `{著者姓}_{n}_{PMID}` 形式で自動生成されます。後から手動で修正してください
