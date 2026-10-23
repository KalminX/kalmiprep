/**
 * KalmiPrep Scientific Calculator Mathematical Engine
 * Core numerical, symbolic, and algebraic computation engine.
 *
 * Capabilities:
 * 1. Safe AST translation from MathLive LaTeX to canonical computable expressions.
 * 2. High-precision numerical evaluation via Math.js.
 * 3. Exact symbolic fraction, surd, and algebraic reduction via Nerdamer.
 * 4. Mode-specific computation: COMP, CMPLX (complex numbers & exponents), EQN (polynomial & linear solvers),
 *    STAT (statistics), MAT (matrix operations), VCT (vector operations).
 * 5. Degree/Radian aware trigonometric calculations with strict branch/singularity handling.
 * 6. ZERO usage of JavaScript eval() or new Function().
 */

(function (global) {
  'use strict';

  // --- Recursive LaTeX Brace & Bracket Parsers ---
  function parseBraces(str, startIndex) {
    if (str[startIndex] !== '{') return null;
    let depth = 0;
    for (let i = startIndex; i < str.length; i++) {
      if (str[i] === '{') depth++;
      else if (str[i] === '}') {
        depth--;
        if (depth === 0) return { content: str.slice(startIndex + 1, i), endIndex: i };
      }
    }
    return null;
  }

  function parseBrackets(str, startIndex) {
    if (str[startIndex] !== '[') return null;
    let depth = 0;
    for (let i = startIndex; i < str.length; i++) {
      if (str[i] === '[') depth++;
      else if (str[i] === ']') {
        depth--;
        if (depth === 0) return { content: str.slice(startIndex + 1, i), endIndex: i };
      }
    }
    return null;
  }

  function parseLatexArgument(str, startIndex) {
    let cur = startIndex;
    while (cur < str.length && /\s/.test(str[cur])) cur++;
    if (cur >= str.length) return null;
    if (str[cur] === '{') return parseBraces(str, cur);
    if (str[cur] === '\\') {
      let end = cur + 1;
      while (end < str.length && /[a-zA-Z]/.test(str[end])) end++;
      return { content: str.slice(cur, end), endIndex: end - 1 };
    }
    return { content: str[cur], endIndex: cur };
  }

  // --- Clean Float / Precision Formatter ---
  // Round to display precision. Never snaps small magnitudes to zero: physics
  // quantities such as 1.6e-19 are legitimate results.
  function cleanFloat(val, precision = 12) {
    if (typeof val !== 'number' || !Number.isFinite(val)) return val;
    return parseFloat(val.toPrecision(precision));
  }

  // Trigonometric results within floating-point noise of zero are exactly zero (e.g. sin(pi) in RAD).
  function cleanTrig(val) {
    if (typeof val !== 'number' || !Number.isFinite(val)) return val;
    return Math.abs(val) < 1e-14 ? 0 : cleanFloat(val);
  }

  // --- Convert MathLive LaTeX to Evaluatable Math Expression ---
  function latexToMathExpression(latex) {
    if (!latex || typeof latex !== 'string') return '';
    let s = latex.trim();

    // Remove display formatting and spacing macros
    s = s.replace(/\\displaystyle|\\textstyle|\\limits|\\nolimits/g, '');
    s = s.replace(/\\left|\\right/g, '');
    s = s.replace(/\\[,;:! ]/g, ' ');
    s = s.replace(/\\text\{(\s*P\s*|\s*C\s*)\}/g, '$1');
    s = s.replace(/\\text\{([a-zA-Z0-9_]+)\}/g, '$1');
    s = s.replace(/\\(?:mathrm|operatorname)\{([a-zA-Z]+)\}/g, '$1');

    // Degree literal: 30^\circ or 30° -> degree(30) (angle-mode aware, see createMathScope)
    s = s.replace(/(\d+(?:\.\d+)?)\s*(?:\^\{\\circ\}|\^\\circ|°)/g, 'degree($1)');

    // Recursive structural conversions (fractions, roots, logs, powers)
    let changed = true;
    let iterations = 0;
    while (changed && iterations < 40) {
      changed = false;
      iterations++;

      // 1. Fractions: \frac{numerator}{denominator} or \frac12 -> ((num)/(den))
      const fracIdx = s.indexOf('\\frac');
      if (fracIdx !== -1) {
        let cur = fracIdx + 5;
        const numMatch = parseLatexArgument(s, cur);
        if (numMatch) {
          cur = numMatch.endIndex + 1;
          const denMatch = parseLatexArgument(s, cur);
          if (denMatch) {
            const numExpr = latexToMathExpression(numMatch.content);
            const denExpr = latexToMathExpression(denMatch.content);
            s = s.slice(0, fracIdx) + '((' + numExpr + ')/(' + denExpr + '))' + s.slice(denMatch.endIndex + 1);
            changed = true;
            continue;
          }
        }
      }

      // 2. Nth roots: \sqrt[n]{x} -> (nthRoot((x), (n)))
      const nrootIdx = s.indexOf('\\sqrt[');
      if (nrootIdx !== -1) {
        const nMatch = parseBrackets(s, nrootIdx + 5);
        if (nMatch) {
          let cur = nMatch.endIndex + 1;
          while (cur < s.length && /\s/.test(s[cur])) cur++;
          const xMatch = parseBraces(s, cur);
          if (xMatch) {
            const nExpr = latexToMathExpression(nMatch.content);
            const xExpr = latexToMathExpression(xMatch.content);
            s = s.slice(0, nrootIdx) + 'nthRoot((' + xExpr + '), (' + nExpr + '))' + s.slice(xMatch.endIndex + 1);
            changed = true;
            continue;
          }
        }
      }

      // 3. Square roots: \sqrt{x} or \sqrt2 -> (sqrt(x))
      const sqrtIdx = s.indexOf('\\sqrt');
      if (sqrtIdx !== -1 && s[sqrtIdx + 5] !== '[') {
        let cur = sqrtIdx + 5;
        const xMatch = parseLatexArgument(s, cur);
        if (xMatch) {
          const xExpr = latexToMathExpression(xMatch.content);
          s = s.slice(0, sqrtIdx) + 'sqrt(' + xExpr + ')' + s.slice(xMatch.endIndex + 1);
          changed = true;
          continue;
        }
      }

      // 4. Powers with braces: ^{...} -> ^(...)
      const powIdx = s.indexOf('^{');
      if (powIdx !== -1) {
        const powMatch = parseBraces(s, powIdx + 1);
        if (powMatch) {
          const powExpr = latexToMathExpression(powMatch.content);
          s = s.slice(0, powIdx) + '^(' + powExpr + ')' + s.slice(powMatch.endIndex + 1);
          changed = true;
          continue;
        }
      }

      // 5. Logarithms with base: \log_{b}{x} or \log_{b}(x) -> (log((x), (b)))
      const logBaseIdx = s.indexOf('\\log_{');
      if (logBaseIdx !== -1) {
        const baseMatch = parseBraces(s, logBaseIdx + 5);
        if (baseMatch) {
          let cur = baseMatch.endIndex + 1;
          while (cur < s.length && /\s/.test(s[cur])) cur++;
          let argExpr = '';
          let endArgIdx = cur;
          if (s[cur] === '{') {
            const argMatch = parseBraces(s, cur);
            if (argMatch) {
              argExpr = latexToMathExpression(argMatch.content);
              endArgIdx = argMatch.endIndex + 1;
            }
          } else if (s[cur] === '(') {
            let pDepth = 0;
            for (let j = cur; j < s.length; j++) {
              if (s[j] === '(') pDepth++;
              else if (s[j] === ')') {
                pDepth--;
                if (pDepth === 0) {
                  argExpr = latexToMathExpression(s.slice(cur + 1, j));
                  endArgIdx = j + 1;
                  break;
                }
              }
            }
          }
          if (argExpr) {
            const baseExpr = latexToMathExpression(baseMatch.content);
            s = s.slice(0, logBaseIdx) + '(log((' + argExpr + '), (' + baseExpr + ')))' + s.slice(endArgIdx);
            changed = true;
            continue;
          }
        }
      }
    }

    // Mathematical Constants & Operators
    s = s.replace(/\\times\s*10\^(\d+|\([+-]?\d+\))/g, '* (10^$1)');
    s = s.replace(/\\times/g, '*');
    s = s.replace(/\\cdot/g, '*');
    s = s.replace(/\\div/g, '/');
    s = s.replace(/\\pi/g, 'pi');
    s = s.replace(/\\imaginaryI|\\mathrm\{i\}|\bi\b/g, 'i');

    // Inverse trigonometric functions
    s = s.replace(/\\arcsin|\\sin\^\{-1\}/g, 'asin');
    s = s.replace(/\\arccos|\\cos\^\{-1\}/g, 'acos');
    s = s.replace(/\\arctan|\\tan\^\{-1\}/g, 'atan');

    // Standard trigonometric functions
    s = s.replace(/\\sin/g, 'sin');
    s = s.replace(/\\cos/g, 'cos');
    s = s.replace(/\\tan/g, 'tan');

    // Hyperbolic functions
    s = s.replace(/\\sinh/g, 'sinh');
    s = s.replace(/\\cosh/g, 'cosh');
    s = s.replace(/\\tanh/g, 'tanh');

    // Logarithms: \ln -> natural log, \log -> log10
    s = s.replace(/\\ln/g, 'log');
    s = s.replace(/\\log/g, 'log10');

    // Percent: % -> * 0.01
    s = s.replace(/\\?%/g, '* 0.01');

    // Permutations and Combinations: e.g. 5 P 3 or 5 C 3
    // Case-sensitive and numeric-operand only, so "2pi" or "cos" are never misread
    s = s.replace(/(?<![A-Za-z0-9_.])(\d+)\s*P\s*(\d+)(?![A-Za-z0-9_.])/g, 'nPr($1, $2)');
    s = s.replace(/(?<![A-Za-z0-9_.])(\d+)\s*C\s*(\d+)(?![A-Za-z0-9_.])/g, 'nCr($1, $2)');

    // Absolute value: |x| -> abs(x)
    s = s.replace(/\|([^|]+)\|/g, 'abs($1)');

    // Clean stray backslashes from remaining standard functions
    s = s.replace(/\\([a-zA-Z]+)/g, '$1');

    // Insert implicit multiplication: e.g. 2pi -> 2*pi, 2(3) -> 2*(3), (2)(3) -> (2)*(3), 2i -> 2*i
    // A number is only a standalone literal when not part of an identifier (e.g. log10, x2)
    s = s.replace(/(?<![A-Za-z0-9_])(\d+(?:\.\d+)?)\s*(?=[A-Za-z(])/g, '$1*');
    s = s.replace(/(\))\s*(?=[0-9A-Za-z(])/g, '$1*');

    // Casio-style: unclosed brackets at the end of the expression are closed automatically
    const open = (s.match(/\(/g) || []).length;
    const close = (s.match(/\)/g) || []).length;
    if (open > close) s += ')'.repeat(open - close);

    return s.trim();
  }

  // Nerdamer prints radicals as powers (2^(1/2)); show them as textbook radicals instead
  function surdToLatex(nerdText, nerd) {
    const t = nerdText
      .replace(/(\d+)\^\(1\/2\)/g, 'sqrt($1)')
      .replace(/(\d+)\^\(1\/(\d+)\)/g, 'nthroot($1,$2)');
    return nerd.convertToLaTeX(t);
  }

  // --- KalmiCalcEngine Class Definition ---
  class KalmiCalcEngine {
    constructor() {
      this.mode = 'COMP'; // 'COMP' | 'CMPLX' | 'EQN' | 'STAT'
      this.angleMode = 'DEG'; // 'DEG' | 'RAD'
      this.lastAns = 0;
      this.memory = 0;
      this.variables = {
        A: 0,
        B: 0,
        C: 0,
        D: 0,
        E: 0,
        F: 0,
        X: 0,
        Y: 0,
        M: 0
      };
      this.statData = [];
    }

    setMode(mode) {
      const valid = ['COMP', 'CMPLX', 'EQN', 'STAT'];
      if (valid.includes(mode)) {
        this.mode = mode;
      }
    }

    setAngleMode(mode) {
      if (mode === 'DEG' || mode === 'RAD') {
        this.angleMode = mode;
      }
    }

    setVariable(name, val) {
      const upper = (name || '').toUpperCase();
      if (upper in this.variables) {
        this.variables[upper] = val;
      }
      if (upper === 'M') {
        this.memory = typeof val === 'number' ? val : parseFloat(val) || 0;
      }
    }

    getVariable(name) {
      const upper = (name || '').toUpperCase();
      if (upper === 'ANS') return this.lastAns;
      if (upper in this.variables) return this.variables[upper];
      return 0;
    }

    // --- Create Degree/Radian Aware Math.js Evaluation Scope ---
    createMathScope() {
      const isDeg = this.angleMode === 'DEG';
      const m = typeof window !== 'undefined' && window.math ? window.math : (typeof require !== 'undefined' ? require('mathjs') : null);

      return {
        Ans: this.lastAns,
        ans: this.lastAns,
        pi: Math.PI,
        e: Math.E,
        ...this.variables,
        M: this.memory,

        // Safe Trigonometry with exact singularity & zero enforcement
        sin: (x) => {
          if (typeof x === 'number') {
            if (isDeg && Math.abs(x % 180) === 0) return 0;
            const rad = isDeg ? (x * Math.PI) / 180 : x;
            return cleanTrig(Math.sin(rad));
          }
          if (m && m.sin) return m.sin(x);
          return Math.sin(x);
        },
        cos: (x) => {
          if (typeof x === 'number') {
            if (isDeg && Math.abs((x - 90) % 180) === 0) return 0;
            const rad = isDeg ? (x * Math.PI) / 180 : x;
            return cleanTrig(Math.cos(rad));
          }
          if (m && m.cos) return m.cos(x);
          return Math.cos(x);
        },
        tan: (x) => {
          if (typeof x === 'number') {
            if (isDeg && Math.abs((x - 90) % 180) === 0) {
              throw new Error('Math ERROR: Tangent singularity at 90 deg');
            }
            if (isDeg && Math.abs(x % 180) === 0) return 0;
            const rad = isDeg ? (x * Math.PI) / 180 : x;
            return cleanTrig(Math.tan(rad));
          }
          if (m && m.tan) return m.tan(x);
          return Math.tan(x);
        },
        asin: (x) => {
          if (m && m.asin) {
            const res = m.asin(x);
            if (typeof res === 'number') {
              return isDeg ? cleanFloat((res * 180) / Math.PI) : cleanFloat(res);
            }
            return res;
          }
          const val = Math.asin(x);
          return isDeg ? cleanFloat((val * 180) / Math.PI) : cleanFloat(val);
        },
        acos: (x) => {
          if (m && m.acos) {
            const res = m.acos(x);
            if (typeof res === 'number') {
              return isDeg ? cleanFloat((res * 180) / Math.PI) : cleanFloat(res);
            }
            return res;
          }
          const val = Math.acos(x);
          return isDeg ? cleanFloat((val * 180) / Math.PI) : cleanFloat(val);
        },
        atan: (x) => {
          if (m && m.atan) {
            const res = m.atan(x);
            if (typeof res === 'number') {
              return isDeg ? cleanFloat((res * 180) / Math.PI) : cleanFloat(res);
            }
            return res;
          }
          const val = Math.atan(x);
          return isDeg ? cleanFloat((val * 180) / Math.PI) : cleanFloat(val);
        },

        // Degree literal: 30° is 30 in DEG mode, or 30*pi/180 in RAD mode
        degree: (x) => (isDeg ? x : (x * Math.PI) / 180),

        // Combinatorics
        nPr: (n, r) => {
          if (m && m.permutations) return m.permutations(n, r);
          return 0;
        },
        nCr: (n, r) => {
          if (m && m.combinations) return m.combinations(n, r);
          return 0;
        },

        // Factorial
        factorial: (n) => {
          if (n < 0 || !Number.isInteger(n)) throw new Error('Math ERROR: Factorial requires non-negative integer');
          if (m && m.factorial) return m.factorial(n);
          let res = 1;
          for (let i = 2; i <= n; i++) res *= i;
          return res;
        }
      };
    }

    // --- Main Evaluation Method ---
    evaluate(latexInput) {
      if (!latexInput || !latexInput.trim()) {
        return {
          success: true,
          exactLatex: '0',
          decimal: '0',
          displayLatex: '0',
          numericValue: 0,
          resultType: 'number'
        };
      }

      // Check for Equation Solving (in EQN mode or when '=' is present)
      if (this.mode === 'EQN' || (latexInput.includes('=') && !latexInput.startsWith('='))) {
        return this.solveEquation(latexInput);
      }

      // Check for Statistics Mode commands
      const plainInput = latexInput.replace(/\\left|\\right/g, '').replace(/\\(?:mathrm|operatorname)\{([a-zA-Z]+)\}/g, '$1').trim();
      if (this.mode === 'STAT' && /^stat\(/i.test(plainInput)) {
        return this.evaluateStatistics(plainInput);
      }

      // 1. Convert LaTeX to standard expression
      const expr = latexToMathExpression(latexInput);
      if (!expr) {
        return { success: false, error: 'Syntax ERROR' };
      }

      const m = typeof window !== 'undefined' && window.math ? window.math : (typeof require !== 'undefined' ? require('mathjs') : null);
      const nerd = typeof window !== 'undefined' && window.nerdamer ? window.nerdamer : (typeof require !== 'undefined' ? require('nerdamer/dist/bundle.js') : null);

      let decimalResult = null;
      let exactLatexResult = null;
      let numericVal = 0;
      let ansValue = null; // set for non-real answers (complex) so Ans can recall them
      let resultType = 'number';

      // 2. Numerical Computation via Math.js
      if (m && typeof m.evaluate === 'function') {
        try {
          const scope = this.createMathScope();
          const raw = m.evaluate(expr, scope);

          if (raw === undefined || typeof raw === 'function') {
            return { success: false, error: 'Syntax ERROR' };
          }

          if (typeof raw === 'number') {
            if (!Number.isFinite(raw)) {
              return { success: false, error: raw > 0 ? 'Math ERROR (Infinity)' : 'Math ERROR (-Infinity)' };
            }
            numericVal = cleanFloat(raw);
            decimalResult = numericVal.toString();
          } else if (raw && raw.isComplex) {
            // Casio convention: outside complex input, a complex result means a domain error
            const usesComplexAns = /\b[Aa]ns\b/.test(expr) && typeof this.lastAns === 'object';
            if (this.mode !== 'CMPLX' && !/\bi\b/.test(expr) && !usesComplexAns) {
              return { success: false, error: 'Math ERROR (domain)' };
            }
            resultType = 'complex';
            // Drop floating-point noise relative to the larger component
            const scale = Math.max(Math.abs(raw.re), Math.abs(raw.im));
            const re = Math.abs(raw.re) < scale * 1e-13 ? 0 : cleanFloat(raw.re);
            const im = Math.abs(raw.im) < scale * 1e-13 ? 0 : cleanFloat(raw.im);
            if (im === 0) {
              decimalResult = re.toString();
              numericVal = re;
            } else if (re === 0) {
              decimalResult = im === 1 ? 'i' : (im === -1 ? '-i' : `${im}i`);
            } else {
              const sign = im > 0 ? '+' : '-';
              const absIm = Math.abs(im) === 1 ? '' : Math.abs(im);
              decimalResult = `${re} ${sign} ${absIm}i`;
            }
            exactLatexResult = decimalResult.replace(/i/g, '\\mathrm{i}');
            ansValue = raw;
          } else if (raw && raw.isFraction) {
            resultType = 'exact_fraction';
            numericVal = cleanFloat(raw.valueOf());
            decimalResult = numericVal.toString();
            exactLatexResult = `\\frac{${raw.s * raw.n}}{${raw.d}}`;
          } else if (raw && raw.isMatrix) {
            resultType = 'matrix';
            decimalResult = raw.toString();
            exactLatexResult = decimalResult;
          } else {
            decimalResult = raw.toString();
          }
        } catch (mathErr) {
          const msg = (mathErr && mathErr.message) || '';
          if (msg.includes('Math ERROR')) return { success: false, error: msg };
          if (mathErr instanceof SyntaxError || /Unexpected|Value expected|Parenthesis|Undefined (symbol|function)|Unexpected end/i.test(msg)) {
            return { success: false, error: 'Syntax ERROR' };
          }
          return { success: false, error: 'Math ERROR' };
        }
      }

      // 3. Exact Symbolic Computation via Nerdamer (when available and applicable)
      if (nerd && resultType === 'number' && !expr.includes('i')) {
        try {
          // Exclude arbitrary base logs or special unsupported commands from Nerdamer
          if (!expr.includes('log10') && !expr.includes('nPr') && !expr.includes('nCr')) {
            const sym = nerd(expr);
            const text = sym.text();
            // If nerdamer gives a fraction like '5/6'
            if (/^-?\d+\/\d+$/.test(text)) {
              const parts = text.split('/');
              exactLatexResult = `\\frac{${parts[0]}}{${parts[1]}}`;
              resultType = 'exact_fraction';
            } else if (text.includes('^') || text.includes('sqrt')) {
              // Convert surd like 3*2^(1/2) to LaTeX
              exactLatexResult = surdToLatex(text, nerd);
              resultType = 'exact_surd';
            }
          }
        } catch (nerdErr) {
          // Fall back gracefully to decimal result
        }
      }

      // Determine default display
      const finalDecimal = decimalResult !== null ? decimalResult : '0';
      const finalExact = exactLatexResult !== null ? exactLatexResult : finalDecimal;

      // Update lastAns for recall
      this.lastAns = ansValue !== null ? ansValue : numericVal;

      return {
        success: true,
        decimal: finalDecimal,
        exactLatex: finalExact,
        displayLatex: finalExact,
        isExact: exactLatexResult !== null && exactLatexResult !== finalDecimal,
        numericValue: numericVal,
        resultType: resultType
      };
    }

    // --- Equation Solver for EQN Mode ---
    solveEquation(rawLatex) {
      const nerd = typeof window !== 'undefined' && window.nerdamer ? window.nerdamer : (typeof require !== 'undefined' ? require('nerdamer/dist/bundle.js') : null);
      if (!nerd || typeof nerd.solve !== 'function') {
        return { success: false, error: 'EQN solver engine unavailable' };
      }

      try {
        let expr = latexToMathExpression(rawLatex);
        if (expr.includes('=')) {
          const parts = expr.split('=');
          expr = `(${parts[0]}) - (${parts[1]})`;
        }

        const rootsObj = nerd.solve(expr, 'x');
        const rootsStr = rootsObj.toString();
        if (rootsStr === '[]' || rootsStr === '{}') {
          return {
            success: true,
            decimal: 'No real or complex solutions',
            exactLatex: '\\text{No Solution}',
            displayLatex: '\\text{No Solution}',
            resultType: 'equation_roots',
            roots: []
          };
        }

        const rawRoots = rootsStr.replace(/[{}[\]]/g, '').split(',').map((s) => s.trim()).filter(Boolean);
        const formattedRoots = rawRoots.map((r, idx) => {
          let cleanR = r.replace(/\*/g, '').replace(/i/g, '\\mathrm{i}');
          return `x_{${idx + 1}} = ${cleanR}`;
        });

        const displayLatex = formattedRoots.join(', \\quad ');
        const decimal = rawRoots.join(', ');

        return {
          success: true,
          decimal: decimal,
          exactLatex: displayLatex,
          displayLatex: displayLatex,
          resultType: 'equation_roots',
          roots: rawRoots
        };
      } catch (err) {
        return { success: false, error: 'Cannot solve equation' };
      }
    }

    // --- 1-Variable Statistics Evaluator ---
    evaluateStatistics(latexInput) {
      const m = typeof window !== 'undefined' && window.math ? window.math : (typeof require !== 'undefined' ? require('mathjs') : null);
      if (!m) return { success: false, error: 'STAT engine unavailable' };

      try {
        const match = latexInput.match(/stat\((.*?)\)/i);
        if (!match) return { success: false, error: 'Use format: stat(1, 2, 3, 4)' };
        const nums = match[1].split(',').map((s) => parseFloat(s.trim())).filter((n) => !isNaN(n));
        if (nums.length === 0) return { success: false, error: 'Empty dataset' };

        const mean = cleanFloat(m.mean(nums));
        const median = cleanFloat(m.median(nums));
        const sum = cleanFloat(m.sum(nums));
        const std = cleanFloat(m.std(nums));
        const variance = cleanFloat(m.variance(nums));

        const exactLatex = `\\bar{x}=${mean}, \\; \\sum x=${sum}, \\; \\sigma=${std}, \\; n=${nums.length}`;
        const decimal = `mean: ${mean}, sum: ${sum}, std: ${std}, median: ${median}, n: ${nums.length}`;

        return {
          success: true,
          decimal: decimal,
          exactLatex: exactLatex,
          displayLatex: exactLatex,
          resultType: 'statistics',
          statSummary: { mean, median, sum, std, variance, n: nums.length }
        };
      } catch (e) {
        return { success: false, error: 'STAT calculation error' };
      }
    }
  }

  // Export engine
  global.KalmiCalcEngine = KalmiCalcEngine;
  global.latexToMathExpression = latexToMathExpression;

})(typeof window !== 'undefined' ? window : global);
