/**
 * KalmiPrep Scientific Calculator - LaTeX Formatter
 * 
 * GoF Adapter / Decorator Pattern.
 * Converts calculator tokens and expressions into textbook-quality LaTeX
 * for rendering in the Natural Textbook Display via KaTeX, and exposes
 * raw LaTeX conversion strings for students, teachers, and CBT exams.
 */

(function (global) {
  'use strict';

  const KalmiCalcFormatter = {
    /**
     * Converts a mathematical expression into clean LaTeX markup.
     * Natural Casio Display: stacked fractions, radicals, powers, and trig.
     * 
     * @param {string} expr Raw calculator expression
     * @returns {string} Clean LaTeX representation
     */
    toLatex(expr) {
      if (!expr || expr === '0') return '0';

      let s = expr;

      // 1. Stacked fractions: convert A ÷ B to \frac{A}{B}
      s = s.replace(/([0-9a-zA-Zπe]+|\([^\(\)]+\))\s*[÷/]\s*([0-9a-zA-Zπe]+|\([^\(\)]+\))/g, (m, num, den) => {
        const cleanNum = num.startsWith('(') && num.endsWith(')') ? num.slice(1, -1) : num;
        const cleanDen = den.startsWith('(') && den.endsWith(')') ? den.slice(1, -1) : den;
        return '\\frac{' + cleanNum + '}{' + cleanDen + '}';
      });
      // Handle trailing division like '5 ÷' -> \frac{5}{\Box}
      s = s.replace(/([0-9a-zA-Zπe]+|\([^\(\)]+\))\s*[÷/]$/, (m, num) => {
        const cleanNum = num.startsWith('(') && num.endsWith(')') ? num.slice(1, -1) : num;
        return '\\frac{' + cleanNum + '}{\\Box}';
      });

      // 2. Radicals: sqrt( ... ) and cbrt( ... )
      s = s.replace(/sqrt\(\s*\)/g, '\\sqrt{\\Box}');
      s = s.replace(/cbrt\(\s*\)/g, '\\sqrt[3]{\\Box}');
      s = s.replace(/sqrt\($/, '\\sqrt{\\Box}');
      s = s.replace(/cbrt\($/, '\\sqrt[3]{\\Box}');
      s = s.replace(/sqrt\(([^)]+)\)/g, '\\sqrt{$1}');
      s = s.replace(/cbrt\(([^)]+)\)/g, '\\sqrt[3]{$1}');
      s = s.replace(/sqrt\(([^)]+)$/g, '\\sqrt{$1}');
      s = s.replace(/cbrt\(([^)]+)$/g, '\\sqrt[3]{$1}');

      // 3. Powers: ^(x) -> ^{x}, ^2 -> ^{2}, 10^(x) -> 10^{x}
      s = s.replace(/\^\(([^)]+)\)/g, '^{$1}');
      s = s.replace(/\^\(([^)]+)$/g, '^{$1}');
      s = s.replace(/\^\($/, '^{\\Box}');
      s = s.replace(/\^2/g, '^{2}');
      s = s.replace(/10\^/g, '10^');

      // 4. Auto-balance any remaining unclosed parentheses
      const opens = (s.match(/\(/g) || []).length;
      const closes = (s.match(/\)/g) || []).length;
      if (opens > closes) {
        s += ')'.repeat(opens - closes);
      }

      // 5. Operators, functions & constants
      s = s
        .replace(/×/g, ' \\times ')
        .replace(/÷/g, ' \\div ')
        .replace(/−/g, ' - ')
        .replace(/π/g, ' \\pi ')
        .replace(/Ans/gi, ' \\text{Ans} ')
        .replace(/EXP/g, ' \\times 10^')
        .replace(/asin\(/g, '\\sin^{-1}(')
        .replace(/acos\(/g, '\\cos^{-1}(')
        .replace(/atan\(/g, '\\tan^{-1}(')
        .replace(/sin\(/g, '\\sin(')
        .replace(/cos\(/g, '\\cos(')
        .replace(/tan\(/g, '\\tan(')
        .replace(/ln\(/g, '\\ln(')
        .replace(/log\(/g, '\\log(');

      return s;
    },

    /**
     * Builds the complete LaTeX formula equation string (e.g. \frac{1}{2} + \sqrt{16} = 4.5).
     */
    buildFullLatex(expression, result, isFractionMode, currentFraction) {
      if (!expression || expression === '0') return '0';
      const exprLatex = this.toLatex(expression);
      if (!result || result === '0' || result === 'Error' || result === 'Math ERROR') {
        return exprLatex;
      }
      let resLatex = result;
      if (isFractionMode && currentFraction && currentFraction.latex) {
        resLatex = currentFraction.latex;
      }
      return `${exprLatex} = ${resLatex}`;
    },

    /**
     * Safely renders the expression with an active blinking cursor indicator.
     * Splits into left and right tokens and inserts <span class="calc-cursor"></span>
     * for authentic Casio Natural Textbook Display navigation.
     */
    renderExpressionWithCursor(target, expression, cursorPos) {
      const el = typeof target === 'string' ? document.getElementById(target) : target;
      if (!el) return;

      if (!expression || expression === '0') {
        el.innerHTML = '<span class="calc-cursor"></span>0';
        return;
      }

      const pos = typeof cursorPos === 'number' && cursorPos >= 0 && cursorPos <= expression.length
        ? cursorPos
        : expression.length;

      const left = expression.slice(0, pos);
      const right = expression.slice(pos);

      const katexLib = typeof global !== 'undefined' && global.katex ? global.katex : null;
      if (katexLib && typeof katexLib.renderToString === 'function') {
        try {
          const leftTex = left ? this.toLatex(left) : '';
          const rightTex = right ? this.toLatex(right) : '';
          const leftHtml = leftTex ? katexLib.renderToString(leftTex, { throwOnError: false, output: 'html' }) : '';
          const rightHtml = rightTex ? katexLib.renderToString(rightTex, { throwOnError: false, output: 'html' }) : '';
          el.innerHTML = leftHtml + '<span class="calc-cursor"></span>' + rightHtml;
          return;
        } catch (e) {}
      }

      el.textContent = (left || '') + '|' + (right || '');
    },

    /**
     * Safely renders LaTeX into a DOM container element.
     * Uses KaTeX if available, with immediate fallback to clean textContent.
     * 
     * @param {HTMLElement|string} target Target element or ID
     * @param {string} latexStr LaTeX string to render
     * @param {string} fallbackText Fallback text if KaTeX is unavailable
     */
    renderToElement(target, latexStr, fallbackText = '') {
      const el = typeof target === 'string' ? document.getElementById(target) : target;
      if (!el) return;

      if (latexStr === 'Math ERROR' || latexStr === 'Error' || latexStr === 'Syntax ERROR') {
        el.textContent = latexStr;
        return;
      }

      const katexLib = typeof global !== 'undefined' && global.katex ? global.katex : null;
      if (katexLib && typeof katexLib.renderToString === 'function') {
        try {
          const html = katexLib.renderToString(latexStr, {
            throwOnError: false,
            displayMode: false,
            output: 'html'
          });
          el.innerHTML = html;
          return;
        } catch (e) {
          // Fall through to textContent fallback
        }
      }

      el.textContent = fallbackText || latexStr || '0';
    }
  };

  // Export for browser and Node.js
  if (typeof module !== 'undefined' && module.exports) {
    module.exports = { KalmiCalcFormatter };
  }
  global.KalmiCalcFormatter = KalmiCalcFormatter;

})(typeof window !== 'undefined' ? window : globalThis);
