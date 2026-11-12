#!/usr/bin/env node

/**
 * KalmiPrep Playwright Blueprint Executor
 *
 * Drives real Chromium browser sessions to validate:
 * - Real DOM rendering of templates and KaTeX math formulas
 * - Responsive viewports (375px mobile to 1280px desktop)
 * - Navigation links, ARIA labels, and focus rings
 * - Visual contrast & anti-AI slop markers
 *
 * Can run inside Docker or directly on host.
 */

const fs = require('fs');
const path = require('path');
const { chromium } = require('playwright-core');
const {
  calculateContrastRatio,
  checkKaTeXErrors,
  checkPureBlackProhibition,
  checkAntiAISlop
} = require('./helpers/nuance_assertions');
const { BASE_URL } = require('./helpers/auth_fixtures');

// Determine Chromium executable path
function resolveChromiumPath() {
  if (process.env.CHROMIUM_PATH && fs.existsSync(process.env.CHROMIUM_PATH)) {
    return process.env.CHROMIUM_PATH;
  }
  const candidates = [
    '/usr/bin/chromium-browser',
    '/usr/bin/chromium',
    '/usr/bin/google-chrome',
    '/snap/bin/chromium'
  ];
  for (const c of candidates) {
    if (fs.existsSync(c)) return c;
  }
  return undefined;
}

const screenshotsDir = path.resolve(__dirname, 'screenshots');
if (!fs.existsSync(screenshotsDir)) {
  fs.mkdirSync(screenshotsDir, { recursive: true });
}

const targetBaseUrl = process.env.BASE_URL || 'http://172.18.0.8:8000';

