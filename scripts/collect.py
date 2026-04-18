#!/usr/bin/env python3
"""
医療論文 自動収集スクリプト

処理フロー:
  1. scripts/collect_config.yaml から設定を読み込む
  2. PubMed E-utilities API でキーワード検索 → search_results 件の PMID 取得
  3. メタデータ・DOI を一括取得
  4. iCite API で被引用数・年平均被引用数を一括取得
  5. scripts/sjr.csv で雑誌スコア (SJR) を照合
  6. 3指標のスコアで降順ソート → 上位 max_results 件を処理
  7. Unpaywall API で合法な無料 PDF URL を確認
  8. PDF をダウンロード → references/pdfs/ に保存
  9. refs.yaml にメタデータを自動登録
  10. 二者協議エージェント用プロンプトを生成

PDF の読み取りは Claude Code が直接行うため、pdftotext は不要です。

使い方:
  Claude Code に「文献を収集して」と依頼してください。
  直接実行: python scripts/collect.py
"""

import csv
import math
import os
import re
import sys
import time
import webbrowser
from pathlib import Path

if sys.platform == "win32":
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    sys.stderr.reconfigure(encoding="utf-8", errors="replace")

try:
    import requests
    import yaml
except ImportError:
    print("依存パッケージが不足しています。以下を実行してください:")
    print("  pip install requests pyyaml")
    sys.exit(1)

# --- パス設定 -----------------------------------------------------------

REPO_ROOT = Path(__file__).parent.parent
PDF_DIR = REPO_ROOT / "references" / "pdfs"
ABSTRACT_DIR = REPO_ROOT / "references" / "abstracts"
REFS_YAML = REPO_ROOT / "references" / "refs.yaml"
PROMPTS_DIR = REPO_ROOT / "prompts"
CONFIG_FILE = Path(__file__).parent / "collect_config.yaml"
SJR_FILE = Path(__file__).parent / "sjr.csv"

if sys.platform == "win32":
    TEMP_DIR = Path(os.environ.get("TEMP", "C:/Windows/Temp"))
else:
    TEMP_DIR = Path("/tmp")

PROMPT_OUT_DIR = TEMP_DIR / "eval_prompts"

# ------------------------------------------------------------------------


def load_config() -> dict:
    if not CONFIG_FILE.exists():
        print(f"設定ファイルが見つかりません: {CONFIG_FILE}")
        print("Claude Code に「文献を収集して」と依頼すると自動設定されます。")
        sys.exit(1)
    with open(CONFIG_FILE, encoding="utf-8") as f:
        config = yaml.safe_load(f) or {}
    query = str(config.get("query", "")).strip()
    email = str(config.get("email", "")).strip()
    if not query or not email:
        print("設定が未完了です (query または email が空白)。")
        print(f"Claude Code に「文献を収集して」と依頼するか、{CONFIG_FILE} を直接編集してください。")
        sys.exit(1)
    return {
        "query": query,
        "email": email,
        "search_results": int(config.get("search_results", 50)),
        "max_results": int(config.get("max_results", 20)),
        "weight_citations_per_year": float(config.get("weight_citations_per_year", 0.3)),
        "weight_citation_count": float(config.get("weight_citation_count", 0.2)),
        "weight_sjr": float(config.get("weight_sjr", 0.5)),
    }


def search_pubmed(query: str, count: int, email: str) -> list:
    url = "https://eutils.ncbi.nlm.nih.gov/entrez/eutils/esearch.fcgi"
    params = {"db": "pubmed", "term": query, "retmax": count, "retmode": "json", "email": email}
    resp = requests.get(url, params=params, timeout=15)
    resp.raise_for_status()
    return resp.json()["esearchresult"]["idlist"]


def fetch_metadata_batch(pmids: list, email: str) -> dict:
    """複数 PMID のメタデータを一括取得"""
    url = "https://eutils.ncbi.nlm.nih.gov/entrez/eutils/esummary.fcgi"
    params = {"db": "pubmed", "id": ",".join(pmids), "retmode": "json", "email": email}
    resp = requests.get(url, params=params, timeout=30)
    resp.raise_for_status()
    result = resp.json().get("result", {})
    return {pmid: result[pmid] for pmid in pmids if pmid in result}


