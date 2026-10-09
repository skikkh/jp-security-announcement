"""公開窓口の宛先が別ホスト・追加受信者に解釈される反例を確認する。"""
import copy
import importlib.util
import json
from pathlib import Path
import unittest
import urllib.parse

ROOT = Path(__file__).resolve().parent.parent
spec = importlib.util.spec_from_file_location('site_builder', ROOT / 'tools/build.py')
build = importlib.util.module_from_spec(spec)
spec.loader.exec_module(build)


class ContactValidation(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.rows = json.loads((ROOT / 'src/data/breaches.json').read_text())
        cls.entry = next(e for e in cls.rows if e.get('contact'))

    def test_current_notices_remain_valid(self):
        build.validate(self.rows)
        for entry in self.rows:
            for address in (entry.get('contact') or {}).get('emails', []):
                parsed = urllib.parse.urlsplit(build.mailto_href(address))
                self.assertEqual(parsed.scheme, 'mailto')
                self.assertEqual(parsed.query, '')
                self.assertEqual(parsed.fragment, '')

    def test_bad_url_is_rejected_in_every_copy(self):
        attacks = [
            'https://trusted.example@attacker.invalid/report',
            'https://trusted.example\n@attacker.invalid/report',
            'https://trusted.example/\u0085report',
            'https://trusted.example/\u009freport',
            'https://trusted.example\\@attacker.invalid/report',
            'https://trusted.example%40attacker.invalid/report',
            'https://trusted.example:443:80/report',
            'https://localhost/admin', 'https://host.local/admin',
            'https://127.0.0.1/admin', 'https://[::1]/admin',
            'https://[::ffff:127.0.0.1]/admin', 'https://10.0.0.1/admin',
            'https://224.0.0.1/admin', 'https://[ff02::1]/admin',
            'https://2130706433/admin', 'https://0177.0.0.1/admin',
            'https://0x7f000001/admin', 'https://127。0。0。1/admin',
            'javascript:alert(1)', 'http://trusted.example/report', None, 42,
        ]
        for value in attacks:
            self.assertFalse(build.valid_https_url(value), value)
            for field in ('url', 'official', 'contact_source', 'form'):
                with self.subTest(value=value, field=field):
                    entry = copy.deepcopy(self.entry)
                    if field == 'form':
                        entry['contact']['forms'] = [{'label': '検証用', 'url': value}]
                    else:
                        entry[field] = value
                    if value is None and field != 'form':
                        # 任意fieldの未指定は許可。必須urlの欠落は別の検査で拒否。
                        if field != 'url':
                            continue
                    with self.assertRaises(SystemExit):
                        build.validate([entry])

    def test_mail_cannot_add_headers_or_another_recipient(self):
        attacks = [
            'help@trusted.example?bcc=collector@attacker.invalid',
            'help@trusted.example?subject=x&bcc=collector@attacker.invalid',
            'help@trusted.example,collector@attacker.invalid',
            'help@trusted.example;collector@attacker.invalid',
            'help@trusted.example%3Fbcc%3Dcollector%40attacker.invalid',
            'help@trusted.example%0D%0ABcc%3Acollector@attacker.invalid',
            'help@trusted.example\n?bcc=collector@attacker.invalid',
            'help\u0085@trusted.example', 'help\u009f@trusted.example',
            'help@trusted.example#fragment', 'help@localhost',
            'help@127.0.0.1', 'a..b@trusted.example', 'no-address', None,
        ]
        for value in attacks:
            with self.subTest(value=value):
                entry = copy.deepcopy(self.entry)
                entry['contact']['emails'] = [value]
                with self.assertRaises(SystemExit):
                    build.validate([entry])
                with self.assertRaises(ValueError):
                    build.mailto_href(value)

    def test_real_addresses_and_iri_keep_their_meaning(self):
        for value in [
            'https://trusted.example/report?q=1#contact',
            'https://trusted.example/公表資料?q=確認#窓口',
            'https://例え.テスト/問い合わせ',
            'https://1.1.1.1/report', 'https://[2606:4700:4700::1111]/report',
        ]:
            with self.subTest(value=value):
                self.assertTrue(build.valid_https_url(value))
        for value in [
            'N1000X074@trusted.example', 'security_team@trusted.example',
            'incident+2026@trusted.example', 'a?bcc=b@trusted.example',
            'a&b@trusted.example', 'a%b@trusted.example',
            '"a@b"@trusted.example', 'help@例え.テスト', 'help@faß.de',
        ]:
            with self.subTest(value=value):
                uri = urllib.parse.urlsplit(build.mailto_href(value))
                self.assertEqual(uri.query, '')
                self.assertEqual(uri.fragment, '')
                self.assertEqual(urllib.parse.unquote(uri.path), build.mailbox(value))
                if value == 'help@faß.de':
                    self.assertEqual(urllib.parse.unquote(uri.path), value)


if __name__ == '__main__':
    unittest.main()
