/**
 * KalmiPrep Scientific Calculator - Controller
 * 
 * GoF Command Pattern dispatcher & UI Controller.
 * Encapsulates keypad actions, keyboard bindings, DOM synchronization,
 * sign repetition validation, and LaTeX Natural Textbook rendering via KaTeX.
 */

(function (global) {
  'use strict';

  class KalmiCalcController {
    constructor() {
      this.engine = new (global.KalmiCalcEngine || class { evaluate() { return { success: true, result: '0' }; } })();
      this.memento = global.KalmiCalcMemento || { load: () => null, save: () => {} };
      this.validator = global.KalmiCalcValidator || { sanitize: (e, t) => (e || '') + t };
      this.formatter = global.KalmiCalcFormatter || { toLatex: (e) => e, renderToElement: (el, l, f) => { if (el) el.textContent = f || l; } };

      const saved = this.memento.load() || {};
      this.state = {
        isOpen: false,
        angleMode: saved.angleMode || 'DEG',
        expression: saved.expression || '',
        result: saved.result || '0',
        lastAns: saved.lastAns || '0',
        memory: typeof saved.memory === 'number' ? saved.memory : 0,
        isEvaluated: Boolean(saved.isEvaluated),
        isFractionMode: Boolean(saved.isFractionMode),
        currentFraction: saved.currentFraction || null,
      };

      this.boundKeyHandler = null;
      this.init();
    }

    init() {
      this.bindShortcuts();
      this.render();
    }

    getState() {
      return this.state;
    }

    // ----------------------------------------------------
    // Command Pattern Handlers
    // ----------------------------------------------------
    open() {
      if (!document.getElementById('scientific-calculator-modal')) return;
      this.state.isOpen = true;
      this.syncStore();
      this.render();
    }

    close() {
      if (!document.getElementById('scientific-calculator-modal')) return;
      this.state.isOpen = false;
      this.syncStore();
      this.render();
    }

    toggle() {
      if (!document.getElementById('scientific-calculator-modal')) return;
      this.state.isOpen = !this.state.isOpen;
      this.syncStore();
      this.render();
    }

    setAngleMode(mode) {
      this.state.angleMode = mode;
      this.evaluate(false);
      this.syncStore();
      this.render();
    }

    toggleAngleMode() {
      this.setAngleMode(this.state.angleMode === 'DEG' ? 'RAD' : 'DEG');
    }

    toggleFractionMode() {
      if (this.state.currentFraction) {
        this.state.isFractionMode = !this.state.isFractionMode;
        this.syncStore();
        this.render();
      }
    }

    clear() {
      this.state.expression = '';
      this.state.result = '0';
      this.state.isEvaluated = false;
      this.state.currentFraction = null;
      this.state.isFractionMode = false;
      this.syncStore();
      this.render();
    }

    backspace() {
      let expr = this.state.expression;
      if (!expr || this.state.isEvaluated) {
        this.clear();
        return;
      }

      const fnMatch = expr.match(/(sin|cos|tan|asin|acos|atan|sinh|cosh|tanh|ln|log|sqrt|cbrt)\($/);
      if (fnMatch) {
        expr = expr.slice(0, -fnMatch[0].length);
        if (expr.endsWith('×') || expr.endsWith('*')) {
          expr = expr.slice(0, -1);
        }
      } else {
        expr = expr.slice(0, -1);
      }

      this.state.expression = expr;
      this.evaluate(false);
      this.syncStore();
      this.render();
    }

    append(token) {
      let { expression, isEvaluated, lastAns } = this.state;
      const isOperator = ['+', '-', '−', '*', '/', '×', '÷', '^', '%'].includes(token);

      if (isEvaluated) {
        if (isOperator) {
          expression = (lastAns && lastAns !== 'Error' && lastAns !== 'Math ERROR' ? lastAns : '0');
        } else {
          expression = '';
        }
        this.state.isEvaluated = false;
      }

      // Pass through GoF validator to prevent repeated signs and illegal sequences
      this.state.expression = this.validator.sanitize(expression, token, lastAns);
      this.evaluate(false);
      this.syncStore();
      this.render();
    }

    evaluate(isFinal = true) {
      const { expression, angleMode, lastAns } = this.state;
      if (!expression || !expression.trim()) {
        if (isFinal) {
          this.state.result = '0';
          this.state.isEvaluated = false;
          this.state.currentFraction = null;
          this.syncStore();
          this.render();
        }
        return;
      }

      const res = this.engine.evaluate(expression, angleMode, lastAns);
      const output = res.success ? res.result : (res.error || 'Error');

      if (isFinal) {
        const isErr = !res.success || output === 'Error' || output === 'Math ERROR';
        this.state.result = output;
        this.state.lastAns = isErr ? this.state.lastAns : output;
        this.state.isEvaluated = true;
        this.state.currentFraction = isErr ? null : (res.fraction || null);
        this.state.isFractionMode = false;
      } else {
        if (res.success && output !== 'Error' && output !== 'Math ERROR') {
          this.state.result = output;
          this.state.currentFraction = res.fraction || null;
        }
      }

      this.syncStore();
      this.render();
    }

    memoryAdd() {
      const current = parseFloat(this.state.result) || 0;
      this.state.memory += current;
      this.syncStore();
      this.render();
    }

    memorySubtract() {
      const current = parseFloat(this.state.result) || 0;
      this.state.memory -= current;
      this.syncStore();
      this.render();
    }

    memoryRecall() {
      this.append(this.state.memory.toString());
    }

    memoryClear() {
      this.state.memory = 0;
      this.syncStore();
      this.render();
    }

    // ----------------------------------------------------
    // DOM Synchronization & LaTeX Rendering
    // ----------------------------------------------------
    render() {
      const widget = document.getElementById('scientific-calculator-modal');
      if (!widget) return;

      const { isOpen, expression, result, lastAns, angleMode, memory, isFractionMode, currentFraction } = this.state;

      widget.classList.toggle('hidden', !isOpen);
      widget.setAttribute('aria-hidden', isOpen ? 'false' : 'true');

      const exprEl = document.getElementById('calc-expression-display');
      const resultEl = document.getElementById('calc-result-display');
      const angleBtn = document.getElementById('calc-angle-mode-btn');
      const memIndicator = document.getElementById('calc-memory-indicator');
      const ansIndicator = document.getElementById('calc-ans-indicator');
      const sdBtn = document.getElementById('calc-sd-btn');
      const sdIndicator = document.getElementById('calc-sd-indicator');

      // 1. Natural Textbook Expression line via KaTeX LaTeX
      if (exprEl) {
        const latexExpr = this.formatter.toLatex(expression || '0');
        this.formatter.renderToElement(exprEl, latexExpr, expression || '0');
      }

      // 2. High-precision Result line (Stacked Fraction vs Decimal)
      if (resultEl) {
        let resultLatex = result || '0';
        if (isFractionMode && currentFraction && currentFraction.latex) {
          resultLatex = currentFraction.latex;
        }
        this.formatter.renderToElement(resultEl, resultLatex, result || '0');
      }

      // 3. Status badges and indicators
      if (angleBtn) angleBtn.textContent = angleMode;
      if (memIndicator) memIndicator.classList.toggle('hidden', memory === 0);
      if (ansIndicator) ansIndicator.classList.toggle('hidden', !lastAns || lastAns === '0');
      if (sdIndicator) sdIndicator.classList.toggle('hidden', !currentFraction);
      if (sdBtn) {
        sdBtn.classList.toggle('opacity-50', !currentFraction);
        sdBtn.classList.toggle('cursor-not-allowed', !currentFraction);
      }

      // 4. Update dedicated LaTeX code conversion bar
      const latexCodeEl = document.getElementById('calc-latex-code');
      if (latexCodeEl) {
        const fullLatex = this.formatter.buildFullLatex(expression, result, isFractionMode, currentFraction);
        latexCodeEl.textContent = fullLatex;
      }

      if (global.lucide && typeof global.lucide.createIcons === 'function') {
        global.lucide.createIcons();
      }

      this.memento.save(this.state);
    }

    copyLatex() {
      const fullLatex = this.formatter.buildFullLatex(
        this.state.expression,
        this.state.result,
        this.state.isFractionMode,
        this.state.currentFraction
      );
      if (typeof navigator !== 'undefined' && navigator.clipboard && typeof navigator.clipboard.writeText === 'function') {
        navigator.clipboard.writeText(fullLatex).catch(() => {});
      }
      const copyBtn = document.getElementById('calc-copy-latex-btn');
      if (copyBtn) {
        const original = copyBtn.innerHTML;
        copyBtn.innerHTML = '<span class="text-emerald-400 font-bold">Copied!</span>';
        setTimeout(() => {
          copyBtn.innerHTML = original;
          if (global.lucide && typeof global.lucide.createIcons === 'function') {
            global.lucide.createIcons();
          }
        }, 1500);
      }
    }

    syncStore() {
      if (global.useKalmiStore && typeof global.useKalmiStore.setState === 'function') {
        global.useKalmiStore.setState((s) => ({
          calc: {
            ...s.calc,
            ...this.state,
          }
        }));
      }
    }

    // ----------------------------------------------------
    // Keyboard Handling
    // ----------------------------------------------------
    bindShortcuts() {
      if (this.boundKeyHandler || global.__kalmiCalcShortcutsBound) return;
      global.__kalmiCalcShortcutsBound = true;

      this.boundKeyHandler = (e) => {
        const widget = document.getElementById('scientific-calculator-modal');
        if (!widget) return;

        if (['INPUT', 'TEXTAREA', 'SELECT'].includes(e.target.tagName) || e.target.isContentEditable) {
          return;
        }

        const isAltC = e.altKey && (e.key === 'c' || e.key === 'C');
        if (isAltC) {
          e.preventDefault();
          this.toggle();
          return;
        }

        if (this.state.isOpen) {
          if (e.key === 'Escape') {
            e.preventDefault();
            this.close();
          } else if (e.key >= '0' && e.key <= '9') {
            e.preventDefault();
            this.append(e.key);
          } else if (e.key === '.') {
            e.preventDefault();
            this.append('.');
          } else if (e.key === '+') {
            e.preventDefault();
            this.append('+');
          } else if (e.key === '-' || e.key === '−') {
            e.preventDefault();
            this.append('−');
          } else if (e.key === '*' || e.key === 'x' || e.key === 'X') {
            e.preventDefault();
            this.append('×');
          } else if (e.key === '/') {
            e.preventDefault();
            this.append('÷');
          } else if (e.key === '(' || e.key === ')') {
            e.preventDefault();
            this.append(e.key);
          } else if (e.key === '^') {
            e.preventDefault();
            this.append('^(');
          } else if (e.key === '%') {
            e.preventDefault();
            this.append('%');
          } else if (e.key === 'Enter' || e.key === '=') {
            e.preventDefault();
            this.evaluate(true);
          } else if (e.key === 'Backspace') {
            e.preventDefault();
            this.backspace();
          } else if (e.key === 'Delete') {
            e.preventDefault();
            this.clear();
          }
        }
      };

      document.addEventListener('keydown', this.boundKeyHandler);
    }
  }

  // Singleton instance
  let calcInstance = null;
  function getCalcController() {
    if (!calcInstance) {
      calcInstance = new KalmiCalcController();
    }
    return calcInstance;
  }

  global.KalmiCalc = {
    getInstance: getCalcController,
    open: () => getCalcController().open(),
    close: () => getCalcController().close(),
    toggle: () => getCalcController().toggle(),
    clear: () => getCalcController().clear(),
    backspace: () => getCalcController().backspace(),
    append: (t) => getCalcController().append(t),
    evaluate: (f) => getCalcController().evaluate(f),
    setAngleMode: (m) => getCalcController().setAngleMode(m),
    toggleAngleMode: () => getCalcController().toggleAngleMode(),
    toggleFractionMode: () => getCalcController().toggleFractionMode(),
    memoryAdd: () => getCalcController().memoryAdd(),
    memorySubtract: () => getCalcController().memorySubtract(),
    memoryRecall: () => getCalcController().memoryRecall(),
    memoryClear: () => getCalcController().memoryClear(),
    copyLatex: () => getCalcController().copyLatex(),
    render: () => getCalcController().render(),
  };

  // Lifecycle bootstrapper for HTMX and DOM readiness
  function bootstrap() {
    if (document.getElementById('scientific-calculator-modal')) {
      getCalcController().render();
    }
  }

  if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', bootstrap);
  } else {
    bootstrap();
  }
  document.addEventListener('htmx:load', bootstrap);

  if (typeof module !== 'undefined' && module.exports) {
    module.exports = { KalmiCalcController, getCalcController };
  }

})(typeof window !== 'undefined' ? window : globalThis);
