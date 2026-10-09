"""検証した固定バイト列を、GitHub署名付きコミットとしてmainへ追記する。"""
import sys
if not sys.flags.isolated:
    raise SystemExit('python3 -I tools/publish_signed.py で起動してください')

import argparse
import base64
import hashlib
import json
import re
import subprocess
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
REPO = 'skikkh/jp-security-announcement'


def run(*args):
    return subprocess.check_output(args, cwd=ROOT, text=True).strip()


def api(path):
    return json.loads(run('gh', 'api', path))


def base_objects():
    rows = subprocess.check_output(['git', 'ls-tree', '-r', '-z', 'HEAD'], cwd=ROOT)
    return {row.split(b'\t', 1)[1].decode(): row.split(b'\t', 1)[0].split()[2].decode()
            for row in rows.split(b'\0') if row}


def blob_oid(data):
    return hashlib.sha1(b'blob ' + str(len(data)).encode() + b'\0' + data).hexdigest()


def changed_paths(blobs, original):
    return sorted(name for name in set(blobs) | set(original)
                  if blobs.get(name) is None or blob_oid(blobs[name]) != original.get(name))


def capture():
    names = subprocess.check_output(['git', 'ls-files', '-z'], cwd=ROOT).decode().split('\0')
    blobs = {}
    for name in filter(None, names):
        path = ROOT / name
        if name.startswith(('.env', '.git/')) or path.is_symlink() or not path.resolve().is_relative_to(ROOT):
            raise SystemExit('公開できないパスです: ' + name)
        blobs[name] = path.read_bytes() if path.is_file() else None
    return blobs


def check_scope(paths, all_tracked, blobs):
    if all_tracked:
        return
    safe = {'src/data/breaches.json', 'src/pages/about.html', 'tools/build.py', 'tools/pending-notices.json'}
    outputs = {'docs/' + x + '.html' for x in ('index', 'about', 'accounts', 'breaches', 'delete', 'family', 'help', 'id', 'plan', 'scams', 'threat', '404')}
    outputs.update({'docs/assets/' + x for x in ('app.js', 'style.css', 'og.png', 'icon.svg')})
    outputs.update({'docs/robots.txt', 'docs/sitemap.xml', 'docs/.nojekyll'})
    if any(x not in safe | outputs for x in paths):
        raise SystemExit('通常更新の範囲を越えています。実装変更は独立確認したmanifestを指定してください')
    if 'tools/build.py' in paths:
        before = run('git', 'show', 'HEAD:tools/build.py')
        after = blobs['tools/build.py'].decode().strip()
        pattern = r'^UPDATED(?:_ISO)? = "[^"\n]*"$'
        if len(re.findall(pattern, before, re.M)) != 2 or len(re.findall(pattern, after, re.M)) != 2 or re.sub(pattern, '更新日', before, flags=re.M) != re.sub(pattern, '更新日', after, flags=re.M):
            raise SystemExit('通常更新ではビルドの更新日以外を変更できません')
    if 'src/pages/about.html' in paths:
        before = run('git', 'show', 'HEAD:src/pages/about.html')
        after = blobs['src/pages/about.html'].decode().strip()
        pattern = r'(<h2 id="history">[^<]*</h2>\s*<ul>)[\s\S]*?(</ul>)'
        if len(re.findall(pattern, before)) != 1 or len(re.findall(pattern, after)) != 1 or re.sub(pattern, r'\1更新履歴\2', before) != re.sub(pattern, r'\1更新履歴\2', after):
            raise SystemExit('通常更新ではaboutの更新履歴以外を変更できません')
        old_body, new_body = re.search(pattern, before).group(0), re.search(pattern, after).group(0)
        old_rows = old_body[old_body.index('<ul>') + 4:-5].strip()
        new_rows = new_body[new_body.index('<ul>') + 4:-5].strip()
        if not new_rows.endswith(old_rows):
            raise SystemExit('通常更新では既存の履歴を保持し、先頭に追加してください')
        added = new_rows[:-len(old_rows)].strip() if old_rows else new_rows
        if added and not re.fullmatch(r'(?:<li>20\d{2}年\d{1,2}月\d{1,2}日：[^<>]+</li>\s*)+', added):
            raise SystemExit('追加履歴は日付付きの文章だけです。HTMLや外部リンクを追加できません')


def check_reviewed(blobs, args, expected):
    if not args.all_tracked:
        return
    if not args.reviewed_manifest:
        raise SystemExit('実装全体の公開には、独立確認した --reviewed-manifest が必要です')
    source = Path(args.reviewed_manifest).resolve()
    if source.is_relative_to(ROOT):
        raise SystemExit('監査manifestは公開リポジトリの外に保存してください')
    manifest = json.loads(source.read_text())
    if manifest.get('base_sha') != expected:
        raise SystemExit('監査manifestの基準mainが一致しません')
    approved = manifest.get('files', {})
    if set(blobs) != set(approved):
        raise SystemExit('監査manifestとファイル一覧が一致しません')
    for name, data in blobs.items():
        if data is None or approved[name] != hashlib.sha256(data).hexdigest():
            raise SystemExit('監査manifestと固定バイト列が一致しません: ' + name)


