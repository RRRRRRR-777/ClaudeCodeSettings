#!/usr/bin/env python3
"""解説ページ(HTML)を Chrome で描画して検証する。

使い方: python3 verify_page.py <HTMLのパス>

標準出力にJSONを1つ出力する。ok が true のとき終了コード0、それ以外は1。
Chrome は外部コマンドとして呼ぶ(サンドボックスの外で実行すること)。
"""
import json
import re
import shutil
import subprocess
import sys
import tempfile
from collections import Counter
from html.parser import HTMLParser
from pathlib import Path

CHROME = "/Applications/Google Chrome.app/Contents/MacOS/Google Chrome"
TIMEOUT_SEC = 90
MAX_SHOT_HEIGHT = 16000
DEFAULT_SHOT_HEIGHT = 2000
PLACEHOLDERS = ("{{TITLE}}", "{{BODY}}")


class BodyAttrParser(HTMLParser):
    """dump-dom の結果から <body> の属性だけを取り出す。"""

    def __init__(self):
        super().__init__()
        self.body_attrs = {}

    def handle_starttag(self, tag, attrs):
        if tag == "body" and not self.body_attrs:
            self.body_attrs = {k: (v or "") for k, v in attrs}


class IdClassCollector(HTMLParser):
    """ソースから id 属性の一覧と、class に "id" を持つ要素の有無を集める。"""

    def __init__(self):
        super().__init__()
        self.ids = []
        self.has_id_badge = False

    def handle_starttag(self, tag, attrs):
        for key, value in attrs:
            if key == "id" and value:
                self.ids.append(value)
            if key == "class" and value and "id" in value.split():
                self.has_id_badge = True


def run_chrome(args, profile_dir):
    cmd = [
        CHROME, "--headless=new", "--disable-gpu", "--no-first-run",
        f"--user-data-dir={profile_dir}", *args,
    ]
    return subprocess.run(cmd, capture_output=True, text=True, timeout=TIMEOUT_SEC)


def strip_non_content(source):
    """style・script・コメントを除く(テンプレートの説明文を解析対象にしないため)。"""
    text = re.sub(r"<!--.*?-->", "", source, flags=re.S)
    text = re.sub(r"<style\b.*?</style>", "", text, flags=re.S | re.I)
    return re.sub(r"<script\b.*?</script>", "", text, flags=re.S | re.I)


def to_int(value):
    try:
        return int(value)
    except (TypeError, ValueError):
        return None


def analyze_source(source, warnings):
    """ソースだけで分かる警告を集める。"""
    leftover = [p for p in PLACEHOLDERS if p in source]
    for p in leftover:
        warnings.append(f"プレースホルダ {p} が残っている")

    content = strip_non_content(source)

    pattern = r'<(\w+)\b[^>]*class="[^"]*\bmermaid\b[^"]*"[^>]*>(.*?)</\1>'
    for index, match in enumerate(re.finditer(pattern, content, flags=re.S), start=1):
        body = match.group(2)
        if re.search(r"<br", body, flags=re.I) or re.search(r"&lt;br", body, flags=re.I):
            warnings.append(f"Mermaid {index}番目の記法に <br> がある(ラベルを短くし説明は .figcap へ)")
        if re.search(r"<b>", body, flags=re.I) or re.search(r"&lt;b&gt;", body, flags=re.I):
            warnings.append(f"Mermaid {index}番目の記法に <b> がある(ラベルを短くし説明は .figcap へ)")

    collector = IdClassCollector()
    collector.feed(content)
    for name, count in Counter(collector.ids).items():
        if count > 1:
            warnings.append(f"id 属性が重複している: {name} ({count}回)")
    if not collector.has_id_badge:
        warnings.append("識別子(.id)の要素が1つも無い(D-/U-/Q- の識別子を振ること)")
    return leftover


def main():
    if len(sys.argv) != 2:
        print("使い方: python3 verify_page.py <HTMLのパス>", file=sys.stderr)
        return 2

    html_path = Path(sys.argv[1]).resolve()
    if not html_path.is_file():
        print(f"ファイルが無い: {html_path}", file=sys.stderr)
        return 2

    warnings = []
    leftover = analyze_source(html_path.read_text(encoding="utf-8"), warnings)

    result = {
        "ok": False,
        "mermaidReady": None,
        "mermaidSources": 0,
        "mermaidRendered": 0,
        "pageHeight": None,
        "warnings": warnings,
        "screenshot": None,
    }
    mermaid_errors = 0
    chrome_ran = False
    url = html_path.as_uri()
    profiles = []

    try:
        # 1. DOM を取得して状態属性を読む
        profile = tempfile.mkdtemp(prefix="verify-page-")
        profiles.append(profile)
        dom = run_chrome(["--virtual-time-budget=20000", "--dump-dom", url], profile)
        if dom.returncode == 0 and dom.stdout.strip():
            chrome_ran = True
            parser = BodyAttrParser()
            parser.feed(dom.stdout)
            attrs = parser.body_attrs
            ready = attrs.get("data-mermaid-ready")
            result["mermaidReady"] = None if ready is None else ready == "true"
            result["mermaidSources"] = to_int(attrs.get("data-mermaid-sources")) or 0
            result["mermaidRendered"] = to_int(attrs.get("data-mermaid-rendered")) or 0
            mermaid_errors = to_int(attrs.get("data-mermaid-errors")) or 0
            result["pageHeight"] = to_int(attrs.get("data-page-height"))
            if mermaid_errors:
                warnings.append(f"Mermaid の描画エラーが {mermaid_errors} 件ある(ページ内に原因が表示されている)")
        else:
            warnings.append("Chrome の DOM 取得に失敗した(サンドボックス内で実行していないか確認): "
                            + dom.stderr.strip()[-300:])

        if result["pageHeight"] is None:
            warnings.append("pageHeight が取得できない(テンプレート末尾の高さ出力 script を消していないか確認)")

        # 2. スクリーンショットを html の隣に保存する
        if chrome_ran:
            height = min(result["pageHeight"], MAX_SHOT_HEIGHT) if result["pageHeight"] else DEFAULT_SHOT_HEIGHT
            png = html_path.with_suffix(".png")
            profile = tempfile.mkdtemp(prefix="verify-page-")
            profiles.append(profile)
            shot = run_chrome([
                "--virtual-time-budget=20000", "--hide-scrollbars",
                f"--window-size=1280,{height}", f"--screenshot={png}", url,
            ], profile)
            if shot.returncode == 0 and png.is_file():
                result["screenshot"] = str(png)
            else:
                warnings.append("スクリーンショットの保存に失敗した: " + shot.stderr.strip()[-300:])
    except subprocess.TimeoutExpired:
        warnings.append(f"Chrome が {TIMEOUT_SEC} 秒でタイムアウトした")
    except OSError as e:
        warnings.append(f"Chrome を起動できない: {e}")
    finally:
        for p in profiles:
            shutil.rmtree(p, ignore_errors=True)

    sources = result["mermaidSources"]
    result["ok"] = bool(
        chrome_ran
        and not leftover
        and (sources == 0 or result["mermaidReady"] is True)
        and result["mermaidRendered"] == sources
        and mermaid_errors == 0
    )
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 0 if result["ok"] else 1


if __name__ == "__main__":
    sys.exit(main())