def get_doi_batch(pmids: list) -> dict:
    """複数 PMID の DOI を一括取得"""
    url = f"https://www.ncbi.nlm.nih.gov/pmc/utils/idconv/v1.0/?ids={','.join(pmids)}&format=json"
    try:
        resp = requests.get(url, timeout=15)
        records = resp.json().get("records", [])
        return {r["pmid"]: r.get("doi") for r in records if "pmid" in r}
    except Exception:
        return {}


def fetch_icite(pmids: list) -> dict:
    """iCite API で被引用数・年平均被引用数を一括取得"""
    url = "https://icite.od.nih.gov/api/pubs"
    try:
        resp = requests.get(url, params={"pmids": ",".join(pmids)}, timeout=20)
        resp.raise_for_status()
        return {str(item["pmid"]): item for item in resp.json().get("data", [])}
    except Exception as e:
        print(f"  iCite 取得失敗 (被引用フィルタをスキップ): {e}")
        return {}


def load_sjr_data() -> dict:
    """sjr.csv を読み込み {正規化ISSN: sjr_score} を返す"""
    if not SJR_FILE.exists():
        print(f"  sjr.csv が見つかりません — SJR スコアをスキップします")
        return {}
    sjr = {}
    with open(SJR_FILE, encoding="utf-8") as f:
        reader = csv.DictReader(f, delimiter=";")
        for row in reader:
            issn_field = row.get("Issn", "")
            sjr_str = row.get("SJR", "0").replace(",", ".")
            try:
                score = float(sjr_str) if sjr_str and sjr_str != "-" else 0.0
            except ValueError:
                continue
            for raw in issn_field.replace(",", " ").split():
                normalized = _normalize_issn(raw)
                if normalized:
                    sjr[normalized] = score
    return sjr


def _normalize_issn(issn: str) -> str:
    digits = re.sub(r"[^0-9X]", "", issn.upper())
    return f"{digits[:4]}-{digits[4:]}" if len(digits) == 8 else ""


def _get_issns(meta: dict) -> list:
    """esummary レスポンスから ISSN (print + electronic) を返す"""
    return [meta.get(k, "").strip() for k in ("issn", "essn") if meta.get(k, "").strip()]


def compute_scores(pmids: list, meta: dict, icite: dict, sjr_data: dict, weights: dict) -> list:
    """
    3指標 (citations_per_year / citation_count / sjr) を log1p + min-max 正規化し、
    重み付き合計でスコアを算出して降順ソートした [(pmid, score, detail), ...] を返す。
    データ欠損時は当該指標を除いた重みで再計算する。
    """
    rows = []
    for pmid in pmids:
        ic = icite.get(pmid, {})
        issns = _get_issns(meta.get(pmid, {}))
        rows.append({
            "pmid": pmid,
            "cpy": ic.get("citations_per_year") or 0.0,
            "cnt": ic.get("citation_count") or 0,
            "sjr": next((sjr_data[i] for i in issns if i in sjr_data), 0.0),
        })

    def _normalize(key: str, use_log: bool):
        vals = [r[key] for r in rows if r[key] is not None]
        if not vals:
            return
        transformed = [math.log1p(v) for v in vals] if use_log else list(map(float, vals))
        lo, hi = min(transformed), max(transformed)
        span = hi - lo or 1.0
        for r in rows:
            raw = r[key]
            if raw is None:
                r[f"n_{key}"] = None
            else:
                v = math.log1p(raw) if use_log else float(raw)
                r[f"n_{key}"] = (v - lo) / span

    _normalize("cpy", use_log=True)
    _normalize("cnt", use_log=True)
    _normalize("sjr", use_log=False)

    metric_weights = [
        ("n_cpy", weights["citations_per_year"]),
        ("n_cnt", weights["citation_count"]),
        ("n_sjr", weights["sjr"]),
    ]

    results = []
    for r in rows:
        weighted_sum = total_w = 0.0
        for key, w in metric_weights:
            if r.get(key) is not None:
                weighted_sum += r[key] * w
                total_w += w
        score = weighted_sum / total_w if total_w > 0 else 0.0
        results.append((r["pmid"], score, r))

    results.sort(key=lambda x: x[1], reverse=True)
    return results


