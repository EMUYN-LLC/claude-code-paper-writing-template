# scripts/ — スクリプト実行の指示

## collect.py の実行

初回セットアップ時は Claude Code が自動的に実行する。
再実行が必要な場合 (キーワード変更・追加収集など):

1. `scripts/collect_config.yaml` の `query` を変更する
2. `python scripts/collect.py` を実行する

## セッション再開時のチェックリスト

前回セッションから再開する場合:

```bash
# 前セッションのエージェント出力が残っているか確認
ls {TEMP}/eval_*.md

# 二者協議まで完了しているサマリーを確認
grep -rl "二者協議" references/summaries/
```

前セッションの agent ID は新セッションでは無効 (SendMessage 不可)。
一時ファイルが唯一の引継ぎ手段。

## セットアップ (初回のみ)

詳細は `scripts/README.md` を参照。

```bash
pip install -r scripts/requirements.txt
```
