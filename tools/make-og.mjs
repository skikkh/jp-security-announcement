// OGP画像（src/assets/og.png）を tools/og.html から生成します。
// 使い方: node tools/make-og.mjs   （Playwright が必要）
import { createRequire } from 'module';
import { execSync } from 'child_process';
import { fileURLToPath } from 'url';
import path from 'path';
const require = createRequire(execSync('npm root -g').toString().trim() + '/');
const { chromium } = require('playwright');
const here = path.dirname(fileURLToPath(import.meta.url));
const browser = await chromium.launch();
const page = await browser.newPage({ viewport: { width: 1200, height: 630 } });
await page.goto('file://' + path.join(here, 'og.html'));
await page.screenshot({ path: path.join(here, '..', 'src', 'assets', 'og.png') });
await browser.close();
console.log('wrote src/assets/og.png');
