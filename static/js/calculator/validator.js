/**
 * KalmiPrep Scientific Calculator - Input Validator
 * 
 * GoF Chain of Responsibility / State Validator.
 * Prevents repeating signs, duplicate operators, multiple decimal points,
 * and invalid syntax sequences according to physical Casio fx-991 rules.
 */

(function (global) {
  'use strict';

  const KalmiCalcValidator = {
    /**
     * Sanitizes and validates an append action.
     * Prevents repeating signs, illegal operator sequences, and duplicate decimals.
     * 
     * @param {string} expr Current expression string
     * @param {string} token Input token to append
     * @param {string|number} lastAns Previous answer value
     * @returns {string} Sanitized new expression string
     */
    sanitize(expr, token, lastAns = '0') {
      if (!token) return expr || '';

      let t = token;
      if (t === '*') t = '×';
      if (t === '/') t = '÷';
      if (t === '-') t = '−';

      const isOp = ['+', '−', '×', '÷', '^', '%'].includes(t);
      const isDigit = /^[0-9]$/.test(t);

      // ----------------------------------------------------
      // 1. Binary & Unary Operators (+, −, ×, ÷, ^, %)
      // ----------------------------------------------------
      if (isOp) {
        if (!expr || expr === '0') {
          if (t === '−') return '−'; // unary minus to start a negative number
          if (lastAns && lastAns !== '0' && lastAns !== 'Error' && lastAns !== 'Math ERROR') {
            return 'Ans' + t;
          }
          return '0';
        }

        // Check if expression ends with an operator followed by a unary minus (e.g. '×−')
        if (/[+×÷^]−$/.test(expr)) {
          if (t === '−') return expr; // reject duplicate minus '--'
          return expr.slice(0, -2) + t; // replace operator pair with new operator
        }

        // Check if expression ends with a single operator
        if (/[+−×÷^%]$/.test(expr)) {
          // Allow unary minus following multiply, divide, or power
          if (t === '−' && /[×÷^]$/.test(expr)) {
            return expr + '−';
          }
          // If plus followed by minus, replace with minus
          if (t === '−' && expr.endsWith('+')) {
            return expr.slice(0, -1) + '−';
          }
          // Do not allow duplicate minus '--'
          if (expr.endsWith('−') && t === '−') {
            return expr;
          }
          // Replace last operator with the new operator
          return expr.slice(0, -1) + t;
        }

        // After an open parenthesis, only unary minus is allowed
        if (expr.endsWith('(')) {
          if (t === '−') return expr + '−';
          return expr; // block '+', '×', '÷' inside empty '('
        }

        return expr + t;
      }

      // ----------------------------------------------------
      // 2. Decimal Point (.)
      // ----------------------------------------------------
      if (t === '.') {
        if (!expr || /[+−×÷^%(]$/.test(expr)) {
          return (expr || '') + '0.';
        }
        // Extract the trailing number token
        const parts = expr.split(/[+−×÷^%(]/);
        const lastPart = parts[parts.length - 1];
        if (lastPart.includes('.')) {
          return expr; // reject duplicate decimal point in same number
        }
        return expr + '.';
      }

      // ----------------------------------------------------
      // 3. Digits (0 - 9)
      // ----------------------------------------------------
      if (isDigit) {
        const parts = expr.split(/[+−×÷^%(]/);
        const lastPart = parts[parts.length - 1];
        // Handle leading zeros: prevent '00' -> replace single '0' with digit
        if (lastPart === '0') {
          if (t === '0') return expr; // reject multiple leading zeros
          return expr.slice(0, -1) + t; // replace lone 0 with digit
        }
        return (expr === '0' ? '' : expr) + t;
      }

      // ----------------------------------------------------
      // 4. Parentheses
      // ----------------------------------------------------
      if (t === '(') {
        // Implicit multiplication: 2(3) -> 2×(3) or )( -> )×(
        if (/[0-9πe)]$|Ans$/.test(expr)) {
          return expr + '×(';
        }
        return expr + '(';
      }

      if (t === ')') {
        const openCount = (expr.match(/\(/g) || []).length;
        const closeCount = (expr.match(/\)/g) || []).length;
        if (openCount <= closeCount) return expr; // cannot close unopened paren
        if (/[+−×÷^(]$/.test(expr)) return expr; // cannot close on operator or empty '('
        return expr + ')';
      }

      // ----------------------------------------------------
      // 5. Mathematical Functions (sin(, cos(, sqrt(, etc.)
      // ----------------------------------------------------
      if (/^[a-z0-9]+\($/i.test(t)) {
        // Implicit multiplication: 2sin(30) -> 2×sin(30)
        if (/[0-9πe)]$|Ans$/.test(expr)) {
          return expr + '×' + t;
        }
        return (expr === '0' ? '' : expr) + t;
      }

      // ----------------------------------------------------
      // 6. Constants (pi, e)
      // ----------------------------------------------------
      if (t === 'π' || t === 'e') {
        if (/[0-9πe)]$|Ans$/.test(expr)) {
          return expr + '×' + t;
        }
        return (expr === '0' ? '' : expr) + t;
      }

      return expr + t;
    }
  };

  // Export for browser and Node.js
  if (typeof module !== 'undefined' && module.exports) {
    module.exports = { KalmiCalcValidator };
  }
  global.KalmiCalcValidator = KalmiCalcValidator;

})(typeof window !== 'undefined' ? window : globalThis);