def build_snapshot(blobs):
    # 未追跡ファイルや、検査後に書き換えられた原稿を実行・生成に取り込まない。
    with tempfile.TemporaryDirectory(prefix='jp-security-publish-') as folder:
        fixture = Path(folder)
        for name, data in blobs.items():
            if data is not None:
                path = fixture / name
                path.parent.mkdir(parents=True, exist_ok=True)
                path.write_bytes(data)
        for command in (['python3', '-I', 'tools/build.py'], ['node', '--check', 'src/assets/app.js'], ['python3', '-I', 'tools/check_site.py']):
            subprocess.run(command, cwd=fixture, check=True, stdout=subprocess.PIPE)
        result = {name: data for name, data in blobs.items() if not name.startswith('docs/')}
        result.update({'docs/' + p.relative_to(fixture / 'docs').as_posix(): p.read_bytes()
                       for p in (fixture / 'docs').rglob('*') if p.is_file()})
        return result


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--message', required=True)
    parser.add_argument('--dry-run', action='store_true')
    parser.add_argument('--all-tracked', action='store_true')
    parser.add_argument('--reviewed-manifest')
    args = parser.parse_args()
    if run('git', 'remote', 'get-url', 'origin') not in ('https://github.com/' + REPO + '.git', 'git@github.com:' + REPO + '.git'):
        raise SystemExit('対象リポジトリが一致しません')
    actor = api('user')
    if actor['login'] != 'skikkh' or actor['id'] != 16469483:
        raise SystemExit('認証された所有者が一致しません')
    run('git', 'fetch', 'origin', 'refs/heads/main:refs/remotes/origin/main')
    expected = run('git', 'rev-parse', 'origin/main')
    if run('git', 'rev-parse', 'HEAD') != expected:
        raise SystemExit('最新mainをローカルへ統合してから実行してください')
    if run('git', 'diff', '--name-only', '--diff-filter=U'):
        raise SystemExit('未解決の競合があります')
    original = base_objects()
    captured = capture()
    check_scope(changed_paths(captured, original), args.all_tracked, captured)
    check_reviewed(captured, args, expected)
    blobs = build_snapshot(captured)
    paths = changed_paths(blobs, original)
    check_scope(paths, args.all_tracked, blobs)
    check_reviewed(blobs, args, expected)
    if not paths:
        print('変更なし')
        return
    additions = [{'path': name, 'contents': base64.b64encode(blobs[name]).decode()} for name in paths if blobs.get(name) is not None]
    deletions = [{'path': name} for name in paths if blobs.get(name) is None]
    info = {'expected_head': expected, 'files': paths, 'actor': actor['login']}
    if args.dry_run:
        print(json.dumps(info, ensure_ascii=False))
        return
    query = 'mutation($input:CreateCommitOnBranchInput!){createCommitOnBranch(input:$input){commit{oid url signature{isValid state}}}}'
    body = {'query': query, 'variables': {'input': {'branch': {'repositoryNameWithOwner': REPO, 'branchName': 'main'}, 'expectedHeadOid': expected, 'message': {'headline': args.message}, 'fileChanges': {'additions': additions, 'deletions': deletions}}}}
    response = subprocess.run(['gh', 'api', 'graphql', '--input', '-'], cwd=ROOT, input=json.dumps(body), text=True, capture_output=True)
    try:
        data = json.loads(response.stdout)
    except json.JSONDecodeError:
        raise SystemExit('APIの成否を確認できません。再実行する前にmainの履歴を確認してください')
    if data.get('errors'):
        raise SystemExit('; '.join(e.get('message', 'APIエラー') for e in data['errors']))
    if response.returncode:
        raise SystemExit('API呼び出しに失敗しました。再実行する前にmainの履歴を確認してください')
    commit = data['data']['createCommitOnBranch']['commit']
    verification = api('repos/' + REPO + '/commits/' + commit['oid'])['commit']['verification']
    print(json.dumps({**info, 'commit': commit['oid'], 'url': commit['url'], 'verified': verification['verified'], 'reason': verification['reason']}, ensure_ascii=False))
    if not verification['verified']:
        raise SystemExit('コミットは作成されましたが署名確認に失敗しました。再作成せず原因を確認してください')
    run('git', 'fetch', 'origin', 'refs/heads/main:refs/remotes/origin/main')
    for name in paths:
        path = ROOT / name
        current = path.read_bytes() if path.is_file() else None
        published = blobs.get(name)
        if current != captured.get(name) and current != published:
            raise SystemExit('公開後にローカル変更があります。作成済みSHAを確認して統合してください: ' + name)
    for name in paths:
        path = ROOT / name
        if blobs.get(name) is not None:
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_bytes(blobs[name])
        elif path.exists():
            path.unlink()
    run('git', 'reset', '--mixed', commit['oid'])


if __name__ == '__main__':
    main()
