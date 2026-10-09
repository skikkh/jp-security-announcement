"""生成ページの内部リンクと参照先を確認する（外部通信なし）。"""
from html.parser import HTMLParser
from pathlib import Path
from urllib.parse import urlparse, unquote

ROOT = Path(__file__).resolve().parent.parent / "docs"
BASE = "/jp-security-announcement/"

class Page(HTMLParser):
    def __init__(self):
        super().__init__()
        self.ids = set()
        self.links = []
    def handle_starttag(self, tag, attrs):
        attrs = dict(attrs)
        if attrs.get("id"):
            self.ids.add(attrs["id"])
        for name in ("href", "src"):
            if attrs.get(name):
                self.links.append(attrs[name])

pages = {}
for path in ROOT.glob("*.html"):
    page = Page()
    page.feed(path.read_text())
    pages[path.name] = page
errors = []
checked = 0
for name, page in pages.items():
    for link in page.links:
        url = urlparse(link)
        if url.scheme or url.netloc:
            if url.scheme not in ("https", "mailto", "tel"):
                errors.append(f"{name}: 使用できないリンク {link}")
            continue
        target = unquote(url.path)
        if target.startswith(BASE):
            target = target[len(BASE):]
        elif target.startswith("/"):
            errors.append(f"{name}: サイト外の絶対パス {link}")
            continue
        target = target or name
        path = (ROOT / target).resolve()
        if not path.is_relative_to(ROOT.resolve()) or not path.is_file():
            errors.append(f"{name}: 参照先がありません {link}")
        elif url.fragment and "=" not in url.fragment and path.name in pages and unquote(url.fragment) not in pages[path.name].ids:
            errors.append(f"{name}: ページ内の参照先がありません {link}")
        checked += 1
if errors:
    raise SystemExit("\n".join(errors))
print(f"内部参照 {checked} 件を確認")