def check_unpaywall(doi: str | None, email: str) -> str | None:
    if not doi:
        return None
    url = f"https://api.unpaywall.org/v2/{doi}?email={email}"
    try:
        resp = requests.get(url, timeout=10)
        if resp.status_code != 200:
            return None
        best = resp.json().get("best_oa_location")
        return best.get("url_for_pdf") if best else None
    except Exception:
        return None


def fetch_abstract(pmid: str, email: str) -> Path | None:
    dest = ABSTRACT_DIR / f"{pmid}.txt"
    if dest.exists():
        print(f"    アブストラクト既存: {dest.name}")
        return dest
    url = "https://eutils.ncbi.nlm.nih.gov/entrez/eutils/efetch.fcgi"
    params = {"db": "pubmed", "id": pmid, "rettype": "abstract", "retmode": "text", "email": email}
    try:
        resp = requests.get(url, params=params, timeout=15)
        if resp.status_code == 200 and resp.text.strip():
            ABSTRACT_DIR.mkdir(parents=True, exist_ok=True)
            dest.write_text(resp.text, encoding="utf-8")
            print(f"    アブストラクト保存: {dest.name}")
            return dest
    except Exception as e:
        print(f"    アブストラクト取得失敗: {e}")
    return None


def download_pdf(pdf_url: str, pmid: str) -> Path | None:
    dest = PDF_DIR / f"{pmid}.pdf"
    if dest.exists():
        print(f"    既存: {dest.name}")
        return dest
    try:
        resp = requests.get(pdf_url, allow_redirects=True, timeout=30)
        if resp.status_code == 200 and "pdf" in resp.headers.get("content-type", ""):
            dest.write_bytes(resp.content)
            print(f"    ダウンロード完了: {dest.name}")
            return dest
    except Exception as e:
        print(f"    ダウンロード失敗: {e}")
    return None


def register_refs_yaml(meta: dict, pmid: str, doi: str | None):
    refs_data = {"references": []}
    if REFS_YAML.exists():
        with open(REFS_YAML, encoding="utf-8") as f:
            refs_data = yaml.safe_load(f) or {"references": []}
    existing_pmids = [str(r.get("pmid", "")) for r in refs_data.get("references", [])]
    if pmid in existing_pmids:
        print(f"    refs.yaml: 登録済み (PMID {pmid})")
        return
    authors = meta.get("authors", [])
    first_author = authors[0].get("name", "Unknown").split(" ")[0] if authors else "Unknown"
    year = meta.get("pubdate", "")[:4]
    entry = {
        "tag": f"{first_author}_{pmid}",
        "authors": ", ".join(a.get("name", "") for a in authors),
        "title": meta.get("title", ""),
        "journal": meta.get("fulljournalname", ""),
        "year": int(year) if year.isdigit() else year,
        "pmid": pmid,
        "doi": doi or "",
        "papers": [],
        "notes": "",
    }
    refs_data["references"].append(entry)
    with open(REFS_YAML, "w", encoding="utf-8") as f:
        yaml.dump(refs_data, f, allow_unicode=True, default_flow_style=False)
    print(f"    refs.yaml 登録: {entry['tag']}")


