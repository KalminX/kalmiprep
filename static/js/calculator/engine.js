/**
 * KalmiPrep Scientific Calculator - Mathematical Engine
 * 
 * Decoupled, pure evaluation engine powered by Math.js AST parser.
 * Zero eval() or Function() constructor calls.
 * 
 * Features:
 * - Parentheses auto-balancing
 * - Strict DEG and RAD trigonometry with exact boundary snapping (cos 90 = 0, tan 90 = Math ERROR)
 * - Inverse trigonometric functions (asin, acos, atan)
 * - Natural logarithms (ln) and common logarithms (log)
 * - Powers (x^y, x^2, 10^x) and roots (sqrt, cbrt)
 * - Factorials (n!)
 * - Scientific exponential notation (EXP -> *10^)
 * - Percentages (%)
 * - Mathematical constants (pi, e)
 * - Ans memory chaining
 */

(function (global) {
  'use strict';

  function factorial(n) {
    if (n < 0 || !Number.isInteger(n)) return NaN;
    if (n === 0 || n === 1) return 1;
    if (n > 170) return Infinity; // JS 64-bit float precision limit
    let res = 1;
    for (let i = 2; i <= n; i++) res *= i;
    return res;
  }

  function balanceParentheses(expr) {
    if (!expr) return '';
    const openCount = (expr.match(/\(/g) || []).length;
    const closeCount = (expr.match(/\)/g) || []).length;
    if (openCount > closeCount) {
      return expr + ')'.repeat(openCount - closeCount);
    }
    return expr;
  }

  function cleanExpression(expr, lastAns = 0) {
    const numericAns = parseFloat(lastAns) || 0;
    return expr
      .replace(/×/g, '*')
      .replace(/÷/g, '/')
      .replace(/−/g, '-')
      .replace(/π/g, 'pi')
      .replace(/Ans/gi, `(${numericAns})`)
      .replace(/EXP/g, '*10^')
      .replace(/(\d+(\.\d+)?)%/g, '($1 * 0.01)');
  }

  function getMathScope(mathjs, angleMode = 'DEG', numericAns = 0) {
    if (angleMode === 'DEG') {
      return {
        Ans: numericAns,
        ans: numericAns,
        sin: (x) => {
          const rad = (x * Math.PI) / 180;
          const s = Math.sin(rad);
          return Math.abs(s) < 1e-15 ? 0 : s;
        },
        cos: (x) => {
          const rad = (x * Math.PI) / 180;
          const c = Math.cos(rad);
          return Math.abs(c) < 1e-15 ? 0 : c;
        },
        tan: (x) => {
          if (Math.abs((x - 90) % 180) < 1e-10) throw new Error('Math ERROR');
          return Math.tan((x * Math.PI) / 180);
        },
        asin: (x) => (Math.asin(x) * 180) / Math.PI,
        acos: (x) => (Math.acos(x) * 180) / Math.PI,
        atan: (x) => (Math.atan(x) * 180) / Math.PI,
        ln: (x) => Math.log(x),
        log: (x) => Math.log10(x),
        sqrt: (x) => Math.sqrt(x),
        cbrt: (x) => Math.cbrt(x),
        factorial: (n) => factorial(n),
      };
    }

    return {
      Ans: numericAns,
      ans: numericAns,
      ln: (x) => Math.log(x),
      log: (x) => Math.log10(x),
      sqrt: (x) => Math.sqrt(x),
      cbrt: (x) => Math.cbrt(x),
      factorial: (n) => factorial(n),
    };
  }

  class KalmiCalcEngine {
    constructor(mathInstance = null) {
      this.math = mathInstance || (typeof global !== 'undefined' && global.math ? global.math : null);
    }

    getMathInstance() {
      if (this.math) return this.math;
      if (typeof global !== 'undefined' && global.math) {
        this.math = global.math;
      } else if (typeof require !== 'undefined') {
        try { this.math = require('mathjs'); } catch (e) {}
      }
      return this.math;
    }

    evaluate(expression, angleMode = 'DEG', lastAns = 0) {
      if (!expression || !expression.trim()) {
        return { success: true, result: '0', numericValue: 0 };
      }

      const mathjs = this.getMathInstance();
      if (!mathjs || typeof mathjs.evaluate !== 'function') {
        return { success: false, error: 'Math engine unavailable' };
      }

      const numericAns = parseFloat(lastAns) || 0;
      const balanced = balanceParentheses(expression.trim());
      const cleaned = cleanExpression(balanced, numericAns);
      const scope = getMathScope(mathjs, angleMode, numericAns);

      try {
        const raw = mathjs.evaluate(cleaned, scope);

        if (typeof raw === 'function') {
          return { success: false, error: 'Error' };
        }

        if (typeof raw === 'number') {
          if (!isFinite(raw)) {
            return { success: false, error: 'Math ERROR' };
          }
          if (Math.abs(raw) < 1e-12 && Math.abs(raw) > 0) {
            return { success: true, result: '0', numericValue: 0 };
          }
          const formatted = parseFloat(raw.toPrecision(12)).toString();
          return { success: true, result: formatted, numericValue: raw };
        }

        if (raw && typeof raw.format === 'function') {
          const formatted = raw.format({ precision: 12 });
          return { success: true, result: formatted, numericValue: Number(raw) || 0 };
        }

        return { success: true, result: String(raw), numericValue: Number(raw) || 0 };
      } catch (err) {
        if (err && err.message === 'Math ERROR') {
          return { success: false, error: 'Math ERROR' };
        }
        return { success: false, error: 'Error' };
      }
    }
  }

  // Export for browser and Node.js
  if (typeof module !== 'undefined' && module.exports) {
    module.exports = { KalmiCalcEngine, factorial, balanceParentheses, cleanExpression };
  }
  global.KalmiCalcEngine = KalmiCalcEngine;

})(typeof window !== 'undefined' ? window : globalThis);
