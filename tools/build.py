#!/usr/bin/env python3
"""情報漏えい対策ガイド — 静的サイトビルダー（Python標準ライブラリのみ）

src/ にある原稿から docs/ を生成します。GitHub Pages は docs/ を配信します。
    python3 tools/build.py
"""
from __future__ import annotations

import hashlib
import html
import json
import re
import shutil
import tempfile
import uuid
from collections import Counter
from datetime import date
import urllib.parse
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
    ("delete", "退会・データ消去の進め方"),
    ("scams", "便乗詐欺の手口"),
    ("accounts", "パスワードとログインの守り方"),
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
    "カード情報（番号・有効期限など）": "t-danger",
    "カード情報": "t-danger",
    "認証トークン": "t-warn",
    "口座情報": "t-warn",
}
# 漏えい項目タグ → 「自分専用の対策」の選択肢
TAG_TO_PLAN = {
    "氏名": "address", "住所": "address", "電話番号": "phone", "メールアドレス": "email",
    "生年月日": "birth", "パスワード": "password", "本人確認書類の画像": "idimg",
    "パスポート情報": "idimg", "免許証番号": "idimg", "本人確認書類の番号": "idimg",
    "カード情報の一部": "card", "カード情報（番号・有効期限など）": "card", "口座情報": "bank", "購入・配送・利用履歴": "history",
    "家族情報": "family", "カード情報": "card", "認証トークン": "token", "保存ファイル・画像": "files",
}
STATUS = {
    "対象情報なし": ("s-unconfirmed", "対象に個人情報なし"),
    "確認": ("s-confirmed", "漏えい確認"),
    "可能性": ("s-possible", "可能性・おそれ"),
    "調査中": ("s-investigating", "調査中"),
    "未確認": ("s-investigating", "漏えい未確認"),
}
FILTER_KEYS = {
    "id": {"本人確認書類の画像", "パスポート情報", "免許証番号", "本人確認書類の番号"},
    "password": {"パスワード"},
    "name": {"氏名"}, "email": {"メールアドレス"}, "phone": {"電話番号"},
    "birth": {"生年月日"}, "token": {"認証トークン"}, "files": {"保存ファイル・画像"},
    "history": {"購入・配送・利用履歴"}, "family": {"家族情報"},
    "address": {"住所"},
    "money": {"カード情報の一部", "カード情報（番号・有効期限など）", "カード情報", "口座情報"},
}

CATEGORIES = {
    "retail": "小売・通販", "food": "飲食", "travel": "旅行・宿泊", "transport": "交通・配送",
    "finance": "金融・保険", "telecom_it": "通信・IT", "health": "医療・健康",
    "work_education": "人材・教育", "media_entertainment": "メディア・娯楽",
    "government": "行政・公共", "manufacturing": "製造・卸売", "energy": "エネルギー・インフラ",
    "real_estate": "不動産・住まい", "other": "その他",
}


def category_options(entries: list[dict]) -> str:
    counts = Counter(e["category"] for e in entries)
    options = [f'<option value="all">すべての事業種別（{len(entries)}件）</option>']
    for key, label in CATEGORIES.items():
        if counts[key]:
            options.append(f'<option value="{key}">{esc(label)}（{counts[key]}件）</option>')
    return "".join(options)


def check_date_label(iso: str | None) -> str:
    if not iso:
        return "確認日未記録"
    value = date.fromisoformat(iso)
    return f"{value.year}年{value.month}月{value.day}日確認"

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


def report_text(title: str) -> str:
    page = title.split("｜")[0]
    text = (
        f"@skikkh 「情報漏えい対策ガイド」の「{page}」で、誤りや古い情報を見つけました。\n\n"
        "（どこが違うか・正しい情報が載っているページのURL）\n"
    )
    return text


def report_url(title: str, canonical: str) -> str:
    """X の投稿画面を、ページ名とURLが入った状態で開くリンク"""
    return "https://x.com/intent/post?" + urllib.parse.urlencode({"text": report_text(title), "url": canonical})


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


def tel_href(tel: str) -> str:
    return "tel:" + re.sub(r"[^0-9+]", "", tel)


