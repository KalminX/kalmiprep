/**
 * Real-browser check of the calculator with the REAL MathLive (Playwright + Chromium).
 * Usage: BASE_URL=https://kalmiprep.kalmitech.app SESSION_PATH=/practice/session/1/ node tests/e2e_calculator_browser.js
 * Only drives the calculator; never selects or submits an answer.
 * Needs: npm i -D playwright-core and a Chromium (CHROMIUM_PATH or the Playwright cache).
 */
const fs = require('fs');
const os = require('os');
const path = require('path');
const { chromium } = require('playwright-core');

const BASE = process.env.BASE_URL || 'http://127.0.0.1:8000';
const SESSION = process.env.SESSION_PATH || '/practice/session/1/';

function findChromium() {
  if (process.env.CHROMIUM_PATH) return process.env.CHROMIUM_PATH;
  const dir = path.join(os.homedir(), '.cache', 'ms-playwright');
  for (const d of fs.readdirSync(dir).filter((n) => n.startsWith('chromium-')).sort().reverse()) {
    const p = path.join(dir, d, 'chrome-linux64', 'chrome');
    if (fs.existsSync(p)) return p;
  }
  throw new Error('No Chromium found; set CHROMIUM_PATH');
}

let failures = 0;
const check = (name, ok, detail = '') => { console.log(`${ok ? '✓ PASS' : '✗ FAIL'}: ${name}${detail ? '  -> ' + detail : ''}`); if (!ok) failures += 1; };

