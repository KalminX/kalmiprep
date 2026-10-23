/**
 * KalmiPrep Scientific Calculator - interface controller.
 *
 * Pairs a MathLive <math-field> (natural textbook input) with a Casio-style keypad
 * and the KalmiCalcEngine (engine.js). This module owns ALL calculator state
 * (expression, answer, memory, angle mode, history, SHIFT/ALPHA/HYP flags).
 * Modal visibility is the only thing owned by the global store (store.js).
 *
 * Idempotent: safe to load repeatedly (hx-boost page swaps); listeners and the
 * public API are registered exactly once.
 */
(function (global) {
  'use strict';

  if (global.KalmiCalcUI) return; // already initialised on this document

  const STORAGE_KEY = 'kalmiprep_calc_memento';
  const MODE_LABELS = { COMP: 'COMP', CMPLX: 'CMPLX', EQN: 'EQN', STAT: 'STAT' };

  const state = {
    mathfield: null,
    engine: null,
    shift: false,
    alpha: false,
    hyp: false,
    pendingStore: false, // SHIFT+RCL pressed: next ALPHA variable key stores the answer
    result: null,
    format: 'exact', // 'exact' | 'decimal'
    history: [],
    historyIndex: -1,
  };

  // Variable assigned to each ALPHA key (matches the red labels on the keypad)
  const ALPHA_VARS = { NEG: 'A', DEG: 'B', HYP: 'C', SIN: 'D', COS: 'E', TAN: 'F', LPAREN: 'X', RPAREN: 'Y' };

  // ---------- engine & persistence ----------
  function getEngine() {
    if (!state.engine) {
      state.engine = new global.KalmiCalcEngine();
      try {
        const saved = JSON.parse(localStorage.getItem(STORAGE_KEY) || '{}');
        if (saved.angleMode) state.engine.setAngleMode(saved.angleMode);
        if (saved.mode) state.engine.setMode(saved.mode);
        if (typeof saved.lastAns === 'number') state.engine.lastAns = saved.lastAns;
        if (typeof saved.memory === 'number') state.engine.memory = saved.memory;
        if (saved.variables && typeof saved.variables === 'object') {
          Object.keys(saved.variables).forEach((k) => {
            if (typeof saved.variables[k] === 'number') state.engine.setVariable(k, saved.variables[k]);
          });
        }
        if (Array.isArray(state.history) && Array.isArray(saved.history)) state.history = saved.history;
      } catch (e) { /* corrupted storage: start fresh */ }
    }
    return state.engine;
  }

  function saveState() {
    try {
      const eng = getEngine();
      const vars = {};
      Object.keys(eng.variables).forEach((k) => {
        if (typeof eng.variables[k] === 'number') vars[k] = eng.variables[k];
      });
      localStorage.setItem(STORAGE_KEY, JSON.stringify({
        angleMode: eng.angleMode,
        mode: eng.mode,
        lastAns: typeof eng.lastAns === 'number' ? eng.lastAns : 0,
        memory: eng.memory,
        variables: vars,
        history: state.history.slice(0, 30),
        latex: state.mathfield ? state.mathfield.value : '',
      }));
    } catch (e) { /* storage unavailable (private mode / quota) */ }
  }

  // ---------- MathLive field ----------
  function initMathField() {
    const container = document.getElementById('calc-mathfield-container');
    if (!container || !global.customElements || !global.customElements.get('math-field')) return null;

    // Re-create when the page was swapped and our field is detached from the live container
    if (state.mathfield && container.contains(state.mathfield)) return state.mathfield;

    const ML = global.MathLive && global.MathLive.MathfieldElement;
    if (ML) {
      ML.fontsDirectory = null; // fonts are served by mathlive-fonts.css (self-hosted, no CDN)
      ML.soundsDirectory = null;
    }

    const field = document.createElement('math-field');
    field.id = 'calc-mathlive-field';
    field.setAttribute('aria-label', 'Calculator expression');
    field.setAttribute('math-virtual-keyboard-policy', 'manual'); // our own keypad is the keyboard
    field.setAttribute('smart-superscript', 'true');
    field.setAttribute('smart-fence', 'true');
    field.className = 'w-full';

    try {
      const saved = JSON.parse(localStorage.getItem(STORAGE_KEY) || '{}');
      if (typeof saved.latex === 'string' && saved.latex) field.value = saved.latex;
    } catch (e) { /* ignore */ }

    field.addEventListener('input', () => {
      state.historyIndex = -1;
    });
    // Bubble phase on purpose: MathLive must process the key first (fractions on "/", arrows,
    // Backspace inside nested structures). The modal-level handler (bindModal) then stops the
    // event from reaching page shortcuts and handles Escape / Alt+C.
    field.addEventListener('keydown', (e) => {
      if (e.key === 'Enter') {
        e.preventDefault();
        executeEvaluation();
      }
    });

    container.innerHTML = '';
    container.appendChild(field);
    state.mathfield = field;
    return field;
  }

  function insertLatex(latex) {
    const f = initMathField();
    if (!f) return;
    f.executeCommand(['insert', latex]);
    f.focus();
  }

  // ---------- display ----------
  function refreshChrome() {
    const eng = getEngine();
    const $ = (id) => document.getElementById(id);
    const toggle = (id, on) => { const el = $(id); if (el) el.classList.toggle('hidden', !on); };

    toggle('calc-badge-shift', state.shift);
    toggle('calc-badge-alpha', state.alpha);
    toggle('calc-badge-hyp', state.hyp);
    toggle('calc-badge-sto', state.pendingStore);
    toggle('calc-badge-mem', eng.memory !== 0);
    toggle('calc-badge-replay', state.history.length > 0);
    toggle('calc-eqn-keys', eng.mode === 'EQN' || eng.mode === 'STAT');

    const angle = $('calc-badge-angle');
    if (angle) angle.textContent = eng.angleMode;
    const mode = $('calc-badge-mode');
    if (mode) mode.textContent = MODE_LABELS[eng.mode] || eng.mode;

    const shiftKey = $('calc-key-shift');
    const alphaKey = $('calc-key-alpha');
    if (shiftKey) shiftKey.setAttribute('aria-pressed', String(state.shift));
    if (alphaKey) alphaKey.setAttribute('aria-pressed', String(state.alpha));

    // Highlight keys whose secondary function is currently armed
    document.querySelectorAll('#scientific-calculator-modal [data-sec]').forEach((el) => {
      el.classList.toggle('calc-sec-armed', (state.shift && el.dataset.sec === 'shift') || (state.alpha && el.dataset.sec === 'alpha'));
    });
  }

  function clearModifiers() {
    state.shift = false;
    state.alpha = false;
    refreshChrome();
  }

  function renderOutput(content, mathy) {
    const out = document.getElementById('calc-result-output');
    if (!out) return;
    out.classList.remove('calc-error');
    out.textContent = '';
    if (mathy && global.katex) {
      try {
        global.katex.render(content, out, { throwOnError: false, displayMode: false });
        return;
      } catch (e) { /* fall through to plain text */ }
    }
    out.textContent = content;
  }

  function showResult(res) {
    state.result = res;
    const sd = document.getElementById('calc-sd-indicator');
    if (sd) {
      sd.classList.toggle('hidden', !res.isExact);
      sd.textContent = state.format === 'exact' ? 'S⇔D' : 'D';
    }
    if (state.format === 'decimal' || !res.isExact) {
      renderOutput(res.decimal, res.resultType === 'complex');
      if (res.resultType === 'complex') renderOutput(res.displayLatex, true);
    } else {
      renderOutput(res.displayLatex, true);
    }
  }

  function showError(message) {
    const out = document.getElementById('calc-result-output');
    const sd = document.getElementById('calc-sd-indicator');
    if (sd) sd.classList.add('hidden');
    if (!out) return;
    out.textContent = message; // textContent: never interpreted as HTML
    out.classList.add('calc-error');
    out.setAttribute('role', 'alert');
  }

  // ---------- evaluation ----------
  function executeEvaluation() {
    const f = initMathField();
    if (!f) return;
    const latex = f.value.trim();
    if (!latex) { renderOutput('0', false); return; }

    const eng = getEngine();
    const res = eng.evaluate(latex);
    if (res.success) {
      state.format = 'exact';
      showResult(res);
      state.history.unshift({ latex, display: res.displayLatex, decimal: res.decimal, isExact: !!res.isExact });
      if (state.history.length > 30) state.history.pop();
      state.historyIndex = -1;
      saveState();
    } else {
      showError(res.error || 'Syntax ERROR');
    }
    refreshChrome();
    f.focus();
  }

  function recallHistory(delta) {
    const f = initMathField();
    if (!f || state.history.length === 0) return;
    if (delta < 0) {
      state.historyIndex = state.historyIndex === -1 ? 0 : Math.min(state.historyIndex + 1, state.history.length - 1);
    } else if (state.historyIndex <= 0) {
      state.historyIndex = -1;
      f.setValue('');
      renderOutput('0', false);
      f.focus();
      return;
    } else {
      state.historyIndex -= 1;
    }
    const item = state.history[state.historyIndex];
    f.setValue(item.latex);
    renderOutput(item.isExact ? item.display : item.decimal, item.isExact || /i/.test(item.decimal));
    f.focus();
  }

  // ---------- keypad ----------
  // Storing: SHIFT+RCL arms STO, then ALPHA + variable key stores the last answer.
  function tryAlphaVariable(key) {
    const name = ALPHA_VARS[key];
    if (!state.alpha || !name) return false;
    const eng = getEngine();
    if (state.pendingStore) {
      const value = state.result && typeof state.result.numericValue === 'number' ? state.result.numericValue : eng.lastAns;
      if (typeof value === 'number') eng.setVariable(name, value);
      state.pendingStore = false;
      clearModifiers();
      saveState();
      renderOutput(`${name} = ${value}`, false);
      return true;
    }
    insertLatex(name);
    clearModifiers();
    return true;
  }

  function trigKey(key, base) {
    if (tryAlphaVariable(key)) return;
    let fn;
    if (state.hyp) fn = `\\${base}h`;
    else if (state.shift) fn = `\\arc${base}`;
    else fn = `\\${base}`;
    state.hyp = false;
    insertLatex(`${fn}\\left(#?\\right)`);
    clearModifiers();
  }

  const HANDLERS = {
    SHIFT() { state.shift = !state.shift; if (state.shift) state.alpha = false; refreshChrome(); },
    ALPHA() { state.alpha = !state.alpha; if (state.alpha) state.shift = false; refreshChrome(); },
    HYP() { if (tryAlphaVariable('HYP')) return; state.hyp = !state.hyp; refreshChrome(); },

    AC() {
      const f = initMathField();
      if (f) f.setValue('');
      state.result = null;
      state.historyIndex = -1;
      state.pendingStore = false;
      state.hyp = false;
      renderOutput('0', false);
      const sd = document.getElementById('calc-sd-indicator');
      if (sd) sd.classList.add('hidden');
      clearModifiers();
      if (f) f.focus();
      saveState();
    },
    DEL() {
      const f = initMathField();
      if (!f) return;
      f.executeCommand(['deleteBackward']);
      clearModifiers();
      f.focus();
    },

    NAV_LEFT() { const f = initMathField(); if (f) { f.executeCommand(['moveToPreviousChar']); f.focus(); } },
    NAV_RIGHT() { const f = initMathField(); if (f) { f.executeCommand(['moveToNextChar']); f.focus(); } },
    NAV_UP() { recallHistory(-1); },
    NAV_DOWN() { recallHistory(1); },

    FRAC() { insertLatex('\\frac{#?}{#?}'); clearModifiers(); },
    SQRT() { insertLatex(state.shift ? '\\sqrt[3]{#?}' : '\\sqrt{#?}'); clearModifiers(); },
    SQUARE() { insertLatex(state.shift ? '^{3}' : '^{2}'); clearModifiers(); },
    POWER() { insertLatex(state.shift ? '\\sqrt[#?]{#?}' : '^{#?}'); clearModifiers(); },
    LOG() { insertLatex(state.shift ? '10^{#?}' : '\\log\\left(#?\\right)'); clearModifiers(); },
    LN() { insertLatex(state.shift ? 'e^{#?}' : '\\ln\\left(#?\\right)'); clearModifiers(); },

    SIN() { trigKey('SIN', 'sin'); },
    COS() { trigKey('COS', 'cos'); },
    TAN() { trigKey('TAN', 'tan'); },

    NEG() {
      if (tryAlphaVariable('NEG')) return;
      insertLatex(state.shift ? '\\left|#?\\right|' : '-');
      clearModifiers();
    },
    DEGREE() {
      if (tryAlphaVariable('DEG')) return;
      insertLatex('^{\\circ}');
      clearModifiers();
    },
    LPAREN() { if (tryAlphaVariable('LPAREN')) return; insertLatex('\\left(#?\\right)'); clearModifiers(); },
    RPAREN() { if (tryAlphaVariable('RPAREN')) return; const f = initMathField(); if (f) { f.executeCommand(['moveToNextChar']); f.focus(); } clearModifiers(); },
    IMAG() { insertLatex('\\imaginaryI'); clearModifiers(); },

    MUL() { insertLatex(state.shift ? '\\mathrm{P}' : '\\times'); clearModifiers(); },
    DIV() { insertLatex(state.shift ? '\\mathrm{C}' : '\\div'); clearModifiers(); },
    ADD() { insertLatex('+'); clearModifiers(); },
    SUB() { insertLatex('-'); clearModifiers(); },
    DOT() {
      if (state.shift) insertLatex(String(Math.random().toFixed(3))); // Ran#
      else insertLatex('.');
      clearModifiers();
    },
    EXP() {
      if (state.shift) insertLatex('\\pi');
      else if (state.alpha) insertLatex('e');
      else insertLatex('\\times10^{#?}');
      clearModifiers();
    },
    FACT() { insertLatex('!'); clearModifiers(); },
    PERM() { insertLatex('\\mathrm{P}'); clearModifiers(); },
    COMB() { insertLatex('\\mathrm{C}'); clearModifiers(); },
    PI() { insertLatex('\\pi'); clearModifiers(); },
    EULER() { insertLatex('e'); clearModifiers(); },
    HELPER(payload) { insertLatex(payload); },

    ANS() {
      insertLatex(state.shift ? '%' : '\\mathrm{Ans}');
      clearModifiers();
    },

    EQUALS() { executeEvaluation(); clearModifiers(); },

    SD_TOGGLE() {
      if (!state.result || !state.result.success || !state.result.isExact) return;
      state.format = state.format === 'exact' ? 'decimal' : 'exact';
      showResult(state.result);
      const f = initMathField(); if (f) f.focus();
    },

    MEM_PLUS() {
      const eng = getEngine();
      const value = state.result && typeof state.result.numericValue === 'number' ? state.result.numericValue : null;
      if (value !== null) {
        eng.memory += state.shift ? -value : value;
        eng.setVariable('M', eng.memory);
        saveState();
      }
      clearModifiers();
    },
    RCL() {
      if (state.shift) { state.pendingStore = true; state.shift = false; state.alpha = true; refreshChrome(); return; }
      insertLatex('M');
      clearModifiers();
    },
    MEM_CLEAR() {
      const eng = getEngine();
      eng.memory = 0;
      eng.setVariable('M', 0);
      saveState();
      refreshChrome();
    },

    ANGLE_TOGGLE() {
      const eng = getEngine();
      eng.setAngleMode(eng.angleMode === 'DEG' ? 'RAD' : 'DEG');
      saveState();
      refreshChrome();
      const f = initMathField();
      if (f && f.value.trim()) executeEvaluation();
    },
    MODE_TOGGLE() { toggleModeModal(); },

    DIGIT(payload) { insertLatex(payload); clearModifiers(); },
  };

  function handleKeyPress(action, payload) {
    const fn = HANDLERS[action];
    if (!fn) return; // unknown action: never silently insert text
    initMathField();
    fn(payload);
  }

  // ---------- modes ----------
  function toggleModeModal() {
    const modal = document.getElementById('calc-mode-selector-modal');
    if (modal) modal.classList.toggle('hidden');
  }

  function selectMode(mode) {
    const eng = getEngine();
    eng.setMode(mode);
    const modal = document.getElementById('calc-mode-selector-modal');
    if (modal) modal.classList.add('hidden');
    refreshChrome();
    saveState();
    const f = initMathField(); if (f) f.focus();
  }

  // ---------- lifecycle ----------
  function bindModal() {
    const modal = document.getElementById('scientific-calculator-modal');
    if (!modal || modal.dataset.calcBound === 'true') return;
    modal.dataset.calcBound = 'true';
    // Keep focus (and the caret) in the mathfield when keys are pressed with a mouse / finger
    modal.addEventListener('mousedown', (e) => {
      if (e.target.closest('button')) e.preventDefault();
    });
    // Calculator keystrokes must never leak to exam shortcuts (A-D / 1-5 answer selection).
    // Escape and Alt+C stay available when focus is on a keypad button.
    modal.addEventListener('keydown', (e) => {
      e.stopPropagation();
      if (e.key === 'Escape') {
        e.preventDefault();
        if (global.useKalmiStore) global.useKalmiStore.getState().closeCalc();
      } else if (e.altKey && (e.key === 'c' || e.key === 'C')) {
        e.preventDefault();
        if (global.useKalmiStore) global.useKalmiStore.getState().toggleCalc();
      }
    });
  }

  function onCalcModalOpened() {
    bindModal();
    const f = initMathField();
    refreshChrome();
    if (f) global.setTimeout(() => f.focus(), 30);
  }

  function init() {
    if (!document.getElementById('scientific-calculator-modal')) return; // unrelated page: do nothing
    bindModal();
    initMathField();
    refreshChrome();
  }

  global.KalmiCalcUI = {
    handleKeyPress,
    executeEvaluation,
    toggleModeModal,
    selectMode,
    onCalcModalOpened,
    init,
    getEngine,
    actions: Object.keys(HANDLERS),
    _state: state, // exposed for tests only
  };

  if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', init, { once: true });
  } else {
    init();
  }
})(typeof window !== 'undefined' ? window : globalThis);
