# references/ — 文献作業の指示

## 一時ファイルの命名規則

- エージェント出力: `{TEMP}/eval_{PMID}_{役割}.md`
  - 役割名: `statistician` / `specialist`
  - `{TEMP}` は OS に応じて自動判定される (Windows: `%TEMP%` / Mac・Linux: `/tmp`)。編集不要。

## サマリー作成フロー

**Step 1** — PDF を `references/pdfs/` に配置する。Claude Code は PDF を直接読めるため、テキスト変換は不要。

**Step 2** — `references/summaries/_template.md` のフォーマットで
`references/summaries/{著者姓}_{キーワード}_{PMID}.md` を作成する。

**Step 3** — `prompts/` のプロンプトを使い、2エージェントを同時に起動する
(`run_in_background: true`)。各エージェントは PDF を直接読み、評価結果を一時ファイルに書き出す。

- 1論文ずつ処理 = 2エージェント並列 (推奨)
- 最大 5論文同時 = 10エージェント並列 (これ以上はコンテキスト過負荷)

**Step 4** — 2エージェントの完了後、必ず以下の形式で案内してからサマリーに統合する。

```
=== 二者協議 完了: PMID {PMID} ===

評価ファイル:
  統計家 → {TEMP}/eval_{PMID}_statistician.md
  専門医 → {TEMP}/eval_{PMID}_specialist.md

次の作業: 評価結果をサマリーに統合する
  ・サマリー未作成の場合は先に prompts/01_summary_creation.md のプロンプトで作成すること
  ・サマリー作成済みの場合は以下をそのまま送信:

──────────────────────────────────────────────────
{TEMP}/eval_{PMID}_statistician.md と {TEMP}/eval_{PMID}_specialist.md を読み、
references/summaries/ 内の該当サマリーの「二者協議による批判的評価」セクションに統合してください。
──────────────────────────────────────────────────
```

## ファイル命名規則

| 種別 | 規則 | 例 |
|------|------|----|
| PDF | `{PMID}.pdf` | `12345678.pdf` |
| サマリー | `{著者姓}_{キーワード}_{PMID}.md` | `Smith_keyword_12345678.md` |
| エージェント出力 | `eval_{PMID}_{役割}.md` | `eval_12345678_statistician.md` |

## refs.yaml への登録

サマリー作成後、`references/refs.yaml` にエントリを追加する。
タグ形式: `著者姓_PMID`

```yaml
- tag: Smith_12345678
  authors: Smith J, Jones A
  title: "Paper title here"
  journal: Journal Name
  year: 2020
  pmid: "12345678"
  doi: "10.1097/example.0000"
  papers: [P01]
  notes: ""
```

## 品質ルール

- すべてのサマリーに「引用時の注意点」セクションを設け、主要な限界を明記する
- 数値・統計はすべて論文から正確に引用する (推測・補完しない)
- セッション再開時: `ls {TEMP}/eval_*.md` で前回の出力が残っていないか確認する
- 前セッションの agent ID は新セッションでは無効 (SendMessage 不可)
