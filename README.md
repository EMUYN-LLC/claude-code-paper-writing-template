# Claude Code — 医療論文執筆テンプレート

[Claude Code](https://claude.ai/code) を使って医療研究論文の執筆を支援するテンプレートです。文献収集・批判的評価・原稿推敲を AI と協働して進めることができます。

臨床医・研究者を対象に設計しています。外科・内科・精神科・公衆衛生・基礎医学など、分野を問わず使えます。

---

## このテンプレートと組み合わせて使いたい EMUYN LLC のツール

論文作成に必須の 2 つの無料ツールを [EMUYN LLC](https://www.emuyn.net) が提供しています。

### 📄 [PubMedX](https://www.emuyn.net/pubmedx/index) — PubMed に和訳・IF を追加するブラウザ拡張

PubMed の検索結果に **日本語訳** と **論文スコア** をその場で表示します。Chrome / Edge / Firefox 対応、無料。文献収集の効率が大幅に上がります。

### 📊 [Reactive Stat](https://www.emuyn.net/stats/index) — ブラウザだけで使える無料統計ソフト

インストール不要、Windows / Mac / スマートフォン対応。R による信頼性の高い統計解析を AI が解説付きで実行します。アップロードしたデータはインターネットに送信されないため安全に使えます。

---

## このテンプレートで何ができるか

- **CLAUDE.md** — Claude Code がセッション開始時に自動で読み込む動作指示ファイル。プロジェクトの文脈・ルール・ワークフローをここに書いておくことで、毎回同じ説明をせずに済みます。各フォルダの CLAUDE.md は自由にカスタマイズ可能。ただし長く書きすぎるとコンテキストを圧迫するため簡潔に保つこと。「このルールを CLAUDE.md に追記して」と依頼すれば Claude Code 自身に更新させることもできます
- **`.claude/settings.json`** — 作業中に権限確認で中断されないよう設定済みの許可リスト
- **コピペ用プロンプト集** — 二者協議システム (統計家 / 専門医) のエージェント起動プロンプト
- **ファイルテンプレート** — 原稿・研究計画・文献サマリー・引用レジストリ
- **スコアリング付き文献収集** — 「文献を収集して」と伝えるだけで、PubMed 検索・被引用数 (iCite)・雑誌スコア (SJR) の 3 指標で自動スコアリングし、上位論文から順に PDF 取得・文献登録が完了する

---

## 二者協議システム

参考文献ごとに Claude Code エージェントを **2つ同時に** 起動し、それぞれが論文全文を読んで異なる視点から批判的評価を行います。

| エージェント | 評価視点 |
|---|---|
| 統計家 | 研究デザイン・サンプルサイズ・バイアス・統計手法 |
| 専門医 | 臨床的妥当性・実臨床への適用可能性・専門的正確さ |

2 エージェントが同時に動くため、待ち時間は 1 エージェント分だけです。評価結果は一時ファイルに保存されるため、作業を中断・再開しても消えません。

---

## 文献スコアリングシステム

PubMed の検索結果を 3 つの指標から自動スコアリングし、質の高い論文から優先的に処理します。

| 指標 | データソース | 重み (デフォルト) |
|---|---|---|
| 年平均被引用数 (citations/year) | NIH iCite API | 30% |
| 総被引用数 | NIH iCite API | 20% |
| 雑誌スコア (SJR) | SCImago Journal Rank 2024 | 50% |

各指標を log スケール + min-max 正規化したうえで重み付き合計を算出。候補論文 (デフォルト 50 件) をスコア順に並べ、上位から順に処理します。SJR 未掲載雑誌はスコアが低くなるため、査読水準の低い OA 誌が上位に来にくくなっています。重みは `scripts/collect_config.yaml` で自由に調整できます。

---

## はじめ方

> **最初の環境構築だけは少し手間がかかります。** git・Claude Code のセットアップが必要です。でも、それさえ乗り越えれば、その後の作業は一気に楽になります。文献収集・評価・原稿推敲のサイクルが驚くほどスムーズに回り始めます。ぜひ最初の壁を越えてください。

### Step 1 — パソコンに取り込む

#### Mac の場合

1. **ターミナルを開く** — Spotlight 検索 (⌘ + スペース) で「ターミナル」と入力して開く
2. 以下のコマンドを実行する:

```bash
git clone https://github.com/EMUYN-LLC/claude-code-paper-writing-template.git
```

3. コマンドを実行したフォルダの中に `claude-code-paper-writing-template` フォルダが作られます

> Mac には git が最初から入っています。初回実行時に「コマンドラインデベロッパツールをインストールしますか」と表示されたら「インストール」をクリックしてから再度実行してください。

#### Windows の場合

1. **Git をインストールする** — [git-scm.com/download/win](https://git-scm.com/download/win) を開き、「Click here to download」をクリック。インストーラーはすべてデフォルトのまま「Next」で進める
2. スタートメニューで「**ターミナル**」を開く
3. 以下のコマンドを実行する:

```bash
git clone https://github.com/EMUYN-LLC/claude-code-paper-writing-template.git
```

4. コマンドを実行したフォルダの中に `claude-code-paper-writing-template` フォルダが作られます

### Step 2 — フォルダの中から Claude Code を起動する

1. [claude.ai/code](https://claude.ai/code) から Claude Code をインストール (まだの場合)
2. ターミナルでクローンしたフォルダに移動して Claude Code を起動する:

**Mac** — ターミナルで:
```bash
cd claude-code-paper-writing-template
claude
```

**Windows** — ターミナルで:
```
cd claude-code-paper-writing-template
claude.cmd
```

3. 起動直後に以下の安全確認が表示されます。**「1. Yes, I trust this folder」を選択**してください。

```
Quick safety check: Is this a project you created or one you trust?
❯ 1. Yes, I trust this folder
  2. No, exit
```

> **英語の確認ダイアログについて**: 作業中にファイルの読み書きや実行に関する英語の許可確認が表示されることがあります。このテンプレートの範囲内では危険な操作は行われないため、**基本的にすべて Yes (または Enter) で問題ありません**。

### Step 3 — 「セットアップして」と入力する

Claude Code は起動しただけでは待機状態です。プロンプトに **`セットアップして`** と入力して Enter を押してください。

すると Claude が自動的にセットアップを開始します。

1. 研究テーマ・論文一覧を質問 → `CLAUDE.md` を更新
2. 文献収集の設定 (キーワード・件数・メールアドレス) を質問 → `scripts/collect_config.yaml` に保存
3. 「自動収集しますか？」の確認後、PubMed から自動収集

---

### GitHub で作業履歴を保存する場合 (オプション)

自分の GitHub リポジトリに紐づけると、作業履歴のクラウド保存・共同研究者との共有ができます。

1. [github.com](https://github.com) でアカウントを作成 (無料)
2. このページの「**Use this template**」→「**Create a new repository**」で自分のリポジトリを作成
3. ローカルのリモート先を自分のリポジトリに変更して push:

```bash
git remote set-url origin https://github.com/{あなたのユーザー名}/{リポジトリ名}.git
git push -u origin main
```

> **日常の作業後**: Claude Code から `git add` → `git commit` するだけで変更履歴が GitHub に自動保存されます。履歴の確認・共有は [github.com](https://github.com) のブラウザ画面から行えます。

---

## ディレクトリ構成

```
my-paper-project/
├── CLAUDE.md                        # Claude Code への動作指示 (最初に編集)
├── .claude/
│   └── settings.json                # 権限許可リスト
├── manuscripts/
│   └── P01_your_study/
│       └── manuscript_v1.md         # 英語原稿テンプレート
├── projects/
│   └── P01_your_study.md            # 研究計画・仮説メモ
├── references/
│   ├── pdfs/                        # PDF ファイルをここに置く
│   ├── abstracts/                   # PDF 未取得時のアブストラクト (自動生成)
│   ├── summaries/                   # 生成した文献サマリー
│   │   └── _template.md             # サマリーのフォーマットテンプレート
│   └── refs.yaml                    # 引用文献の一元管理レジストリ
├── scripts/
│   ├── collect.py                   # PubMed 自動収集スクリプト
│   ├── collect_config.yaml          # 検索キーワード・件数・メールアドレス
│   └── requirements.txt
├── data/
│   └── .gitignore                   # 患者データを GitHub に送らないための設定
└── prompts/                         # コピペ用プロンプト集
    ├── README.md
    ├── 01_summary_creation.md
    ├── 02_agent_statistician.md
    └── 03_agent_specialist.md
```

---

## 患者データの安全性

`data/raw/` フォルダ内のファイルは GitHub に送られない設定になっています。生データをこのフォルダ内に置く限り、個人情報がインターネット上に公開されることはありません。

---

## クレジット表示について (CC BY 4.0)

本テンプレートは **[EMUYN LLC](https://emuyn.net)** が作成し、[CC BY 4.0](https://creativecommons.org/licenses/by/4.0/) ライセンスで公開しています。

改変・再配布・商用利用はすべて自由ですが、**クレジット表示が必要**です。

使用・派生物には以下のいずれかの形でクレジットを記載してください:

```
Based on claude-code-paper-writing-template by EMUYN LLC
https://github.com/EMUYN-LLC/claude-code-paper-writing-template
```

このテンプレートが役に立った場合は、リポジトリに ⭐ をいただけると励みになります。
