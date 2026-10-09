# 漏れた後の守り方

2026年秋に続いている国内の個人情報大量漏えいを受けて、**一人ひとりが今できる対策**を、効果の大きい順にまとめた静的サイトです。

公開URL（GitHub Pages）：https://skikkh.github.io/jp-security-announcement/

## 考え方

- 国や企業の呼びかけを並べ直すのではなく、「盗まれた情報を攻撃者がどうお金に変えるか」から逆算して、断ち切る場所を選んでいます（`threat.html`）。
- 事実には出典を付け、推測や見立ては「エンジニアの見立て」と明記しています。
- 外部スクリプト、アクセス解析、広告、Cookie は使いません。コンテンツセキュリティポリシーで、自サイト以外のスクリプトを禁止しています。チェックの記録は閲覧者の端末の localStorage にだけ保存します。

## ページ

| ファイル | 内容 |
| --- | --- |
| `index.html` | 現状、3つの原則、今日の30分でやること |
| `plan.html` | 漏れた項目を選ぶと、自分専用の対策リストを作る（URLで共有可） |
| `id.html` | 運転免許証・身分証の画像が漏れたら |
| `delete.html` | 退会・削除・書き換え（UPDATE/INSERT）の真実と、消去請求文の作成 |
| `scams.html` | 便乗詐欺の手口と、見分けずに防ぐ方法 |
| `accounts.html` | アカウントの守りを固める（優先順位、パスキー、エイリアス、振込限度額） |
| `family.html` | 家族・高齢の親を守る（印刷用カード付き） |
| `breaches.html` | 主な漏えい事案の一覧（絞り込み可） |
| `threat.html` | なぜこの対策なのか（攻撃者の換金ルート） |
| `help.html` | 被害に遭ったら・相談窓口 |
| `about.html` | このサイトについて・出典・更新履歴 |

## 構成

```
src/
  layout.html          共通レイアウト（ヘッダー、フッター、CSP）
  pages/*.html         各ページの原稿（先頭の <!--meta ... --> にタイトルと説明）
  data/breaches.json   漏えい事案のデータ
  assets/              style.css, app.js, icon.svg, og.png
tools/
  build.py             src/ から docs/ を生成（Python 標準ライブラリのみ）
  og.html, make-og.mjs OGP画像の生成（Playwright）
docs/                  生成物。GitHub Pages はここを配信
```

## 更新のしかた

```sh
# 原稿やデータを編集したら
python3 tools/build.py

# 手元で確認
python3 -m http.server -d docs 8000
```

- 最終更新日は `tools/build.py` の `UPDATED` と `UPDATED_ISO` を書き換えます。
- 漏えい事案は `src/data/breaches.json` に追記します。`items` のタグは `tools/build.py` の `TAG_CLASS` と `TAG_TO_PLAN` に合わせてください。`status` は「確認」「可能性」「調査中」のいずれかです。
- `docs/` は生成物ですが、GitHub Pages が配信するためコミットします。編集は必ず `src/` 側で行ってください。

## 公開（GitHub Pages）

1. このブランチを `main` にマージする（または `main` として使う）
2. リポジトリの Settings → Pages → Build and deployment で、Source を「Deploy from a branch」、Branch を `main`、フォルダを `/docs` にする
3. 数分後に https://skikkh.github.io/jp-security-announcement/ で公開されます

別のURLで公開する場合は、`tools/build.py` の `BASE_URL` と `BASE_PATH` を変更してビルドし直してください。

## 誤りの報告

事実の誤りや古くなった情報は、Issues でお知らせください。
