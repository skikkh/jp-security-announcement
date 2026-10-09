#!/usr/bin/env python3
"""漏れた後の守り方 — 静的サイトビルダー（Python標準ライブラリのみ）

src/ にある原稿から docs/ を生成します。GitHub Pages は docs/ を配信します。
    python3 tools/build.py
"""
from __future__ import annotations

import hashlib
import html
import json
import re
import shutil
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
SRC = ROOT / "src"
OUT = ROOT / "docs"

BASE_URL = "https://skikkh.github.io/jp-security-announcement/"
BASE_PATH = "/jp-security-announcement/"
UPDATED = "2026年10月9日"
UPDATED_ISO = "2026-10-09"

# (slug, ナビ表示名)
NAV = [
    ("index", "トップ"),
    ("plan", "自分専用の対策を作る"),
    ("id", "免許証・身分証が漏れたら"),
    ("delete", "退会・削除・書き換えの真実"),
    ("scams", "便乗詐欺の手口"),
    ("accounts", "アカウントの守りを固める"),
    ("family", "家族・高齢の親を守る"),
    ("breaches", "主な漏えい事案"),
    ("threat", "なぜこの対策なのか"),
    ("help", "被害に遭ったら・相談窓口"),
    ("about", "このサイトについて"),
]

# 漏えい項目タグ → 表示クラス
TAG_CLASS = {
    "本人確認書類の画像": "t-danger",
    "パスポート情報": "t-danger",
    "免許証番号": "t-danger",
    "本人確認書類の番号": "t-danger",
    "パスワード": "t-warn",
    "カード情報の一部": "t-warn",
    "口座情報": "t-warn",
}
# 漏えい項目タグ → 「自分専用の対策」の選択肢
TAG_TO_PLAN = {
    "氏名": "address", "住所": "address", "電話番号": "phone", "メールアドレス": "email",
    "生年月日": "birth", "パスワード": "password", "本人確認書類の画像": "idimg",
    "パスポート情報": "idimg", "免許証番号": "idimg", "本人確認書類の番号": "idimg",
    "カード情報の一部": "card", "口座情報": "bank", "購入・配送・利用履歴": "history",
    "家族情報": "family",
}
STATUS = {
    "確認": ("s-confirmed", "漏えい確認"),
    "可能性": ("s-possible", "可能性・おそれ"),
    "調査中": ("s-investigating", "調査中"),
}
FILTER_KEYS = {
    "id": {"本人確認書類の画像", "パスポート情報", "免許証番号", "本人確認書類の番号"},
    "password": {"パスワード"},
    "address": {"住所"},
    "money": {"カード情報の一部", "口座情報"},
}

META_RE = re.compile(r"\A\s*<!--meta\s*\n(.*?)\n-->\s*\n", re.S)


def esc(s: str) -> str:
    return html.escape(s, quote=True)


# ヘッダーに常に出す主要ページ（PC幅のみ）
PRIMARY = [
    ("plan", "対策を作る"),
    ("id", "免許証が漏れたら"),
    ("scams", "詐欺の手口"),
    ("help", "被害に遭ったら"),
]


def nav_primary_html(current: str, root: str) -> str:
    items = []
    for slug, label in PRIMARY:
        cur = ' aria-current="page"' if slug == current else ""
        items.append(f'<li><a href="{root}{slug}.html"{cur}>{esc(label)}</a></li>')
    return "<ul>" + "".join(items) + "</ul>"


def nav_html(current: str, root: str) -> str:
    items = []
    for slug, label in NAV:
        cur = ' aria-current="page"' if slug == current else ""
        items.append(f'<li><a href="{root}{slug}.html"{cur}>{esc(label)}</a></li>')
    return "<ul>" + "".join(items) + "</ul>"


def parse_page(text: str) -> tuple[dict, str]:
    m = META_RE.match(text)
    if not m:
        raise SystemExit("meta block missing")
    meta = {}
    for line in m.group(1).splitlines():
        if not line.strip():
            continue
        k, _, v = line.partition(":")
        meta[k.strip()] = v.strip()
    return meta, text[m.end():]


