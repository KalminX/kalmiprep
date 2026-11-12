#!/usr/bin/env node

/**
 * KalmiPrep Static Mobile Responsiveness & Ergonomics Auditor
 *
 * Verifies core mobile invariants across templates and stylesheets:
 * 1. Viewport meta tag contains viewport-fit=cover
 * 2. iOS 16px font-size zoom prevention on inputs/selects/textareas
 * 3. Table overflow protection (overflow-x-auto or card-stack alternative)
 * 4. Safe-area insets for fixed mobile navigation
 * 5. Button touch target height invariant (min-h-[44px])
 * 6. KaTeX horizontal overflow containment
 */

const fs = require('fs');
const path = require('path');

const ROOT_DIR = path.resolve(__dirname, '../../../../');
const TEMPLATES_DIR = path.join(ROOT_DIR, 'templates');
const CSS_FILE = path.join(ROOT_DIR, 'static/css/input.css');

let violations = 0;
let passes = 0;

function reportPass(message) {
  console.log(`  ✓ ${message}`);
  passes++;
}

function reportFail(message) {
  console.error(`  ✗ VIOLATION: ${message}`);
  violations++;
}

function getAllFiles(dir, ext = '.html') {
  let files = [];
  if (!fs.existsSync(dir)) return files;
  const list = fs.readdirSync(dir);
  for (const file of list) {
    const fullPath = path.join(dir, file);
    const stat = fs.statSync(fullPath);
    if (stat.isDirectory()) {
      files = files.concat(getAllFiles(fullPath, ext));
    } else if (file.endsWith(ext)) {
      files.push(fullPath);
    }
  }
  return files;
}

console.log('\n=============================================================');
console.log('   KalmiPrep Mobile Responsiveness & Ergonomics Auditor      ');
console.log('=============================================================\n');

// 1. Audit Viewport Meta Tag in base.html
console.log('1. Auditing Viewport Meta Configuration...');
const baseHtmlPath = path.join(TEMPLATES_DIR, 'base.html');
if (fs.existsSync(baseHtmlPath)) {
  const baseContent = fs.readFileSync(baseHtmlPath, 'utf8');
  const viewportMatch = baseContent.match(/<meta\s+name=["']viewport["']\s+content=["']([^"']+)["']/i);
  if (viewportMatch) {
    const contentVal = viewportMatch[1];
    if (contentVal.includes('width=device-width') && contentVal.includes('viewport-fit=cover')) {
      reportPass(`base.html: Viewport correctly configured with viewport-fit=cover: "${contentVal}"`);
    } else {
      reportFail(`base.html: Viewport meta tag missing "viewport-fit=cover": "${contentVal}"`);
    }
  } else {
    reportFail('base.html: No <meta name="viewport"> tag detected.');
  }
} else {
  reportFail('base.html not found.');
}

// 2. Audit CSS Invariants in input.css
console.log('\n2. Auditing Global Stylesheet Invariants in static/css/input.css...');
if (fs.existsSync(CSS_FILE)) {
  const cssContent = fs.readFileSync(CSS_FILE, 'utf8');

  // Check Touch Target minimum height (44px)
  if (cssContent.includes('min-h-[44px]')) {
    reportPass('Primary and Secondary buttons enforce min-h-[44px] touch target invariant.');
  } else {
    reportFail('input.css does not declare min-h-[44px] for interactive buttons.');
  }

  // Check KaTeX overflow guard
  if (cssContent.includes('.katex-display') && cssContent.includes('overflow-x: auto')) {
    reportPass('KaTeX display equations are safeguarded with overflow-x: auto.');
  } else {
    reportFail('input.css missing .katex-display overflow-x: auto rule.');
  }

  // Check iOS 16px font-size zoom prevention
  const hasIosZoomRule =
    cssContent.includes('font-size: 16px') &&
    (cssContent.includes('@media (max-width: 640px)') || cssContent.includes('@media (max-width: 768px)'));
  if (hasIosZoomRule) {
    reportPass('iOS Safari auto-zoom prevention rule (16px font-size on mobile) is active.');
  } else {
    reportFail('input.css missing iOS Safari 16px input zoom prevention rule for mobile screens.');
  }

  // Check Safe Area Inset classes
  if (cssContent.includes('safe-area-inset-bottom')) {
    reportPass('Safe-area inset utility / padding support detected in stylesheet.');
  } else {
    reportFail('input.css missing safe-area-inset-bottom handling.');
  }
} else {
  reportFail(`input.css not found at ${CSS_FILE}`);
}

// 3. Audit Tables for Horizontal Overflow Wrapping
console.log('\n3. Auditing HTML Templates for Table Overflow Shields...');
const htmlFiles = getAllFiles(TEMPLATES_DIR);
let unshieldedTables = 0;

for (const filePath of htmlFiles) {
  const content = fs.readFileSync(filePath, 'utf8');
  const relativePath = path.relative(ROOT_DIR, filePath);

  if (content.includes('<table')) {
    // Check if the file contains an overflow-x-auto wrapper or a responsive card stack
    const hasOverflowWrapper = content.includes('overflow-x-auto') || content.includes('overflow-x-scroll');
    const hasCardStackAlternative = content.includes('md:hidden') && content.includes('hidden md:table');

    if (hasOverflowWrapper || hasCardStackAlternative) {
      reportPass(`${relativePath}: Table protected with overflow-x-auto or responsive card stack.`);
    } else {
      reportFail(`${relativePath}: <table> tag detected without an overflow-x-auto wrapper or card stack alternative.`);
      unshieldedTables++;
    }
  }
}

// 4. Summary & Exit Code
console.log('\n-------------------------------------------------------------');
console.log(`Audit Summary: ${passes} checks passed, ${violations} violations found.`);
console.log('=============================================================\n');

if (violations > 0) {
  process.exit(1);
} else {
  console.log('All mobile responsiveness invariants verified!\n');
  process.exit(0);
}
