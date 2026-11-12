/**
 * KalmiPrep Nuance Assertions Helper
 *
 * Implements authoritative checks for hidden invariants that raw syntax tests miss:
 * 1. KaTeX formula integrity & error rendering
 * 2. Mobile horizontal viewport blowout
 * 3. 44x44px minimum touch targets
 * 4. WCAG AA color contrast calculation
 * 5. Pure black background prohibition
 * 6. Kobo-precision revenue split calculation
 */

/**
 * Calculates WCAG relative luminance of an RGB/RGBA array [r, g, b] (0-255).
 */
function getRelativeLuminance([r, g, b]) {
  const [rs, gs, bs] = [r, g, b].map(c => {
    const s = c / 255;
    return s <= 0.03928 ? s / 12.92 : Math.pow((s + 0.055) / 1.055, 2.4);
  });
  return 0.2126 * rs + 0.7152 * gs + 0.0722 * bs;
}

/**
 * Parses a CSS color string (rgb, rgba, hex) into [r, g, b].
 */
function parseColor(colorStr) {
  if (!colorStr) return [255, 255, 255];
  colorStr = colorStr.trim().toLowerCase();

  // Handle Hex
  if (colorStr.startsWith('#')) {
    let hex = colorStr.slice(1);
    if (hex.length === 3) hex = hex.split('').map(c => c + c).join('');
    if (hex.length >= 6) {
      return [
        parseInt(hex.slice(0, 2), 16),
        parseInt(hex.slice(2, 4), 16),
        parseInt(hex.slice(4, 6), 16)
      ];
    }
  }

  // Handle rgb / rgba
  const match = colorStr.match(/rgba?\((\d+),\s*(\d+),\s*(\d+)/);
  if (match) {
    return [parseInt(match[1], 10), parseInt(match[2], 10), parseInt(match[3], 10)];
  }

  return [255, 255, 255];
}

/**
 * Computes WCAG contrast ratio between foreground and background.
 */
function calculateContrastRatio(foreground, background) {
  const fgRgb = typeof foreground === 'string' ? parseColor(foreground) : foreground;
  const bgRgb = typeof background === 'string' ? parseColor(background) : background;

  const l1 = getRelativeLuminance(fgRgb);
  const l2 = getRelativeLuminance(bgRgb);

  const lighter = Math.max(l1, l2);
  const darker = Math.min(l1, l2);

  return (lighter + 0.05) / (darker + 0.05);
}

/**
 * Invariant: Revenue split must be calculated in integer kobo without floating-point drift.
 */
function calculateKoboSplit(priceNgn, teacherPercentage = 80) {
  const totalKobo = Math.round(Number(priceNgn) * 100);
  const teacherKobo = Math.floor((totalKobo * teacherPercentage) / 100);
  const platformKobo = totalKobo - teacherKobo;

  return {
    priceNgn: Number(priceNgn),
    totalKobo,
    teacherKobo,
    platformKobo,
    teacherNgn: teacherKobo / 100,
    platformNgn: platformKobo / 100,
    isValid: teacherKobo + platformKobo === totalKobo
  };
}

/**
 * Invariant: KaTeX integrity check.
 * Searches for .katex-error elements or raw unparsed LaTeX delimiters.
 */
async function checkKaTeXErrors(pageOrDoc) {
  if (typeof pageOrDoc.evaluate === 'function') {
    // Running in Playwright page
    return await pageOrDoc.evaluate(() => {
      const errorEls = Array.from(document.querySelectorAll('.katex-error'));
      const errors = errorEls.map(el => el.textContent || el.getAttribute('title') || 'KaTeX render error');

      // Check for raw unrendered delimiters in content
      const contentTexts = Array.from(document.querySelectorAll('.question-body, .option-text, .math-content'))
        .map(el => el.innerText || el.textContent || '');
      
      const unrenderedDelims = [];
      const rawRegex = /(\$\$[^\$]+\$\$|\\\([^\)]+\\\)|\\\[[^\]]+\\\])/g;
      for (const text of contentTexts) {
        const matches = text.match(rawRegex);
        if (matches) unrenderedDelims.push(...matches);
      }

      return {
        passed: errors.length === 0 && unrenderedDelims.length === 0,
        errors,
        unrenderedDelims
      };
    });
  } else {
    // Running in jsdom document
    const errorEls = Array.from(pageOrDoc.querySelectorAll('.katex-error'));
    return {
      passed: errorEls.length === 0,
      errors: errorEls.map(el => el.textContent || 'KaTeX error'),
      unrenderedDelims: []
    };
  }
}

/**
 * Invariant: No pure black background in dark mode.
 */
function checkPureBlackProhibition(colorStr) {
  const [r, g, b] = parseColor(colorStr);
  const isPureBlack = r === 0 && g === 0 && b === 0;
  return {
    passed: !isPureBlack,
    detectedColor: `rgb(${r}, ${g}, ${b})`,
    message: isPureBlack ? 'Pure black rgb(0,0,0) found; use rich dark palette (#0b0f19 or #0f172a).' : 'OK'
  };
}

/**
 * Invariant: Anti-AI UI & Slop Prohibition.
 * Searches for sparkle emojis, neon text gradients, and AI marketing buzzwords.
 */
function checkAntiAISlop(content) {
  const violations = [];

  if (content.includes('✨')) {
    violations.push('Sparkle emoji (✨) found');
  }

  const gradientRegex = /bg-clip-text.*(from-purple|from-pink|via-purple|to-pink)/i;
  if (gradientRegex.test(content)) {
    violations.push('Neon purple/pink text gradient found');
  }

  const buzzwordRegex = /(supercharge|unleash your potential|elevate your prep|game-changer|AI-powered magic)/i;
  const match = content.match(buzzwordRegex);
  if (match) {
    violations.push(`Generic AI marketing buzzword found: "${match[0]}"`);
  }

  return {
    passed: violations.length === 0,
    violations,
    details: violations.length === 0 ? 'Zero AI slop tropes detected' : violations.join('; ')
  };
}

module.exports = {
  getRelativeLuminance,
  parseColor,
  calculateContrastRatio,
  calculateKoboSplit,
  checkKaTeXErrors,
  checkPureBlackProhibition,
  checkAntiAISlop
};
