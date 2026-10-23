/**
 * KalmiPrep Scientific Calculator - LaTeX Formatter
 * 
 * GoF Adapter / Decorator Pattern.
 * Converts calculator tokens and expressions into textbook-quality LaTeX
 * for rendering in the Natural Textbook Display via KaTeX.
 */

(function (global) {
  'use strict';

  const KalmiCalcFormatter = {
    /**
     * Converts a mathematical expression into clean LaTeX markup.
     * 
     * @param {string} expr Raw calculator expression
     * @returns {string} LaTeX representation
     */
    toLatex(expr) {
      if (!expr || expr === '0') return '0';

      // Auto-balance parentheses for visually clean radical & grouping rendering
      let balanced = expr;
      const opens = (expr.match(/\(/g) || []).length;
      const closes = (expr.match(/\)/g) || []).length;
      if (opens > closes) {
        balanced += ')'.repeat(opens - closes);
      }

      let tex = balanced
        .replace(/×/g, ' \\times ')
        .replace(/÷/g, ' \\div ')
        .replace(/−/g, ' - ')
        .replace(/π/g, ' \\pi ')
        .replace(/Ans/gi, ' \\text{Ans} ')
        .replace(/asin\(/g, '\\sin^{-1}(')
        .replace(/acos\(/g, '\\cos^{-1}(')
        .replace(/atan\(/g, '\\tan^{-1}(')
        .replace(/sin\(/g, '\\sin(')
        .replace(/cos\(/g, '\\cos(')
        .replace(/tan\(/g, '\\tan(')
        .replace(/ln\(/g, '\\ln(')
        .replace(/log\(/g, '\\log(')
        .replace(/\^2/g, '^{2}')
        .replace(/\^\(/g, '^{(')
        .replace(/10\^\(/g, '10^{(')
        .replace(/EXP/g, ' \\times 10^')
        .replace(/sqrt\(/g, '\\sqrt{')
        .replace(/cbrt\(/g, '\\sqrt[3]{');

      // Convert matching ')' to '}' for opened radicals (\sqrt{ and \sqrt[3]{)
      let output = '';
      let stack = [];
      for (let i = 0; i < tex.length; i++) {
        if (tex.startsWith('\\sqrt{', i) || tex.startsWith('\\sqrt[3]{', i)) {
          const braceIdx = tex.indexOf('{', i);
          output += tex.slice(i, braceIdx + 1);
          stack.push('}');
          i = braceIdx;
        } else if (tex[i] === '(') {
          output += '(';
          stack.push(')');
        } else if (tex[i] === ')') {
          const expected = stack.pop();
          output += expected || ')';
        } else {
          output += tex[i];
        }
      }
      while (stack.length > 0) {
        output += stack.pop();
      }

      return output;
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