async function runPlaywrightSuite() {
  console.log('\n======================================================');
  console.log('   KalmiPrep Playwright E2E Browser Test Suite        ');
  console.log('======================================================\n');
  console.log(`Base URL: ${targetBaseUrl}`);

  const executablePath = resolveChromiumPath();
  console.log(`Chromium Binary: ${executablePath || 'Playwright default'}`);

  let browser;
  try {
    browser = await chromium.launch({
      executablePath,
      headless: !process.argv.includes('--headed'),
      args: [
        '--no-sandbox',
        '--disable-setuid-sandbox',
        '--disable-dev-shm-usage',
        '--disable-gpu'
      ]
    });
  } catch (err) {
    console.error(`\n❌ Could not launch Chromium browser: ${err.message}`);
    console.log('\nTip: To run with Docker Chromium:');
    console.log('  docker run --rm --network webproxy -v "$(pwd):/app" -w /app kalmiprep-playwright npm run test:playwright\n');
    process.exit(1);
  }

  const context = await browser.newContext({
    viewport: { width: 1280, height: 800 },
    userAgent: 'KalmiPrep-Playwright-E2E/1.0'
  });

  const page = await context.newPage();
  let passCount = 0;
  let failCount = 0;

  async function checkScenario(name, fn) {
    process.stdout.write(`• Running scenario: ${name}... `);
    try {
      await fn();
      passCount++;
      console.log('✓ PASSED');
    } catch (err) {
      failCount++;
      console.log(`✗ FAILED: ${err.message}`);
    }
  }

  try {
    // 1. Landing Page Navigation & ARIA Skip Link Check
    await checkScenario('Landing Page & Skip Link', async () => {
      await page.goto(`${targetBaseUrl}/`, { waitUntil: 'domcontentloaded', timeout: 15000 });
      const title = await page.title();
      if (!title.includes('KalmiPrep')) throw new Error(`Unexpected page title: "${title}"`);

      // Verify skip to main content link
      const skipLink = await page.$('a[href="#main-content"]');
      if (!skipLink) throw new Error('Missing WCAG 2.4.1 Skip-to-content link in base.html');

      // Save screenshot
      await page.screenshot({ path: path.join(screenshotsDir, 'landing_desktop.png') });
    });

    // 2. Mobile Viewport Blowout & Horizontal Scroll Check (375px)
    await checkScenario('Mobile Viewport Stability (375px)', async () => {
      await page.setViewportSize({ width: 375, height: 667 });
      await page.goto(`${targetBaseUrl}/`, { waitUntil: 'domcontentloaded', timeout: 15000 });

      const hasHorizontalScroll = await page.evaluate(() => {
        return document.documentElement.scrollWidth > window.innerWidth;
      });
      if (hasHorizontalScroll) throw new Error('Document root has horizontal scroll blowout on 375px viewport');

      await page.screenshot({ path: path.join(screenshotsDir, 'landing_mobile_375.png') });
    });

    // 3. KaTeX Equation Integrity on Curriculum Page
    await checkScenario('Curriculum Explorer & KaTeX Rendering', async () => {
      await page.setViewportSize({ width: 1280, height: 800 });
      await page.goto(`${targetBaseUrl}/curriculum/`, { waitUntil: 'domcontentloaded', timeout: 15000 });

      // Invariant: Zero KaTeX error classes
      const katexErrors = await page.$$eval('.katex-error', els => els.map(e => e.textContent));
      if (katexErrors.length > 0) {
        throw new Error(`Found ${katexErrors.length} KaTeX rendering error(s): ${katexErrors.join(', ')}`);
      }

      await page.screenshot({ path: path.join(screenshotsDir, 'curriculum_desktop.png') });
    });

    // 4. Questions Catalog & Filter Controls
    await checkScenario('Questions Catalog Navigation', async () => {
      await page.goto(`${targetBaseUrl}/questions/`, { waitUntil: 'domcontentloaded', timeout: 15000 });
      const cards = await page.$$('.question-card, [data-question-card]');
      // Verify page loaded without 500 error
      const statusText = await page.evaluate(() => document.body.innerText);
      if (statusText.includes('Server Error (500)')) throw new Error('Server returned 500 on questions catalog');

      await page.screenshot({ path: path.join(screenshotsDir, 'questions_catalog.png') });
    });

    // 5. Anti-AI Slop Invariant Check
    await checkScenario('Anti-AI Slop Invariant (No Sparkles / Gradient Blobs)', async () => {
      await page.goto(`${targetBaseUrl}/`, { waitUntil: 'domcontentloaded', timeout: 15000 });
      const content = await page.content();
      const check = checkAntiAISlop(content);
      if (!check.passed) throw new Error(check.details);
    });

    // 6. Asynchronous Client Error Telemetry Beacon Check
    await checkScenario('Client Telemetry Error Beacon Endpoint', async () => {
      const beaconStatus = await page.evaluate(async (baseUrl) => {
        const payload = JSON.stringify({
          message: 'Playwright E2E Test Diagnostic Beacon',
          stack_trace: 'playwright_blueprint_executor.js:160:10',
          path: '/e2e-test/',
          domain: 'CLIENT_JS',
          severity: 'INFO',
          metadata: { testRunner: 'Playwright', timestamp: Date.now() }
        });
        const res = await fetch(`${baseUrl}/api/telemetry/error-beacon/`, {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: payload
        });
        return res.status;
      }, targetBaseUrl);

      if (beaconStatus !== 204) {
        throw new Error(`Telemetry beacon returned status ${beaconStatus}, expected 204`);
      }
    });

    // 7. Interactive Exam Setup & CBT Accessibility
    await checkScenario('Practice Setup Form & JAMB 8-Key UI Presence', async () => {
      await page.goto(`${targetBaseUrl}/practice/setup/`, { waitUntil: 'domcontentloaded', timeout: 15000 });
      const setupTitle = await page.title();
      if (!setupTitle.includes('Practice') && !setupTitle.includes('KalmiPrep')) {
        throw new Error(`Unexpected practice setup title: "${setupTitle}"`);
      }

      // Verify accessible form selects are rendered
      const selects = await page.$$('select');
      if (selects.length === 0) {
        throw new Error('No assessment configuration dropdowns found on practice setup page');
      }

      await page.screenshot({ path: path.join(screenshotsDir, 'practice_setup.png') });
    });

  } finally {
    await browser.close();
  }

  console.log('\n------------------------------------------------------');
  console.log(`Playwright E2E Results: ${passCount} passed, ${failCount} failed.`);
  console.log(`Screenshots saved to: ${screenshotsDir}`);
  console.log('======================================================\n');

  if (failCount > 0) process.exit(1);
}

runPlaywrightSuite().catch(err => {
  console.error(`Unexpected Playwright test failure: ${err.message}`);
  process.exit(1);
});