def contact_html(e: dict) -> str:
    c = e.get("contact")
    official = e.get("contact_source") or e.get("official") or (e["url"] if e["src"] == "公式" else None)
    src_link = (
        f'<a href="{esc(official)}" rel="noopener">公式発表で確認</a>' if official else ""
    )
    if not c:
        return (
            '<div class="contact contact-none"><span class="contact-title">公式の問い合わせ窓口</span>'
            "<p>公式発表に、本件専用の窓口の記載を確認できていません。会社の公式サイトを自分で開き、問い合わせ窓口を探してください。"
            + (f" {src_link}" if src_link else "")
            + "</p></div>"
        )
    rows = []
    if c.get("name"):
        rows.append(f'<li class="contact-name">{esc(c["name"])}</li>')
    for tel in c.get("tels", []):
        hours = f'<span class="contact-hours">{esc(c["hours"])}</span>' if c.get("hours") else ""
        rows.append(f'<li>電話 <a class="contact-tel" href="{tel_href(tel)}">{esc(tel)}</a>{hours}</li>')
    if not c.get("tels") and c.get("hours"):
        rows.append(f'<li>受付 {esc(c["hours"])}</li>')
    for mail in c.get("emails", []):
        rows.append(f'<li>メール <a href="mailto:{esc(mail)}">{esc(mail)}</a></li>')
    for f in c.get("forms", []):
        rows.append(f'<li><a href="{esc(f["url"])}" rel="noopener">{esc(f["label"])}</a></li>')
    note = f'<p class="contact-note">{esc(c["note"])}</p>' if c.get("note") else ""
    check = f'<p class="contact-check">{src_link}（{esc(check_date_label(e.get("contact_checked_on")))}）</p>' if src_link else ""
    return (
        '<div class="contact"><span class="contact-title">公式の問い合わせ窓口</span>'
        f'<ul>{"".join(rows)}</ul>{note}{check}</div>'
    )


def incident_id(e: dict) -> str:
    # 表示順・件数・注記・確認日が変わっても同じ事案を参照する。
    identity = json.dumps([e["org"], e.get("service", ""), e["date"]], ensure_ascii=False)
    return "i-" + hashlib.sha256(identity.encode("utf-8")).hexdigest()[:20]


def latest_announcement(e: dict) -> str:
    """date_labelに明記された公表・続報の日付だけを使う。確認日は使わない。"""
    initial = date.fromisoformat(e["date"])
    year = initial.year
    values = [initial]
    for match in re.finditer(r"(?:(20\d{2})年)?(\d{1,2})月(\d{1,2})日", e["date_label"]):
        if match[1]:
            year = int(match[1])
        try:
            values.append(date(year, int(match[2]), int(match[3])))
        except ValueError:
            continue
    return max(values).isoformat()


def incident_registry(entries: list[dict]) -> str:
    rows = []
    for e in entries:
        official = e.get("official") or (e["url"] if e["src"] == "公式" else "")
        attrs = {"id": incident_id(e), "org": e["org"], "service": e.get("service", ""),
                 "note": e.get("note", ""), "official": official,
                 "status": STATUS[e["status"]][1], "items": "、".join(e["items"])}
        rows.append("<span " + " ".join(f'data-{k}="{esc(v)}"' for k, v in attrs.items()) + "></span>")
    return '<div id="incident-data" hidden>' + "".join(rows) + "</div>"


def breach_cards(entries: list[dict]) -> str:
    out = []
    for e in sorted(entries, key=lambda x: (latest_announcement(x), x["date"], x["org"]), reverse=True):
        tags = e["items"]
        keys = sorted({k for k, v in FILTER_KEYS.items() if v & set(tags)})
        plan = [] if e["status"] == "対象情報なし" else (sorted({TAG_TO_PLAN[t] for t in tags if t in TAG_TO_PLAN}) or ["unknown"])
        st_cls, st_label = STATUS[e["status"]]
        tag_html = "".join(
            f'<li class="{TAG_CLASS.get(t, "")}">{esc(t)}</li>' if TAG_CLASS.get(t) else f"<li>{esc(t)}</li>"
            for t in tags
        )
        if not tags:
            tag_html = '<li>対象に個人情報は含まれないと公表</li>' if e["status"] == "対象情報なし" else '<li>対象項目は未公表</li>'
        search = " ".join([e["org"], e.get("service", ""), e.get("kana", "")])
        cls = "breach has-id" if "id" in keys else "breach"
        official = e.get("official") or (e["url"] if e["src"] == "公式" else None)
        links = [f'<a href="{esc(e["url"])}" rel="noopener">出典（{esc(e["src"])}）</a>']
        if plan:
            links.append(f'<a href="plan.html#incident={incident_id(e)}">自分の通知に合わせて対策を選ぶ</a>')
        service = f'<span class="muted">｜{esc(e["service"])}</span>' if e.get("service") else ""
        note = f'<p class="breach-note">{esc(e["note"])}</p>' if e.get("note") else ""
        out.append(
            f'<li class="{cls}" data-keys="{" ".join(keys)}" data-category="{e["category"]}" data-status="{e["status"]}" data-initial="{e["date"]}" data-latest="{latest_announcement(e)}" data-name="{esc(search)}" data-incident="{incident_id(e)}" data-search="{esc(search)}">'
            f'<div class="breach-top"><span>{esc(e["date_label"])} 公表</span>'
            f'<span class="status {st_cls}">{st_label}</span></div>'
            f'<p class="breach-name">{esc(e["org"])}{service}</p>'
            f'<p class="muted">事業種別：{esc(CATEGORIES[e["category"]])}</p>'
            f'<span class="breach-count">{esc(e["count"])}</span>'
            f'<ul class="tags" aria-label="漏えい（の可能性がある）項目">{tag_html}</ul>'
            f"{note}"
            f"{contact_html(e)}"
            f'<div class="breach-links">{"".join(links)}</div>'
            "</li>"
        )
    return '<ul class="breach-list" id="breach-list">' + "".join(out) + "</ul>"


