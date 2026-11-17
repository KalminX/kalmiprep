#!/usr/bin/env node

/**
 * KalmiPrep Curriculum Layout Geometry & ARIA Accessibility Quality Gate
 * 
 * Tests both:
 * 1. Desktop & Mobile Layout Geometry (Bounding box coordinates, side-by-side math, zero horizontal overflow)
 * 2. WAI-ARIA & WCAG Accessibility Audit via axe-core
 */

const assert = require('assert');
const { chromium } = require('playwright-core');

const BASE_URL = process.env.BASE_URL || 'http://kalmiprep-app:8000';
const CHROMIUM_PATH = process.env.CHROMIUM_PATH || '/usr/bin/chromium-browser';

async function runAudit() {
  console.log('\n===============================================================');
  console.log('   KalmiPrep Curriculum Layout & ARIA Quality Gate             ');
  console.log('===============================================================\n');

  const browser = await chromium.launch({
    executablePath: CHROMIUM_PATH,
    args: ['--no-sandbox', '--disable-setuid-sandbox']
  });

  try {
    // -------------------------------------------------------------------------
    // TEST 1: DESKTOP LAYOUT (1440 x 900)
    // -------------------------------------------------------------------------
    console.log('[Test 1] Auditing Desktop Layout (1440x900)...');
    const desktopPage = await browser.newPage({ viewport: { width: 1440, height: 900 } });
    await desktopPage.goto(`${BASE_URL}/curriculum/subjects/`, { waitUntil: 'networkidle' });

    const aside = await desktopPage.$('aside');
    const main = await desktopPage.$('main#topic-viewport');

    assert(aside, 'Desktop <aside> sidebar must exist in DOM');
    assert(main, 'Desktop <main> viewport must exist in DOM');

    const asideBox = await aside.boundingBox();
    const mainBox = await main.boundingBox();

    console.log(`  -> Aside Geometry: X=${asideBox.x.toFixed(1)}, Y=${asideBox.y.toFixed(1)}, Width=${asideBox.width.toFixed(1)}, Height=${asideBox.height.toFixed(1)}`);
    console.log(`  -> Main Geometry:  X=${mainBox.x.toFixed(1)}, Y=${mainBox.y.toFixed(1)}, Width=${mainBox.width.toFixed(1)}, Height=${mainBox.height.toFixed(1)}`);

    // Strict mathematical side-by-side assertions:
    assert(asideBox.width >= 270 && asideBox.width <= 350, `Aside width must be fixed sidebar (~288-320px), got ${asideBox.width}`);
    assert(mainBox.width >= 750, `Main width must take remaining fluid space (>=750px), got ${mainBox.width}`);
    assert(asideBox.x + asideBox.width <= mainBox.x + 5, `Aside must be to the left of Main! (aside.right=${asideBox.x + asideBox.width}, main.left=${mainBox.x})`);
    assert(Math.abs(asideBox.y - mainBox.y) < 25, `Aside and Main must start at approximately the same top coordinate! Y diff=${Math.abs(asideBox.y - mainBox.y)}`);

    console.log('  ✔ DESKTOP GEOMETRY ASSERTION PASSED: Elements are strictly side-by-side horizontally!\n');

    // -------------------------------------------------------------------------
    // TEST 2: MOBILE LAYOUT (390 x 844 - iPhone 14)
    // -------------------------------------------------------------------------
    console.log('[Test 2] Auditing Mobile Layout (390x844)...');
    const mobilePage = await browser.newPage({ viewport: { width: 390, height: 844 } });
    await mobilePage.goto(`${BASE_URL}/curriculum/subjects/`, { waitUntil: 'networkidle' });

    // Assert Desktop Sidebar is hidden
    const asideDisplay = await mobilePage.$eval('aside', el => window.getComputedStyle(el).display);
    assert.strictEqual(asideDisplay, 'none', 'Desktop <aside> must be display:none on mobile');
    console.log('  ✔ Desktop sidebar is cleanly hidden on mobile');

    // Assert Mobile Tabs are rendered and sticky
    const mobileTabsNav = await mobilePage.$('.lg\\:hidden.sticky');
    assert(mobileTabsNav, 'Mobile sticky tab strip must exist');
    const tabsPosition = await mobilePage.$eval('.lg\\:hidden.sticky', el => window.getComputedStyle(el).position);
    assert.strictEqual(tabsPosition, 'sticky', 'Mobile tab bar must have position:sticky');
    console.log('  ✔ Mobile sticky tab strip verified');

    // Assert Zero Horizontal Document Overflow
    const overflow = await mobilePage.evaluate(() => {
      return {
        viewportWidth: window.innerWidth,
        scrollWidth: document.documentElement.scrollWidth,
        bodyScrollWidth: document.body.scrollWidth
      };
    });
    console.log(`  -> Mobile Document Width: ${overflow.viewportWidth}px, ScrollWidth: ${overflow.scrollWidth}px`);
    assert.strictEqual(overflow.scrollWidth, overflow.viewportWidth, 'Page must have ZERO horizontal scroll overflow on mobile!');
    console.log('  ✔ ZERO horizontal scroll overflow confirmed');

    // Assert Touch Target Sizing on visible buttons (WCAG 2.5.5 >= 36px)
    const buttonHeights = await mobilePage.$$eval('a.btn-primary, button.btn-primary, .mobile-sub-tab', els => els.filter(el => el.offsetParent !== null).map(el => el.offsetHeight));
    const undersizedButtons = buttonHeights.filter(h => h < 36);
    assert.strictEqual(undersizedButtons.length, 0, `All touch buttons must be >= 36px tall for mobile accessibility, found ${undersizedButtons.length} undersized`);
    console.log(`  ✔ Verified ${buttonHeights.length} touch buttons satisfy minimum touch target sizing (all >= 36px)`);

    // Test Mobile Tab Switching (Click Mathematics)
    await mobilePage.click('button[data-mobile-tab="mathematics"]');
    const isMathVisible = await mobilePage.$eval('#panel-mathematics', el => !el.classList.contains('hidden'));
    const isBioHidden = await mobilePage.$eval('#panel-biology', el => el.classList.contains('hidden'));
    assert(isMathVisible, 'Panel Mathematics must be visible after click');
    assert(isBioHidden, 'Panel Biology must be hidden after click');
    console.log('  ✔ Mobile interactive tab switching functional and reactive\n');

    // -------------------------------------------------------------------------
    // TEST 3: WAI-ARIA & ACCESSIBILITY AUDIT (axe-core)
    // -------------------------------------------------------------------------
    console.log('[Test 3] Running axe-core ARIA & Accessibility Engine...');
    
    // Inject axe-core into the page
    await desktopPage.addScriptTag({ url: 'https://cdnjs.cloudflare.com/ajax/libs/axe-core/4.10.2/axe.min.js' });
    
    const axeResults = await desktopPage.evaluate(async () => {
      return await window.axe.run(document, {
        runOnly: {
          type: 'tag',
          values: ['wcag2a', 'wcag2aa', 'wcag21a', 'wcag21aa', 'best-practice']
        }
      });
    });

    console.log(`  -> axe-core evaluated ${axeResults.passes.length} rules successfully.`);
    const criticalViolations = axeResults.violations.filter(v => v.impact === 'critical' || v.impact === 'serious');

    if (criticalViolations.length > 0) {
      console.error('\n  ✖ Accessibility Violations Found:');
      criticalViolations.forEach(v => {
        console.error(`     [${v.impact.toUpperCase()}] ${v.help} (${v.id})`);
        v.nodes.slice(0, 3).forEach(n => console.error(`       Target: ${n.target.join(' ')}`));
      });
      throw new Error(`axe-core found ${criticalViolations.length} critical/serious accessibility violations!`);
    } else {
      console.log('  ✔ axe-core ARIA Audit: 0 Critical / 0 Serious Accessibility Violations!\n');
    }

    console.log('===============================================================');
    console.log('   SUCCESS: All Desktop, Mobile & ARIA Assertions Verified!   ');
    console.log('===============================================================\n');

  } finally {
    await browser.close();
  }
}

runAudit().catch(err => {
  console.error('\n✖ Quality Gate Failed:', err.message);
  process.exit(1);
});