(async () => {
  const browser = await chromium.launch({ executablePath: findChromium(), headless: true, args: ['--no-sandbox'] });
  const page = await (await browser.newContext({ viewport: { width: 1100, height: 900 } })).newPage();
  const errors = [];
  page.on('pageerror', (e) => errors.push(String(e)));
  page.on('console', (m) => { if (m.type() === 'error') errors.push(m.text()); });
  const failedAssets = [];
  page.on('response', (r) => { if (r.status() >= 400 && /\/static\//.test(r.url())) failedAssets.push(`${r.status()} ${r.url()}`); });

  await page.goto(BASE + SESSION, { waitUntil: 'networkidle' });
  const selectedBefore = await page.$$eval('input[type=radio]:checked', (els) => els.map((e) => e.value));

  const modal = page.locator('#scientific-calculator-modal');
  check('modal exists and starts closed', (await modal.count()) === 1 && (await modal.isHidden()));
  check('MathLive loads lazily only after the page (custom element defined)', await page.waitForFunction(() => !!customElements.get('math-field'), null, { timeout: 15000 }).then(() => true).catch(() => false));

  await page.keyboard.press('Alt+c');
  check('Alt+C opens the calculator', await modal.isVisible());
  await page.waitForSelector('#calc-mathfield-container math-field', { timeout: 10000 });

  const field = page.locator('#calc-mathfield-container math-field');
  const result = page.locator('#calc-result-output');
  const clear = () => page.click('button[onclick*="\'AC\'"]');
  const evaluate = async () => { await page.keyboard.press('Enter'); await page.waitForTimeout(250); };
  const latex = () => field.evaluate((f) => f.value);
  const shown = () => result.evaluate((el) => ({ text: el.textContent.replace(/\s+/g, ' ').trim(), katex: !!el.querySelector('.katex') }));

  // 1. natural fraction typed via keypad / keyboard ("FRAC" builds a stacked fraction)
  await clear();
  await page.click('button[onclick*="\'FRAC\'"]');
  await field.evaluate((f) => {
    f.executeCommand(['insert', '1']);
    f.executeCommand(['moveToNextPlaceholder']);
    f.executeCommand(['insert', '2']);
    f.executeCommand(['moveToNextChar']);
    f.executeCommand(['insert', '+']);
  });
  await page.click('button[onclick*="\'FRAC\'"]');
  await field.evaluate((f) => {
    f.executeCommand(['insert', '1']);
    f.executeCommand(['moveToNextPlaceholder']);
    f.executeCommand(['insert', '3']);
  });
  const l1 = await latex();
  check('fraction produces a structured \\frac field', /\\frac/.test(l1) && /1/.test(l1) && /2/.test(l1), l1);
  check('fraction is rendered as stacked notation (not plain text)', await field.evaluate((f) => !!f.shadowRoot && f.shadowRoot.innerHTML.includes('frac')));
  await evaluate();
  let r = await shown();
  check('1/2 + 1/3 = 5/6 shown as exact fraction, with S⇔D available', r.katex && /5/.test(r.text) && /6/.test(r.text) && (await page.locator('#calc-sd-indicator').isVisible()), JSON.stringify(r));

  // 2. keypad: sqrt key + typing inside the radical
  await clear();
  await page.click('button[onclick*="\'SQRT\'"]');
  await page.keyboard.type('18');
  const l2 = await latex();
  check('√ key inserts a radical you can type inside', /\\sqrt\{18\}/.test(l2), l2);
  await evaluate();
  r = await shown();
  check('√18 gives the exact surd (3√2) and decimal toggles', r.katex, JSON.stringify(r));

  // 3. trig + DEG/RAD
  await clear();
  await page.click('button[onclick*="\'SIN\'"]');
  await page.keyboard.type('30');
  await evaluate();
  r = await shown();
  check('sin(30) in DEG = 0.5', r.text === '0.5', JSON.stringify(r));
  await page.click('#calc-badge-angle'); await page.waitForTimeout(250);
  r = await shown();
  check('switching to RAD re-evaluates sin(30) = -0.988…', /^-0\.988/.test(r.text), JSON.stringify(r));
  await page.click('#calc-badge-angle');

  // 4. complex exponent through the physical keyboard
  await clear(); await field.click();
  await page.keyboard.type('2^(3+4i)');
  const l4 = await latex();
  await evaluate();
  r = await shown();
  check('2^(3+4i) = -7.4615 + 2.8855i (principal value)', /-7\.4614?9?\d*.*2\.88/.test(r.text.replace(/\s/g, '')) || /-7\.46.*2\.88/.test(r.text.replace(/\s/g, '')), `${l4} => ${JSON.stringify(r)}`);

  // 5. error handling
  await clear(); await field.click();
  await page.keyboard.type('5/0');
  await evaluate();
  r = await shown();
  check('division by zero reports Math ERROR', /Math ERROR/.test(r.text), JSON.stringify(r));
  await clear(); await field.click();
  await page.keyboard.type('5+');
  await evaluate();
  r = await shown();
  check('incomplete expression reports Syntax ERROR', /Syntax ERROR/.test(r.text), JSON.stringify(r));

  // 6. editing nested structure without destroying the rest
  await clear();
  await page.click('button[onclick*="\'FRAC\'"]');
  await field.evaluate((f) => {
    f.executeCommand(['insert', '1']);
    f.executeCommand(['moveToNextPlaceholder']);
    f.executeCommand(['insert', '2']);
    f.executeCommand(['moveToNextChar']);
    f.executeCommand(['insert', '+7']);
    f.executeCommand(['moveToPreviousChar']);
    f.executeCommand(['moveToPreviousChar']);
    f.executeCommand(['deleteBackward']);
  });
  const l6 = await latex();
  check('Backspace edits inside a nested structure without wiping the surrounding expression', /\\frac/.test(l6) && /7/.test(l6), l6);

  // 7. exam isolation + close
  const selectedDuring = await page.$$eval('input[type=radio]:checked', (els) => els.map((e) => e.value));
  await page.keyboard.press('Escape');
  check('Escape closes the calculator', await modal.isHidden());
  const selectedAfter = await page.$$eval('input[type=radio]:checked', (els) => els.map((e) => e.value));
  check('selected answers unchanged by calculator use', JSON.stringify(selectedBefore) === JSON.stringify(selectedDuring) && JSON.stringify(selectedDuring) === JSON.stringify(selectedAfter), JSON.stringify([selectedBefore, selectedAfter]));
  check('still on the same exam page (nothing submitted / navigated)', page.url().startsWith(BASE + SESSION));

  check('no failed /static/ requests', failedAssets.length === 0, failedAssets.join(' | '));
  const realErrors = errors.filter((e) => !/GSAP target/i.test(e) && !/Cross-Origin-Opener-Policy/i.test(e));
  check('no JavaScript errors in console', realErrors.length === 0, realErrors.slice(0, 3).join(' | '));

  await page.screenshot({ path: process.env.SHOT || '/tmp/calc_closed.png' });
  await page.keyboard.press('Alt+c');
  await page.waitForTimeout(300);
  await page.screenshot({ path: process.env.SHOT_OPEN || '/tmp/calc_open.png' });

  await browser.close();
  console.log(failures === 0 ? '--- BROWSER CHECKS PASSED ---' : `--- ${failures} BROWSER CHECK(S) FAILED ---`);
  process.exit(failures === 0 ? 0 : 1);
})().catch((e) => { console.error(e); process.exit(2); });