HERO_RE = re.compile(
    r'\A\s*<p class="updated">.*?</p>\s*<h1>(?P<h1>.*?)</h1>\s*'
    r'(?P<lead><p class="lead">.*?</p>)?\s*(?:<p class="byline">.*?</p>)?',
    re.S,
)
TRUST = (
    '<ul class="trust" aria-label="このページについて">'
    "<li>事実には出典を明記</li>"
    "<li>最終更新 {updated}</li>"
    "</ul>"
)


def page_hero(slug: str, body: str, root: str) -> str:
    """各ページ冒頭（最終更新・h1・リード）を、トップと同じ見出し枠に組み立てる"""
    if slug == "index":
        return body
    label = dict(NAV).get(slug, "")
    crumbs = (
        f'<nav class="crumbs" aria-label="現在地"><a href="{root}index.html">トップ</a>'
        f'<span aria-hidden="true">›</span><span aria-current="page">{esc(label)}</span></nav>'
    ) if label else ""
    m = HERO_RE.match(body)
    if m:
        hero = (
            f'{crumbs}<header class="hero page-hero">'
            '<p class="eyebrow">2026年10月版 市民のための自衛ガイド</p>'
            f'<h1>{m.group("h1")}</h1>{m.group("lead") or ""}'
            f'{TRUST.format(updated=UPDATED)}</header>'
        )
        return hero + body[m.end():]
    # 404 など：h1 だけ枠に入れる
    m = re.match(r"\A\s*<h1>(.*?)</h1>", body, re.S)
    if m:
        return f'<header class="hero page-hero"><h1>{m.group(1)}</h1></header>' + body[m.end():]
    return body


ALLOWED_TAGS = {
    "氏名", "住所", "電話番号", "メールアドレス", "生年月日", "性別", "会員ID", "パスワード",
    "本人確認書類の画像", "免許証番号", "パスポート情報", "本人確認書類の番号",
    "カード情報の一部", "カード情報（番号・有効期限など）", "カード情報", "認証トークン", "保存ファイル・画像", "口座情報", "購入・配送・利用履歴", "家族情報", "勤務先・所属",
    "その他（詳細は出典）", "マイナンバー（個人番号）",
}
CONTACT_KEYS = {"name", "tels", "hours", "emails", "forms", "note"}


def validate(entries: list[dict]) -> None:
    """データの誤りをビルド時に止める（毎時ルーティンの安全装置）"""
    errors = []
    seen = set()
    for i, e in enumerate(entries):
        where = f"#{i} {e.get('org', '?')}"
        for k in ("date", "date_label", "org", "count", "status", "url", "src", "category"):
            if not e.get(k):
                errors.append(f"{where}: {k} がありません")
        if e.get("date") and not re.fullmatch(r"20\d\d-\d\d-\d\d", e["date"]):
            errors.append(f"{where}: date は YYYY-MM-DD 形式にしてください")
        if e.get("status") not in STATUS:
            errors.append(f"{where}: status は {list(STATUS)} のいずれか")
        if e.get("category") not in CATEGORIES:
            errors.append(f"{where}: category は定義済みの事業種別を選んでください")
        for key in ("date", "source_checked_on", "contact_checked_on"):
            if e.get(key):
                try:
                    date.fromisoformat(e[key])
                except (ValueError, TypeError):
                    errors.append(f"{where}: {key} は有効な YYYY-MM-DD の日付にしてください")
        if e.get("src") not in ("公式", "報道"):
            errors.append(f"{where}: src は 公式 か 報道")
        if not isinstance(e.get("items"), list):
            errors.append(f"{where}: items は配列にしてください（未公表なら空配列）")
        for t in e.get("items", []) if isinstance(e.get("items"), list) else []:
            if t not in ALLOWED_TAGS:
                errors.append(f"{where}: 未知のタグ {t}")
        for k in ("url", "official", "contact_source"):
            if e.get(k) and not e[k].startswith("https://"):
                errors.append(f"{where}: {k} は https:// で始めてください")
        c = e.get("contact")
        if c is not None:
            if not isinstance(c, dict) or set(c) - CONTACT_KEYS:
                errors.append(f"{where}: contact のキーは {sorted(CONTACT_KEYS)} のみ")
            else:
                for tel in c.get("tels", []):
                    if not (re.fullmatch(r"0[0-9-]+", tel) and 10 <= len(re.sub(r"\D", "", tel)) <= 11):
                        errors.append(f"{where}: 電話番号の形式 {tel}")
                for m in c.get("emails", []):
                    if "@" not in m or " " in m:
                        errors.append(f"{where}: メールの形式 {m}")
                for f in c.get("forms", []):
                    if not f.get("url", "").startswith("https://") or not f.get("label"):
                        errors.append(f"{where}: forms は label と https の url が必要")
                if (c.get("tels") or c.get("emails") or c.get("forms")) and not (e.get("official") or e.get("src") == "公式"):
                    errors.append(f"{where}: 窓口を載せるときは公式発表のURL（official）が必要")
        key = (e.get("org"), e.get("service", ""), e.get("date"))
        if key in seen:
            errors.append(f"{where}: 重複しています")
        seen.add(key)
    if errors:
        raise SystemExit("breaches.json の検査に失敗しました:\n  " + "\n  ".join(errors))


