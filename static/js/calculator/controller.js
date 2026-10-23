/**
 * KalmiPrep Scientific Calculator - Controller
 * 
 * GoF Command Pattern dispatcher & UI Controller.
 * Encapsulates keypad actions, keyboard bindings, DOM synchronization,
 * sign repetition validation, LaTeX Natural Textbook rendering via KaTeX,
 * and 4-way Casio REPLAY directional cursor navigation (Up, Down, Left, Right).
 */

(function (global) {
  'use strict';

  class KalmiCalcController {
    constructor() {
      this.engine = new (global.KalmiCalcEngine || class { evaluate() { return { success: true, result: '0' }; } })();
      this.memento = global.KalmiCalcMemento || { load: () => null, save: () => {} };
      this.validator = global.KalmiCalcValidator || { sanitize: (e, t) => (e || '') + t };
      this.formatter = global.KalmiCalcFormatter || {
        toLatex: (e) => e,
        renderToElement: (el, l, f) => { if (el) el.textContent = f || l; },
        renderExpressionWithCursor: (el, expr, pos) => { if (el) el.textContent = expr || '0'; },
        buildFullLatex: (e, r) => e + ' = ' + r
      };
      this.converter = global.KalmiCalcConverter || { latexToMath: (l) => l };
      this.ast = new (global.KalmiCalcAST || class {
        clear() {}
        isEmpty() { return true; }
        insertText(t) {}
        insertTemplate(t) {}
        deleteBackward() {}
        navLeft() {}
        navRight() {}
        navUp() { return false; }
        navDown() { return false; }
        toLatex() { return ''; }
        toMathString() { return ''; }
      })();

      const saved = this.memento.load() || {};
      const initExpr = saved.expression || '';
      this.state = {
        isOpen: false,
        angleMode: saved.angleMode || 'DEG',
        expression: initExpr,
        cursorPos: initExpr.length,
        result: saved.result || '0',
        lastAns: saved.lastAns || '0',
        memory: typeof saved.memory === 'number' ? saved.memory : 0,
        isEvaluated: Boolean(saved.isEvaluated),
        isFractionMode: Boolean(saved.isFractionMode),
        currentFraction: saved.currentFraction || null,
      };

      this.history = [];
      this.historyIndex = -1;
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
    // MathLive Integration Helpers
    // ----------------------------------------------------
    getMathField() {
      if (typeof document === 'undefined') return null;
      return document.getElementById('calc-math-field');
    }

    setupMathField() {
      const mf = this.getMathField();
      if (!mf) return;

      if ('mathVirtualKeyboardPolicy' in mf) {
        mf.mathVirtualKeyboardPolicy = 'manual';
      }
      mf.menuItems = [];

      if (!mf._kalmiBound) {
        mf._kalmiBound = true;
        mf.addEventListener('input', () => {
          this.onMathFieldChange(mf.value);
        });
        mf.addEventListener('keydown', (e) => {
          if (e.key === 'Enter' || e.key === '=') {
            e.preventDefault();
            this.evaluate(true);
          }
        });
      }
    }

    onMathFieldChange(latex) {
      this.state.expression = this.converter.latexToMath(latex, this.state.lastAns);
      const latexCodeEl = document.getElementById('calc-latex-code');
      if (latexCodeEl) {
        latexCodeEl.textContent = latex || '0';
      }
      const mirror = document.getElementById('calc-text-mirror');
      if (mirror) {
        mirror.textContent = latex || '0';
      }
    }

    // ----------------------------------------------------
    // Command Pattern Handlers
    // ----------------------------------------------------
    open() {
      if (!document.getElementById('scientific-calculator-modal')) return;
      this.state.isOpen = true;
      this.syncStore();
      this.render();
      this.setupMathField();
      const mf = this.getMathField();
      if (mf && typeof mf.focus === 'function') {
        setTimeout(() => mf.focus(), 60);
      }
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

    // ----------------------------------------------------
    // Casio REPLAY Navigation (Up, Down, Left, Right)
    // ----------------------------------------------------
    navLeft() {
      const mf = this.getMathField();
      if (mf && typeof mf.executeCommand === 'function') {
        mf.executeCommand('moveToPreviousChar');
        return;
      }
      if (this.ast && typeof this.ast.isEmpty === 'function' && !this.ast.isEmpty()) {
        this.ast.navLeft();
        this.state.cursorPos = this.ast.cursor.offset;
        this.syncStore();
        this.render();
        return;
      }
      let { expression, cursorPos } = this.state;
      if (cursorPos === null || typeof cursorPos !== 'number') {
        cursorPos = expression.length;
      }
      if (cursorPos <= 0) {
        this.state.cursorPos = 0;
        this.render();
        return;
      }

      // Check if preceding token is a multi-character function (e.g. sin()
      const left = expression.slice(0, cursorPos);
      const fnMatch = left.match(/(sin|cos|tan|asin|acos|atan|sinh|cosh|tanh|ln|log|sqrt|cbrt)\($/);
      if (fnMatch) {
        cursorPos -= fnMatch[0].length;
      } else {
        cursorPos -= 1;
      }

      this.state.cursorPos = Math.max(0, cursorPos);
      this.syncStore();
      this.render();
    }

    navRight() {
      const mf = this.getMathField();
      if (mf && typeof mf.executeCommand === 'function') {
        const moved = mf.executeCommand('moveToNextPlaceholder');
        if (!moved) {
          mf.executeCommand('moveToNextChar');
        }
        return;
      }
      if (this.ast && typeof this.ast.isEmpty === 'function' && !this.ast.isEmpty()) {
        this.ast.navRight();
        this.state.cursorPos = this.ast.cursor.offset;
        this.syncStore();
        this.render();
        return;
      }
      let { expression, cursorPos } = this.state;
      if (cursorPos === null || typeof cursorPos !== 'number') {
        cursorPos = expression.length;
      }
      if (cursorPos >= expression.length) {
        this.state.cursorPos = expression.length;
        this.render();
        return;
      }

      // Check if subsequent token starts with a multi-character function
      const right = expression.slice(cursorPos);
      const fnMatch = right.match(/^(sin|cos|tan|asin|acos|atan|sinh|cosh|tanh|ln|log|sqrt|cbrt)\(/);
      if (fnMatch) {
        cursorPos += fnMatch[0].length;
      } else {
        cursorPos += 1;
      }

      this.state.cursorPos = Math.min(expression.length, cursorPos);
      this.syncStore();
      this.render();
    }

    navUp() {
      const mf = this.getMathField();
      if (mf && typeof mf.executeCommand === 'function') {
        mf.executeCommand('moveUp');
        return;
      }
      if (this.ast && typeof this.ast.isEmpty === 'function' && !this.ast.isEmpty()) {
        const handled = this.ast.navUp();
        this.state.cursorPos = this.ast.cursor.offset;
        this.syncStore();
        if (handled) {
          this.render();
          return;
        }
      }
      // In Casio fx-991: Up cycles through previous calculation history or jumps to start
      if (this.history.length > 0) {
        if (this.historyIndex === -1) {
          this.historyIndex = this.history.length - 1;
        } else if (this.historyIndex > 0) {
          this.historyIndex -= 1;
        }
        const item = this.history[this.historyIndex];
        if (item) {
          this.state.expression = item.expression;
          this.state.result = item.result;
          this.state.cursorPos = item.expression.length;
          this.syncStore();
          this.render();
          return;
        }
      }
      // Jump cursor to the very start of the expression
      this.state.cursorPos = 0;
      this.syncStore();
      this.render();
    }

    navDown() {
      const mf = this.getMathField();
      if (mf && typeof mf.executeCommand === 'function') {
        mf.executeCommand('moveDown');
        return;
      }
      if (this.ast && typeof this.ast.isEmpty === 'function' && !this.ast.isEmpty()) {
        const handled = this.ast.navDown();
        this.state.cursorPos = this.ast.cursor.offset;
        this.syncStore();
        if (handled) {
          this.render();
          return;
        }
      }
      // In Casio fx-991: Down cycles forward in history or jumps to end
      if (this.history.length > 0 && this.historyIndex !== -1) {
        if (this.historyIndex < this.history.length - 1) {
          this.historyIndex += 1;
          const item = this.history[this.historyIndex];
          if (item) {
            this.state.expression = item.expression;
            this.state.result = item.result;
            this.state.cursorPos = item.expression.length;
            this.syncStore();
            this.render();
            return;
          }
        } else {
          this.historyIndex = -1;
          this.state.expression = '';
          this.state.result = '0';
          this.state.cursorPos = 0;
          this.syncStore();
          this.render();
          return;
        }
      }
      // Jump cursor to the very end of the expression
      this.state.cursorPos = this.state.expression.length;
      this.syncStore();
      this.render();
    }

    clear() {
      const mf = this.getMathField();
      if (mf) mf.value = '';
      const mirror = document.getElementById('calc-text-mirror');
      if (mirror) mirror.textContent = '0';
      if (this.ast && typeof this.ast.clear === 'function') {
        this.ast.clear();
      }
      this.state.expression = '';
      this.state.cursorPos = 0;
      this.state.result = '0';
      this.state.isEvaluated = false;
      this.state.currentFraction = null;
      this.state.isFractionMode = false;
      this.syncStore();
      this.render();
    }

    backspace() {
      let { expression, isEvaluated, cursorPos } = this.state;
      if (!expression || isEvaluated) {
        this.clear();
        return;
      }

      const mf = this.getMathField();
      if (mf && typeof mf.executeCommand === 'function') {
        mf.executeCommand('deleteBackward');
        this.onMathFieldChange(mf.value);
        this.evaluate(false);
        this.syncStore();
        this.render();
        return;
      }

      if (this.ast && typeof this.ast.isEmpty === 'function' && !this.ast.isEmpty()) {
        this.ast.deleteBackward();
      }

      if (cursorPos === null || typeof cursorPos !== 'number' || cursorPos > expression.length) {
        cursorPos = expression.length;
      }

      if (cursorPos <= 0) return;

      let left = expression.slice(0, cursorPos);
      const right = expression.slice(cursorPos);

      const fnMatch = left.match(/(sin|cos|tan|asin|acos|atan|sinh|cosh|tanh|ln|log|sqrt|cbrt)\($/);
      if (fnMatch) {
        left = left.slice(0, -fnMatch[0].length);
        if (left.endsWith('×') || left.endsWith('*')) {
          left = left.slice(0, -1);
        }
      } else {
        left = left.slice(0, -1);
      }

      this.state.expression = left + right;
      this.state.cursorPos = left.length;
      this.evaluate(false);
      this.syncStore();
      this.render();
    }

    insertTemplate(type) {
      if (this.state.isEvaluated) {
        this.clear();
      }
      const mf = this.getMathField();
      if (mf && typeof mf.executeCommand === 'function') {
        if (type === 'fraction') mf.executeCommand(['insert', '\\frac{#?}{#?}']);
        else if (type === 'sqrt') mf.executeCommand(['insert', '\\sqrt{#?}']);
        else if (type === 'power') mf.executeCommand(['insert', '^{#?}']);
        else if (type === 'logbase') mf.executeCommand(['insert', '\\log_{#?}\\left(#?\\right)']);
        else if (type === 'nthroot') mf.executeCommand(['insert', '\\sqrt[#?]{#?}']);
        else if (type === 'abs') mf.executeCommand(['insert', '\\left|#?\\right|']);
        this.onMathFieldChange(mf.value);
        this.evaluate(false);
        this.syncStore();
        this.render();
        return;
      }

      if (this.ast && typeof this.ast.insertTemplate === 'function') {
        this.ast.insertTemplate(type);
        const mathExpr = this.ast.toMathString(this.state.lastAns);
        this.state.expression = mathExpr && mathExpr !== '0' ? mathExpr : this.state.expression;
        this.state.cursorPos = this.state.expression.length;
      }
      this.evaluate(false);
      this.syncStore();
      this.render();
    }

    append(token) {
      if (['fraction', 'logbase', 'nthroot', 'sqrt', 'power', 'abs'].includes(token)) {
        return this.insertTemplate(token);
      }

      const mf = this.getMathField();
      if (mf && typeof mf.executeCommand === 'function') {
        if (this.state.isEvaluated) {
          const isOperator = ['+', '-', '−', '*', '/', '×', '÷', '^', '%'].includes(token);
          if (isOperator) {
            const prev = (this.state.lastAns && this.state.lastAns !== 'Error' && this.state.lastAns !== 'Math ERROR' ? this.state.lastAns : '0');
            mf.value = prev;
          } else {
            mf.value = '';
          }
          this.state.isEvaluated = false;
        }

        if (token === 'sin(') mf.executeCommand(['insert', '\\sin\\left(#?\\right)']);
        else if (token === 'cos(') mf.executeCommand(['insert', '\\cos\\left(#?\\right)']);
        else if (token === 'tan(') mf.executeCommand(['insert', '\\tan\\left(#?\\right)']);
        else if (token === 'asin(') mf.executeCommand(['insert', '\\sin^{-1}\\left(#?\\right)']);
        else if (token === 'acos(') mf.executeCommand(['insert', '\\cos^{-1}\\left(#?\\right)']);
        else if (token === 'atan(') mf.executeCommand(['insert', '\\tan^{-1}\\left(#?\\right)']);
        else if (token === 'log(') mf.executeCommand(['insert', '\\log\\left(#?\\right)']);
        else if (token === 'ln(') mf.executeCommand(['insert', '\\ln\\left(#?\\right)']);
        else if (token === 'π') mf.executeCommand(['insert', '\\pi ']);
        else if (token === 'EXP') mf.executeCommand(['insert', '\\times 10^{#?}']);
        else if (token === 'nPr') mf.executeCommand(['insert', '\\mathrm{P}']);
        else if (token === 'nCr') mf.executeCommand(['insert', '\\mathrm{C}']);
        else if (token === 'Ans') mf.executeCommand(['insert', '\\mathrm{Ans}']);
        else if (token === '×') mf.executeCommand(['insert', '\\times ']);
        else if (token === '÷') mf.executeCommand(['insert', '\\div ']);
        else if (token === '−' || token === '-') mf.executeCommand(['insert', '-']);
        else if (token === '^2') mf.executeCommand(['insert', '^{2}']);
        else if (token === '^(') mf.executeCommand(['insert', '^{#?}']);
        else if (token === '10^(') mf.executeCommand(['insert', '10^{#?}']);
        else if (token === '!') mf.executeCommand(['insert', '!']);
        else if (token === '%') mf.executeCommand(['insert', '%']);
        else mf.executeCommand(['insert', token]);

        this.onMathFieldChange(mf.value);
        this.evaluate(false);
        this.syncStore();
        this.render();
        return;
      }

      let { expression, isEvaluated, lastAns, cursorPos } = this.state;
      const isOperator = ['+', '-', '−', '*', '/', '×', '÷', '^', '%'].includes(token);

      if (isEvaluated) {
        if (isOperator) {
          expression = (lastAns && lastAns !== 'Error' && lastAns !== 'Math ERROR' ? lastAns : '0');
          if (this.ast && typeof this.ast.clear === 'function') {
            this.ast.clear();
            this.ast.insertText(expression);
          }
        } else {
          expression = '';
          if (this.ast && typeof this.ast.clear === 'function') {
            this.ast.clear();
          }
        }
        this.state.isEvaluated = false;
        cursorPos = expression.length;
      }

      if (this.ast && typeof this.ast.insertText === 'function') {
        this.ast.insertText(token);
      }

      if (cursorPos === null || typeof cursorPos !== 'number' || cursorPos >= expression.length) {
        this.state.expression = this.validator.sanitize(expression, token, lastAns);
        this.state.cursorPos = this.state.expression.length;
      } else {
        const left = expression.slice(0, cursorPos);
        const right = expression.slice(cursorPos);
        const newLeft = this.validator.sanitize(left, token, lastAns);
        this.state.expression = newLeft + right;
        this.state.cursorPos = newLeft.length;
      }

      this.evaluate(false);
      this.syncStore();
      this.render();
    }

    evaluate(isFinal = true) {
      let { expression, angleMode, lastAns } = this.state;
      const mf = this.getMathField();
      if (mf && mf.value) {
        expression = this.converter.latexToMath(mf.value, lastAns);
        this.state.expression = expression;
      } else if (this.ast && typeof this.ast.isEmpty === 'function' && !this.ast.isEmpty()) {
        const astMath = this.ast.toMathString(lastAns);
        if (astMath && astMath !== '0') {
          expression = astMath;
        }
      }

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
        if (!isErr) {
          this.history.push({ expression, result: output });
          if (this.history.length > 30) this.history.shift();
          this.historyIndex = -1;
        }
        this.state.cursorPos = this.state.expression.length;
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

      const { isOpen, expression, result, lastAns, angleMode, memory, isFractionMode, currentFraction, cursorPos } = this.state;

      widget.classList.toggle('hidden', !isOpen);
      widget.setAttribute('aria-hidden', isOpen ? 'false' : 'true');

      const exprEl = document.getElementById('calc-expression-display');
      const resultEl = document.getElementById('calc-result-display');
      const angleBtn = document.getElementById('calc-angle-mode-btn');
      const memIndicator = document.getElementById('calc-memory-indicator');
      const ansIndicator = document.getElementById('calc-ans-indicator');
      const sdBtn = document.getElementById('calc-sd-btn');
      const sdIndicator = document.getElementById('calc-sd-indicator');

      // 1. Natural Textbook Expression line via MathLive / KaTeX
      const mf = this.getMathField();
      if (!mf && exprEl) {
        this.formatter.renderExpressionWithCursor(exprEl, expression, cursorPos, this.ast);
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
        let fullLatex = '0';
        if (mf && mf.value) {
          const exprLatex = mf.value;
          let resLatex = result || '0';
          if (isFractionMode && currentFraction && currentFraction.latex) {
            resLatex = currentFraction.latex;
          }
          fullLatex = result && result !== '0' && result !== 'Error' && result !== 'Math ERROR'
            ? `${exprLatex} = ${resLatex}`
            : exprLatex;
        } else if (this.ast && typeof this.ast.isEmpty === 'function' && !this.ast.isEmpty()) {
          const exprLatex = this.ast.toLatex(false);
          let resLatex = result || '0';
          if (isFractionMode && currentFraction && currentFraction.latex) {
            resLatex = currentFraction.latex;
          }
          fullLatex = result && result !== '0' && result !== 'Error' && result !== 'Math ERROR'
            ? `${exprLatex} = ${resLatex}`
            : exprLatex;
        } else {
          fullLatex = this.formatter.buildFullLatex(expression, result, isFractionMode, currentFraction);
        }
        latexCodeEl.textContent = fullLatex;
      }

      if (global.lucide && typeof global.lucide.createIcons === 'function') {
        global.lucide.createIcons();
      }

      this.memento.save(this.state);
    }

    copyLatex() {
      let fullLatex = '0';
      const mf = this.getMathField();
      if (mf && mf.value) {
        const exprLatex = mf.value;
        let resLatex = this.state.result || '0';
        if (this.state.isFractionMode && this.state.currentFraction && this.state.currentFraction.latex) {
          resLatex = this.state.currentFraction.latex;
        }
        fullLatex = this.state.result && this.state.result !== '0' && this.state.result !== 'Error'
          ? `${exprLatex} = ${resLatex}`
          : exprLatex;
      } else if (this.ast && typeof this.ast.isEmpty === 'function' && !this.ast.isEmpty()) {
        const exprLatex = this.ast.toLatex(false);
        let resLatex = this.state.result || '0';
        if (this.state.isFractionMode && this.state.currentFraction && this.state.currentFraction.latex) {
          resLatex = this.state.currentFraction.latex;
        }
        fullLatex = this.state.result && this.state.result !== '0' && this.state.result !== 'Error'
          ? `${exprLatex} = ${resLatex}`
          : exprLatex;
      } else {
        fullLatex = this.formatter.buildFullLatex(
          this.state.expression,
          this.state.result,
          this.state.isFractionMode,
          this.state.currentFraction
        );
      }
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
    // Keyboard Handling (Typing & Arrow Navigation)
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
          } else if (e.key === 'ArrowLeft') {
            e.preventDefault();
            this.navLeft();
          } else if (e.key === 'ArrowRight') {
            e.preventDefault();
            this.navRight();
          } else if (e.key === 'ArrowUp') {
            e.preventDefault();
            this.navUp();
          } else if (e.key === 'ArrowDown') {
            e.preventDefault();
            this.navDown();
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
    insertTemplate: (type) => getCalcController().insertTemplate(type),
    evaluate: (f) => getCalcController().evaluate(f),
    setAngleMode: (m) => getCalcController().setAngleMode(m),
    toggleAngleMode: () => getCalcController().toggleAngleMode(),
    toggleFractionMode: () => getCalcController().toggleFractionMode(),
    navLeft: () => getCalcController().navLeft(),
    navRight: () => getCalcController().navRight(),
    navUp: () => getCalcController().navUp(),
    navDown: () => getCalcController().navDown(),
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