def generate_agent_prompt(pmid: str) -> Path | None:
    PROMPT_OUT_DIR.mkdir(parents=True, exist_ok=True)
    pdf_path = PDF_DIR / f"{pmid}.pdf"
    abstract_path = ABSTRACT_DIR / f"{pmid}.txt"
    if pdf_path.exists():
        source_label, source_path = "論文 PDF", pdf_path
    elif abstract_path.exists():
        source_label, source_path = "アブストラクト (PDF 未取得のため全文評価は不可)", abstract_path
    else:
        return None
    roles = [
        ("statistician", "生物統計の専門家"),
        ("specialist",   "専門医"),
    ]
    lines = ["以下の 2 つのエージェントを同時に起動してください。\n"]
    for role_en, role_ja in roles:
        eval_out = TEMP_DIR / f"eval_{pmid}_{role_en}.md"
        num = {"statistician": "2", "specialist": "3"}[role_en]
        lines += [
            f"--- {role_ja}エージェント ---",
            f"あなたは{role_ja}です。",
            f"以下の{source_label}を読み、{PROMPTS_DIR}/0{num}_agent_{role_en}.md のフォーマットで評価してください。",
            f"{source_label}: {source_path}",
            f"評価結果を {eval_out} に書き出すこと。日本語で出力すること。\n",
        ]
    out_file = PROMPT_OUT_DIR / f"prompt_{pmid}.txt"
    out_file.write_text("\n".join(lines), encoding="utf-8")
    print(f"    評価プロンプト: {out_file}")
    return out_file


def _make_item(pmid: str, meta: dict, doi: str | None) -> dict:
    authors = meta.get("authors", [])
    return {
        "pmid": pmid,
        "title": meta.get("title", ""),
        "authors": ", ".join(a.get("name", "") for a in authors),
        "journal": meta.get("fulljournalname", ""),
        "year": meta.get("pubdate", "")[:4],
        "doi": doi or "",
    }


def generate_manual_download_html(no_pdf_items: list) -> Path:
    rows = ""
    for item in no_pdf_items:
        pmid = item["pmid"]
        save_as = PDF_DIR / f"{pmid}.pdf"
        rows += f"""
        <tr>
          <td>
            <strong>{item.get("title", "(タイトル不明)")}</strong><br>
            <small>{item.get("authors", "")}</small><br>
            <em>{item.get("journal", "")} {item.get("year", "")}</em><br>
            <code>保存先: {save_as}</code>
          </td>
          <td>
            <a href="https://pubmed.ncbi.nlm.nih.gov/{pmid}/" target="_blank">PubMed で開く</a>
          </td>
        </tr>"""

    html = f"""<!DOCTYPE html>
<html lang="ja">
<head>
<meta charset="UTF-8">
<title>手動ダウンロードが必要な論文</title>
<style>
  body {{ font-family: sans-serif; max-width: 960px; margin: 2em auto; padding: 0 1em; }}
  .notice {{ background: #fff3cd; border: 1px solid #ffc107; padding: 1em 1.5em; border-radius: 4px; margin-bottom: 1em; }}
  .pubmedx {{ background: #e8f4fd; border: 1px solid #3498db; padding: 1em 1.5em; border-radius: 4px; margin-bottom: 1.5em; }}
  .pubmedx h2 {{ margin: 0 0 0.3em; font-size: 1.1em; color: #2980b9; }}
  .pubmedx p {{ margin: 0; font-size: 0.9em; }}
  .pubmedx a.btn {{ display: inline-block; margin-top: 0.6em; padding: 0.4em 1em; background: #3498db; color: #fff; border-radius: 4px; text-decoration: none; font-size: 0.9em; }}
  table {{ width: 100%; border-collapse: collapse; }}
  th {{ background: #343a40; color: #fff; padding: 0.6em 1em; text-align: left; }}
  td {{ border: 1px solid #dee2e6; padding: 0.75em 1em; vertical-align: top; }}
  tr:nth-child(even) td {{ background: #f8f9fa; }}
  td a {{ color: #2980b9; }}
  code {{ display: block; margin-top: 0.5em; background: #e9ecef; padding: 0.3em 0.6em; border-radius: 3px; font-size: 0.85em; word-break: break-all; }}
</style>
</head>
<body>
<h1>手動ダウンロードが必要な論文 ({len(no_pdf_items)} 件)</h1>
<div class="pubmedx">
  <h2>📄 PubMedX — PubMed に日本語訳・インパクトファクターを表示するブラウザ拡張</h2>
  <p>PubMed の検索結果にその場で <strong>日本語訳</strong> と <strong>論文スコア</strong> を表示します。Chrome / Edge / Firefox 対応、無料。文献収集の効率が大幅に上がります。</p>
  <a class="btn" href="https://www.emuyn.net/pubmedx/index" target="_blank">PubMedX を入手する →</a>
</div>
<div class="notice">
  <strong>注意:</strong>
  PMC・Unpaywall などで無料公開されている論文であっても、
  自動ダウンロードはサイト側のボット対策によりブロックされることがあります。
  これらの論文はアブストラクトのみ自動保存済みです。全文評価を行うには PDF が必要です。<br><br>
  <strong>💡 大学・病院のネットワークからアクセスしている場合</strong>、機関契約により
  有料論文も無料でダウンロードできることがあります。以下のリンクを開いて PDF を入手してください。<br><br>
  ダウンロードした PDF を <code>保存先</code> に示すファイル名・場所に保存し、
  Claude Code に完了を伝えると二者協議が開始されます。
</div>
<table>
  <tr><th>論文情報</th><th>ダウンロードリンク</th></tr>
  {rows}
</table>
</body>
</html>"""

    out = TEMP_DIR / "manual_download.html"
    out.write_text(html, encoding="utf-8")
    return out