def build_into(output: Path) -> tuple[int, int, str]:
    breaches = json.loads((SRC / "data" / "breaches.json").read_text(encoding="utf-8"))
    validate(breaches)
    pages = sorted((SRC / "pages").glob("*.html"))
    required = {s for s, _ in NAV} | {"404"}
    missing = required - {p.stem for p in pages}
    if missing:
        raise SystemExit(f"原稿がありません: {sorted(missing)}")
    (output / "assets").mkdir(parents=True)

    for f in (SRC / "assets").iterdir():
        if f.is_file():
            shutil.copy2(f, output / "assets" / f.name)

    ver = hashlib.sha256(
        (SRC / "assets" / "style.css").read_bytes() + (SRC / "assets" / "app.js").read_bytes()
    ).hexdigest()[:10]

    layout = (SRC / "layout.html").read_text(encoding="utf-8")
    replacements = {
        "{{breach_cards}}": breach_cards(breaches),
        "{{breach_total}}": str(len(breaches)),
        "{{category_options}}": category_options(breaches),
        "{{incident_registry}}": incident_registry(breaches),
        "{{updated_iso}}": UPDATED_ISO,
        "{{updated}}": UPDATED,
    }

    for p in pages:
        slug = p.stem
        meta, body = parse_page(p.read_text(encoding="utf-8"))
        for k, v in replacements.items():
            body = body.replace(k, v)
        body = page_hero(slug, body, BASE_PATH if slug == "404" else "")
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
            "report_url": esc(report_url(meta["title"], canonical)),
            "report_text": esc(report_text(meta["title"])),
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
        (output / f"{slug}.html").write_text(page, encoding="utf-8")

    urls = "".join(
        f"<url><loc>{BASE_URL if s == 'index' else BASE_URL + s + '.html'}</loc><lastmod>{UPDATED_ISO}</lastmod></url>"
        for s, _ in NAV
    )
    (output / "sitemap.xml").write_text(
        '<?xml version="1.0" encoding="UTF-8"?>\n'
        f'<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">{urls}</urlset>\n',
        encoding="utf-8",
    )
    (output / "robots.txt").write_text(f"User-agent: *\nAllow: /\nSitemap: {BASE_URL}sitemap.xml\n", encoding="utf-8")
    (output / ".nojekyll").write_text("", encoding="utf-8")
    return len(pages), len(breaches), ver


def main() -> None:
    # 生成中のエラーでは配信済みのdocsを触らない。
    with tempfile.TemporaryDirectory(prefix=".site-build-", dir=ROOT) as temp:
        stage = Path(temp) / "docs"
        page_count, breach_count, ver = build_into(stage)
        # 復元にも失敗した場合はバックアップを削除せず、回復可能なまま残す。
        previous = ROOT / (".site-previous-" + uuid.uuid4().hex)
        if OUT.exists():
            OUT.rename(previous)
        try:
            stage.rename(OUT)
        except BaseException:
            if previous.exists():
                previous.rename(OUT)
            raise
        if previous.exists():
            shutil.rmtree(previous)
    print(f"built {page_count} pages, {breach_count} breach entries -> {OUT.relative_to(ROOT)}/ (v={ver})")


if __name__ == "__main__":
    main()
