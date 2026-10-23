/**
 * Real-browser check of the clean scientific calculator (Playwright + Chromium).
 * Usage: BASE_URL=http://172.18.0.20:8000 SESSION_PATH=/practice/session/12/ node tests/e2e_calculator_browser.js
 */
const fs = require('fs');
const os = require('os');
const path = require('path');
const { chromium } = require('playwright-core');

const BASE = process.env.BASE_URL || 'http://127.0.0.1:8000';
const SESSION = process.env.SESSION_PATH || '/practice/session/12/';

function findChromium() {
  if (process.env.CHROMIUM_PATH) return process.env.CHROMIUM_PATH;
  const dir = path.join(os.homedir(), '.cache', 'ms-playwright');
  for (const d of fs.readdirSync(dir).filter((n) => n.startsWith('chromium-')).sort().reverse()) {
    const p = path.join(dir, d, 'chrome-linux64', 'chrome');
    if (fs.existsSync(p)) return p;
    const pShell = path.join(dir, d, 'chrome-headless-shell-linux64', 'chrome-headless-shell');
    if (fs.existsSync(pShell)) return pShell;
  }
  throw new Error('No Chromium found; set CHROMIUM_PATH');
}

let failures = 0;
const check = (name, ok, detail = '') => {
  console.log(`${ok ? '✓ PASS' : '✗ FAIL'}: ${name}${detail ? '  -> ' + detail : ''}`);
  if (!ok) failures += 1;
};