def main():
    print("=" * 50)
    print("医療論文 自動収集スクリプト")
    print("=" * 50)

    cfg = load_config()
    print(f"\n設定読み込み完了")
    print(f"  キーワード   : {cfg['query']}")
    print(f"  候補取得数   : {cfg['search_results']}")
    print(f"  処理件数上限 : {cfg['max_results']}")

    PDF_DIR.mkdir(parents=True, exist_ok=True)

    # 1. PubMed 検索
    print(f"\n検索中: {cfg['query']}")
    pmids = search_pubmed(cfg["query"], cfg["search_results"], cfg["email"])
    print(f"{len(pmids)} 件ヒット\n")

    # 2. メタデータ・DOI 一括取得
    print("メタデータを取得中...")
    meta = fetch_metadata_batch(pmids, cfg["email"])
    doi_map = get_doi_batch(pmids)

    # 3. iCite で被引用数一括取得
    print("iCite から被引用数を取得中...")
    icite = fetch_icite(pmids)

    # 4. SJR データ読み込み
    print("SJR データを読み込み中...")
    sjr_data = load_sjr_data()

    # 5. スコア算出・ソート → 上位 max_results 件を選択
    weights = {
        "citations_per_year": cfg["weight_citations_per_year"],
        "citation_count":     cfg["weight_citation_count"],
        "sjr":                cfg["weight_sjr"],
    }
    scored = compute_scores(pmids, meta, icite, sjr_data, weights)
    top = scored[:cfg["max_results"]]

    print(f"\nスコアリング完了: {len(pmids)} 件 → 上位 {len(top)} 件を処理\n")

    # 6. 上位から順に PDF 取得・登録
    no_pdf_items = []
    for rank, (pmid, score, _) in enumerate(top, 1):
        m = meta.get(pmid, {})
        doi = doi_map.get(pmid)
        print(f"[{rank}/{len(top)}] PMID {pmid}  スコア: {score:.3f}")
        print(f"    {m.get('title', '')[:70]}")

        pdf_url = check_unpaywall(doi, cfg["email"])
        if pdf_url:
            pdf_path = download_pdf(pdf_url, pmid)
            if not pdf_path:
                print(f"    ダウンロード失敗 (ボットブロックの可能性) → アブストラクトを取得")
                fetch_abstract(pmid, cfg["email"])
                no_pdf_items.append(_make_item(pmid, m, doi))
        else:
            print(f"    自動取得不可 → アブストラクトを取得")
            fetch_abstract(pmid, cfg["email"])
            no_pdf_items.append(_make_item(pmid, m, doi))

        generate_agent_prompt(pmid)
        register_refs_yaml(m, pmid, doi)
        time.sleep(0.4)

    auto_count = len(top) - len(no_pdf_items)

    if no_pdf_items:
        html_path = generate_manual_download_html(no_pdf_items)
        webbrowser.open(html_path.as_uri())

    print("\n" + "=" * 50)
    print(f"論文をすべて登録しました (自動取得: {auto_count} 件 / 手動入手が必要: {len(no_pdf_items)} 件)")
    print("=" * 50)


if __name__ == "__main__":
    main()