def breach_cards(entries: list[dict]) -> str:
    out = []
    for e in sorted(entries, key=lambda x: x["date"], reverse=True):
        tags = e["items"]
        keys = sorted({k for k, v in FILTER_KEYS.items() if v & set(tags)})
        plan = sorted({TAG_TO_PLAN[t] for t in tags if t in TAG_TO_PLAN})
        st_cls, st_label = STATUS[e["status"]]
        tag_html = "".join(
            f'<li class="{TAG_CLASS.get(t, "")}">{esc(t)}</li>' if TAG_CLASS.get(t) else f"<li>{esc(t)}</li>"
            for t in tags
        )
        search = " ".join([e["org"], e.get("service", ""), e.get("kana", "")])
        cls = "breach has-id" if "id" in keys else "breach"
        links = [f'<a href="{esc(e["url"])}" rel="noopener">出典（{esc(e["src"])}）</a>']
        if plan:
            links.append(f'<a href="plan.html#items={",".join(plan)}">この漏えいの対策を見る</a>')
        service = f'<span class="muted">｜{esc(e["service"])}</span>' if e.get("service") else ""
        note = f'<p class="breach-note">{esc(e["note"])}</p>' if e.get("note") else ""
        out.append(
            f'<li class="{cls}" data-keys="{" ".join(keys)}" data-search="{esc(search)}">'
            f'<div class="breach-top"><span>{esc(e["date_label"])} 公表</span>'
            f'<span class="status {st_cls}">{st_label}</span></div>'
            f'<p class="breach-name">{esc(e["org"])}{service}</p>'
            f'<span class="breach-count">{esc(e["count"])}</span>'
            f'<ul class="tags" aria-label="漏えい（の可能性がある）項目">{tag_html}</ul>'
            f"{note}"
            f'<div class="breach-links">{"".join(links)}</div>'
            "</li>"
        )
    return '<ul class="breach-list" id="breach-list">' + "".join(out) + "</ul>"


def main() -> None:
    if OUT.exists():
        shutil.rmtree(OUT)
    (OUT / "assets").mkdir(parents=True)

    for f in (SRC / "assets").iterdir():
        if f.is_file():
            shutil.copy2(f, OUT / "assets" / f.name)

    ver = hashlib.sha256(
        (SRC / "assets" / "style.css").read_bytes() + (SRC / "assets" / "app.js").read_bytes()
    ).hexdigest()[:10]

    layout = (SRC / "layout.html").read_text(encoding="utf-8")
    breaches = json.loads((SRC / "data" / "breaches.json").read_text(encoding="utf-8"))
    replacements = {
        "{{breach_cards}}": breach_cards(breaches),
        "{{breach_total}}": str(len(breaches)),
        "{{updated}}": UPDATED,
    }

    pages = sorted((SRC / "pages").glob("*.html"))
    for p in pages:
        slug = p.stem
        meta, body = parse_page(p.read_text(encoding="utf-8"))
        for k, v in replacements.items():
            body = body.replace(k, v)
        is_404 = slug == "404"
        root = BASE_PATH if is_404 else ""
        canonical = BASE_URL if slug == "index" else f"{BASE_URL}{slug}.html"
        page = layout
        fields = {
            "title": esc(meta["title"]),
            "og_title": esc(meta.get("og_title", meta["title"])),
            "description": esc(meta["description"]),
            "canonical": canonical,
            "base_url": BASE_URL,
            "root": root,
            "ver": ver,
            "slug": slug,
            "body_class": (" " + meta["body_class"]) if meta.get("body_class") else "",
            "updated": UPDATED,
            "nav": nav_html(slug, root),
            "nav_primary": nav_primary_html(slug, root),
            "nav_footer": nav_html(slug, root),
            "content": body.strip(),
        }
        for k, v in fields.items():
            page = page.replace("{{" + k + "}}", v)
        if is_404:
            page = page.replace('href="plan.html', f'href="{BASE_PATH}plan.html')
        leftover = re.findall(r"\{\{[a-z_]+\}\}", page)
        if leftover:
            raise SystemExit(f"{p.name}: unresolved placeholders {leftover}")
        (OUT / f"{slug}.html").write_text(page, encoding="utf-8")

    urls = "".join(
        f"<url><loc>{BASE_URL if s == 'index' else BASE_URL + s + '.html'}</loc><lastmod>{UPDATED_ISO}</lastmod></url>"
        for s, _ in NAV
    )
    (OUT / "sitemap.xml").write_text(
        '<?xml version="1.0" encoding="UTF-8"?>\n'
        f'<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">{urls}</urlset>\n',
        encoding="utf-8",
    )
    (OUT / "robots.txt").write_text(f"User-agent: *\nAllow: /\nSitemap: {BASE_URL}sitemap.xml\n", encoding="utf-8")
    (OUT / ".nojekyll").write_text("", encoding="utf-8")
    print(f"built {len(pages)} pages, {len(breaches)} breach entries -> {OUT.relative_to(ROOT)}/ (v={ver})")


if __name__ == "__main__":
    main()