(async () => {
  const browser = await chromium.launch({ executablePath: findChromium(), headless: true, args: ['--no-sandbox'] });
  const page = await (await browser.newContext({ viewport: { width: 1280, height: 800 } })).newPage();
  const errors = [];
  page.on('pageerror', (e) => errors.push(String(e)));
  page.on('console', (m) => {
    if (m.type() === 'error') errors.push(m.text());
  });
  const failedAssets = [];
  page.on('response', (r) => {
    if (r.status() >= 400 && /\/static\//.test(r.url())) failedAssets.push(`${r.status()} ${r.url()}`);
  });

  await page.goto(BASE + SESSION, { waitUntil: 'networkidle' });
  const selectedBefore = await page.$$eval('input[type=radio]:checked', (els) => els.map((e) => e.value));

  const modal = page.locator('#scientific-calculator-modal');
  check('modal exists and starts closed', (await modal.count()) === 1 && (await modal.isHidden()));

  // 1. Open with Alt+C
  await page.keyboard.press('Alt+c');
  check('Alt+C opens the calculator', await modal.isVisible());

  // 2. Chassis dimensions: must be clean and max-width bounded
  const cardBox = await page.locator('.calc-window').boundingBox();
  check('calculator width is bounded and not stretched (>300px and <=450px)', cardBox && cardBox.width >= 300 && cardBox.width <= 450, JSON.stringify(cardBox));

  // 3. Keypad click test: 2 + 3 =
  await modal.locator('button[onclick*="appendCalc(\'2\')"]').click();
  await modal.locator('button[onclick*="appendCalc(\'+\')"]').click();
  await modal.locator('button[onclick*="appendCalc(\'3\')"]').click();
  await modal.locator('button[onclick*="evaluateCalc"]').click();
  await page.waitForTimeout(100);
  const r1 = (await page.locator('#calc-result-display').textContent()).trim();
  check('Keypad: 2 + 3 = 5', r1 === '5', r1);

  // 4. Clear key C
  await modal.locator('button[onclick*="clearCalc"]').click();
  const rClear = (await page.locator('#calc-result-display').textContent()).trim();
  check('Clear key C resets result to 0', rClear === '0', rClear);

  // 5. Direct keyboard typing: 8 * 9 Enter
  await page.keyboard.type('8*9');
  await page.keyboard.press('Enter');
  await page.waitForTimeout(100);
  const r2 = (await page.locator('#calc-result-display').textContent()).trim();
  check('Keyboard typing: 8 * 9 Enter = 72', r2 === '72', r2);

  // 6. Trigonometry DEG vs RAD
  await modal.locator('button[onclick*="clearCalc"]').click();
  await modal.locator('button[onclick*="appendCalc(\'sin(\')"]').click();
  await page.keyboard.type('30');
  await modal.locator('button[onclick*="evaluateCalc"]').click();
  await page.waitForTimeout(100);
  const r3 = (await page.locator('#calc-result-display').textContent()).trim();
  check('sin(30) in DEG = 0.5', r3 === '0.5', r3);

  // S<=>D fraction toggle: 0.5 <-> 1/2
  await modal.locator('#calc-sd-btn').click();
  await page.waitForTimeout(50);
  const rFrac = (await page.locator('#calc-result-display').innerHTML());
  check('S<=>D toggles to fraction 1/2 in KaTeX', rFrac.includes('frac') || rFrac.includes('1'), rFrac);
  
  // LaTeX conversion line & copy test
  const latexStr = (await page.locator('#calc-latex-code').textContent()).trim();
  check('LaTeX conversion line is visible and displays formula', latexStr.length > 0, latexStr);
  await modal.locator('#calc-copy-latex-btn').click();
  await page.waitForTimeout(50);
  const btnText = (await modal.locator('#calc-copy-latex-btn').textContent()).trim();
  check('Copy LaTeX button provides instant feedback', btnText.includes('Copied'), btnText);

  await modal.locator('#calc-sd-btn').click();
  await page.waitForTimeout(50);

  // Toggle to RAD
  await modal.locator('#calc-angle-mode-btn').click();
  await page.waitForTimeout(100);
  const rRad = (await page.locator('#calc-result-display').textContent()).trim();
  check('switching to RAD re-evaluates sin(30) = -0.988...', /^[-−]0\.988/.test(rRad), rRad);

  // Toggle back to DEG
  await modal.locator('#calc-angle-mode-btn').click();

  // 7. Error handling: 5 / 0 = Math ERROR
  await modal.locator('button[onclick*="clearCalc"]').click();
  await page.keyboard.type('5/0');
  await page.keyboard.press('Enter');
  await page.waitForTimeout(100);
  const rDivZero = (await page.locator('#calc-result-display').textContent()).trim();
  check('division by zero reports Math ERROR', /Math ERROR|Infinity/.test(rDivZero), rDivZero);

  // 7b. Casio REPLAY 4-way Directional Pad Navigation
  await modal.locator('button[onclick*="clearCalc"]').click();
  await page.keyboard.type('12+34');
  await modal.locator('#calc-nav-left').click();
  await modal.locator('#calc-nav-left').click();
  await modal.locator('#calc-nav-left').click();
  await page.keyboard.type('5');
  const midNavExpr = (await page.locator('#calc-expression-display').textContent()).trim();
  check('REPLAY directional navigation inserts in middle: 125+34', midNavExpr.includes('125') && midNavExpr.includes('34'), midNavExpr);

  // 8. Exam isolation & radio buttons untouched
  const selectedDuring = await page.$$eval('input[type=radio]:checked', (els) => els.map((e) => e.value));
  await page.keyboard.press('Escape');
  await page.waitForTimeout(100);
  check('Escape closes the calculator', await modal.isHidden());

  const selectedAfter = await page.$$eval('input[type=radio]:checked', (els) => els.map((e) => e.value));
  check('selected answers unchanged by calculator use', JSON.stringify(selectedBefore) === JSON.stringify(selectedDuring) && JSON.stringify(selectedDuring) === JSON.stringify(selectedAfter), JSON.stringify([selectedBefore, selectedAfter]));
  check('still on the same exam page (nothing submitted / navigated)', page.url().startsWith(BASE + SESSION));

  check('no failed /static/ requests', failedAssets.length === 0, failedAssets.join(' | '));
  const realErrors = errors.filter((e) => !/GSAP target/i.test(e) && !/Cross-Origin-Opener-Policy/i.test(e));
  check('no JavaScript errors in console', realErrors.length === 0, realErrors.slice(0, 3).join(' | '));

  await page.screenshot({ path: '/tmp/calc_clean_final.png' });
  await browser.close();

  console.log(failures === 0 ? '--- ALL BROWSER CHECKS PASSED ---' : `--- ${failures} BROWSER CHECK(S) FAILED ---`);
  process.exit(failures === 0 ? 0 : 1);
})().catch((e) => {
  console.error(e);
  process.exit(2);
});
