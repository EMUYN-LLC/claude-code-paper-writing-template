# Claude Code を医療研究論文の執筆支援に使う — 文献収集から原稿推敲まで

## はじめに

臨床研究者が論文を書くとき、最も時間を奪われるのは**文献管理と批判的評価**です。

関連文献を集め、1 本ずつ読んで評価し、引用すべき数値を整理し、自分の原稿との整合性を確認する。この作業は知的に重要ですが、消耗も大きい。

本記事では、**Claude Code** を使ってこのプロセスを体系化したリポジトリ設計を紹介します。文献収集・批判的評価・原稿推敲の一連のワークフローを、AI と協働しながら効率的に進められます。

リポジトリはこちら → [EMUYN-LLC/claude-code-paper-writing-template](https://github.com/EMUYN-LLC/claude-code-paper-writing-template)

---

## このテンプレートでできること

- PubMed から文献を自動収集し、**被引用数・雑誌スコアで自動ランキング**して上位論文を優先取得
- 統計家・専門医の 2 エージェントが**論文全文を並列で批判的評価**
- 評価結果をもとに文献サマリーを作成し、引用レジストリに自動登録
- 原稿の推敲・盗用チェック支援

---

## 文献スコアリングシステム

従来の PubMed 検索は「関連度順」で返ってきますが、関連度が高くても引用されていない論文や質の低い雑誌の論文が混じることがあります。

このテンプレートでは、3 つの指標から複合スコアを算出して順位を付け替えます。

| 指標 | データソース | デフォルト重み |
|---|---|---|
| 年平均被引用数 | NIH iCite API (無料) | 30% |
| 総被引用数 | NIH iCite API (無料) | 20% |
| 雑誌スコア (SJR) | SCImago Journal Rank 2024 | 50% |

各指標を log スケール + min-max 正規化したうえで重み付き合計を算出します。SJR に未掲載の雑誌 (査読水準の低い OA 誌など) はスコアが低くなります。

### 実際の例 ("rectal prolapse laparoscopic surgery" で検索)

| 順位 | 雑誌 | CPY | SJR | スコア |
|---|---|---|---|---|
| 1 | Annals of Surgery | 5.0 | 2.59 | 0.931 |
| 2 | Tech Coloproctol | 5.0 | 0.86 | 0.598 |
| 3 | Colorectal Dis | 4.0 | 1.00 | 0.581 |
| 4 | **Cureus** | **7.0** | **未掲載** | **0.500** |

Cureus は被引用数が最多でも SJR 未掲載のためスコアが低くなり、Annals of Surgery が1位に。

重みは `scripts/collect_config.yaml` で自由に調整できます。

```yaml
search_results: 50        # PubMed から取得する候補数
max_results: 20           # 上位から処理する件数
weight_citations_per_year: 0.3
weight_citation_count: 0.2
weight_sjr: 0.5
```

---

## 二者協議システム

文献ごとに Claude Code エージェントを **2 つ同時に** 起動し、論文全文を読んで評価します。

| エージェント | 評価視点 |
|---|---|
| 統計家 | 研究デザイン・サンプルサイズ・バイアス・統計手法 |
| 専門医 | 臨床的妥当性・実臨床への適用可能性・専門的正確さ |

2 エージェントが並列実行されるため、待ち時間は 1 エージェント分だけです。評価結果は一時ファイルに書き出されるため、作業を中断・再開しても消えません。

評価結果は文献サマリーの「二者協議による批判的評価」セクションに統合されます。

---

## ワークフロー全体像

```
1. セットアップ
   「セットアップして」と入力
   → 研究テーマ・キーワード・メールアドレスを質問
   → collect_config.yaml に保存

2. 文献収集
   「文献を収集して」と入力
   → PubMed 検索 (50 件候補)
   → iCite + SJR でスコアリング
   → 上位 20 件の PDF を自動ダウンロード
   → 取得できなかった論文はブラウザで一覧表示

3. 批判的評価
   → 統計家・専門医エージェントを 2 つ同時起動
   → 各エージェントが PDF 全文を読んで評価
   → 一時ファイルに評価結果を書き出し

4. サマリー統合
   → 評価結果を文献サマリーに統合
   → refs.yaml に引用レジストリとして登録

5. 原稿執筆
   → サマリーと引用レジストリをもとに推敲支援
```

---

## セットアップ

### 必要なもの

- **Claude Code** — [claude.ai/code](https://claude.ai/code) からインストール
- **git** — Mac は標準搭載、Windows は [git-scm.com](https://git-scm.com/download/win) からインストール
- **Python** — Mac は `brew install python3`、Windows は Microsoft Store からインストール

### 手順

```bash
# 1. リポジトリをクローン
git clone https://github.com/EMUYN-LLC/claude-code-paper-writing-template.git

# 2. フォルダに移動して Claude Code を起動
cd claude-code-paper-writing-template
claude          # Mac
claude.cmd      # Windows
```

起動後、「セットアップして」と入力するだけで Claude が対話形式で設定を進めます。

---

## 組み合わせて使いたいツール

### [PubMedX](https://www.emuyn.net/pubmedx/index)

PubMed の検索結果に**日本語訳**と**論文スコア**をその場で表示するブラウザ拡張 (Chrome / Edge / Firefox / 無料)。手動でダウンロードが必要な論文を探すときに役立ちます。

### [Reactive Stat](https://www.emuyn.net/stats/index)

インストール不要・ブラウザだけで使える無料統計ソフト。アップロードしたデータはインターネットに送信されないため安全に使えます。

---

## AI 利用に関する注意

このテンプレートは**研究者自身による論文執筆を支援するためのもの**です。AI が生成したテキストをそのまま論文として投稿することは学術倫理違反です。原稿は最終的に研究者自身が責任をもって確認・修正してください。

---

## まとめ

- PubMed 検索 → iCite + SJR スコアリング → 上位から自動取得
- 統計家・専門医の 2 エージェントが並列で批判的評価
- 評価結果・サマリー・引用レジストリを一元管理

臨床研究者の文献管理の負担を減らし、論文の質の向上につながることを目指して設計しました。ぜひ試してみてください。

リポジトリ → [EMUYN-LLC/claude-code-paper-writing-template](https://github.com/EMUYN-LLC/claude-code-paper-writing-template)
