/**
 * KalmiPrep Zustand Vanilla State Engine
 * Framework-agnostic centralized reactive state manager.
 * Powered by the official Zustand createStore architecture.
 */

(function () {
  'use strict';

  // --- Official Zustand Vanilla createStore implementation ---
  const createStore = (createState) => {
    let state;
    const listeners = new Set();

    const setState = (partial, replace) => {
      const nextState = typeof partial === 'function' ? partial(state) : partial;
      if (!Object.is(nextState, state)) {
        const previousState = state;
        state = (replace ?? (typeof nextState !== 'object' || nextState === null))
          ? nextState
          : Object.assign({}, state, nextState);
        listeners.forEach((listener) => listener(state, previousState));
      }
    };

    const getState = () => state;

    const subscribe = (listener) => {
      listeners.add(listener);
      return () => listeners.delete(listener);
    };

    const destroy = () => {
      listeners.clear();
    };

    const api = { setState, getState, subscribe, destroy };
    state = createState(setState, getState, api);
    return api;
  };

  // --- Factorial Helper ---
  function factorial(n) {
    if (n < 0 || !Number.isInteger(n)) return NaN;
    if (n === 0 || n === 1) return 1;
    if (n > 170) return Infinity; // JS precision limit
    let res = 1;
    for (let i = 2; i <= n; i++) res *= i;
    return res;
  }

  // --- GoF Memento Pattern for Calculator State Persistence ---
  const CALC_MEMENTO_KEY = 'kalmiprep_calc_memento';

  function loadCalcMemento() {
    try {
      const saved = localStorage.getItem(CALC_MEMENTO_KEY);
      if (saved) return JSON.parse(saved);
    } catch (e) {}
    return null;
  }

  function saveCalcMemento(state) {
    try {
      const memento = {
        isOpen: Boolean(state.isOpen),
        angleMode: state.angleMode || 'DEG',
        expression: state.expression || '',
        result: state.result || '0',
        lastAns: state.lastAns || '0',
        memory: typeof state.memory === 'number' ? state.memory : 0,
        isEvaluated: Boolean(state.isEvaluated),
      };
      localStorage.setItem(CALC_MEMENTO_KEY, JSON.stringify(memento));
    } catch (e) {}
  }

  // --- Scientific Expression Evaluator (Powered by Math.js with native fallback) ---
  function safeEvalScientific(expr, angleMode = 'DEG', lastAns = 0) {
    if (!expr || !expr.trim()) return '0';

    // Auto-balance unclosed parentheses
    const openCount = (expr.match(/\(/g) || []).length;
    const closeCount = (expr.match(/\)/g) || []).length;
    let balanced = expr;
    if (openCount > closeCount) {
      balanced = expr + ')'.repeat(openCount - closeCount);
    }

    const numericAns = parseFloat(lastAns) || 0;

    // 1. Math.js Industry Standard Engine
    if (typeof window !== 'undefined' && window.math && typeof window.math.evaluate === 'function') {
      try {
        let cleaned = balanced
          .replace(/×/g, '*')
          .replace(/÷/g, '/')
          .replace(/π/g, 'pi')
          .replace(/Ans/gi, `(${numericAns})`)
          .replace(/EXP/g, '*10^')
          .replace(/(\d+(\.\d+)?)%/g, '($1 * 0.01)');

        const scope = angleMode === 'DEG' ? {
          Ans: numericAns,
          ans: numericAns,
          sin: (x) => window.math.sin(window.math.unit(x, 'deg')),
          cos: (x) => {
            const rad = (x * Math.PI) / 180;
            return Math.abs(Math.cos(rad)) < 1e-15 ? 0 : Math.cos(rad);
          },
          tan: (x) => {
            if (Math.abs((x - 90) % 180) < 1e-10) return Infinity;
            return window.math.tan(window.math.unit(x, 'deg'));
          },
          asin: (x) => (window.math.asin(x) * 180) / Math.PI,
          acos: (x) => (window.math.acos(x) * 180) / Math.PI,
          atan: (x) => (window.math.atan(x) * 180) / Math.PI,
          ln: (x) => window.math.log(x),
          log: (x) => window.math.log10(x),
          cbrt: (x) => window.math.cbrt(x),
        } : {
          Ans: numericAns,
          ans: numericAns,
          ln: (x) => window.math.log(x),
          log: (x) => window.math.log10(x),
          cbrt: (x) => window.math.cbrt(x),
        };

        const result = window.math.evaluate(cleaned, scope);
        if (typeof result === 'function') return 'Error';
        if (typeof result === 'number') {
          if (!isFinite(result)) return result > 0 ? 'Infinity' : '-Infinity';
          if (Math.abs(result) < 1e-12 && Math.abs(result) > 0) return '0';
          return parseFloat(result.toPrecision(12)).toString();
        }
        return window.math.format(result, { precision: 12 });
      } catch (err) {
        // Fall back to native evaluator
      }
    }

    // 2. Safe Fallback Evaluator
    try {
      let sanitized = balanced
        .replace(/×/g, '*')
        .replace(/÷/g, '/')
        .replace(/π/g, 'Math.PI')
        .replace(/\be\b/g, 'Math.E')
        .replace(/Ans/gi, `(${numericAns})`)
        .replace(/EXP/g, '*10**')
        .replace(/(\d+(\.\d+)?)%/g, '($1 * 0.01)');

      sanitized = sanitized.replace(/(\d+)!/g, 'factorial($1)');

      if (angleMode === 'DEG') {
        sanitized = sanitized
          .replace(/sin\(([^)]+)\)/g, 'Math.sin(($1) * Math.PI / 180)')
          .replace(/cos\(([^)]+)\)/g, 'Math.cos(($1) * Math.PI / 180)')
          .replace(/tan\(([^)]+)\)/g, 'Math.tan(($1) * Math.PI / 180)')
          .replace(/asin\(([^)]+)\)/g, '(Math.asin($1) * 180 / Math.PI)')
          .replace(/acos\(([^)]+)\)/g, '(Math.acos($1) * 180 / Math.PI)')
          .replace(/atan\(([^)]+)\)/g, '(Math.atan($1) * 180 / Math.PI)');
      } else {
        sanitized = sanitized
          .replace(/sin\(/g, 'Math.sin(')
          .replace(/cos\(/g, 'Math.cos(')
          .replace(/tan\(/g, 'Math.tan(')
          .replace(/asin\(/g, 'Math.asin(')
          .replace(/acos\(/g, 'Math.acos(')
          .replace(/atan\(/g, 'Math.atan(');
      }

      sanitized = sanitized
        .replace(/log\(/g, 'Math.log10(')
        .replace(/ln\(/g, 'Math.log(')
        .replace(/sqrt\(/g, 'Math.sqrt(')
        .replace(/cbrt\(/g, 'Math.cbrt(')
        .replace(/\^/g, '**');

      if (!/^[0-9+\-*/().,MathPIEfactorial\s*]+$/.test(sanitized)) {
        return 'Error';
      }

      const evalFunc = new Function('factorial', `return (${sanitized});`);
      const val = evalFunc(factorial);

      if (typeof val !== 'number' || isNaN(val)) return 'Error';
      if (!isFinite(val)) return val > 0 ? 'Infinity' : '-Infinity';

      return parseFloat(val.toPrecision(12)).toString();
    } catch (e) {
      return 'Error';
    }
  }

  // --- Central KalmiPrep Zustand Store ---
  let tickInterval = null;
  let heartbeatInterval = null;

  const useKalmiStore = createStore((set, get) => ({
    // ----------------------------------------------------
    // 1. THEME SLICE
    // ----------------------------------------------------
    theme: document.documentElement.classList.contains('dark') ? 'dark' : 'light',
    toggleTheme: () => {
      const isDark = document.documentElement.classList.toggle('dark');
      const nextTheme = isDark ? 'dark' : 'light';
      localStorage.setItem('color-theme', nextTheme);
      set({ theme: nextTheme });
      if (window.lucide) lucide.createIcons();
    },

    // ----------------------------------------------------
    // 2. EXAM TIMER SLICE (Server-Synced)
    // ----------------------------------------------------
    timer: {
      remainingSeconds: 0,
      targetEndTime: null,
      isRunning: false,
      isExpired: false,
      sessionId: null,
      syncUrl: null,
      formatted: '--:--'
    },

    initTimer: (sessionId, remainingSeconds, syncUrl) => {
      // Clear existing intervals
      if (tickInterval) clearInterval(tickInterval);
      if (heartbeatInterval) clearInterval(heartbeatInterval);

      const targetEndTime = Date.now() + (remainingSeconds * 1000);
      const mins = Math.floor(remainingSeconds / 60);
      const secs = remainingSeconds % 60;
      const formatted = `${mins.toString().padStart(2, '0')}:${secs.toString().padStart(2, '0')}`;

      set((state) => ({
        timer: {
          ...state.timer,
          sessionId,
          remainingSeconds,
          targetEndTime,
          syncUrl,
          isRunning: true,
          isExpired: remainingSeconds <= 0,
          formatted
        }
      }));

      // Immediately run first tick
      get().tickTimer();

      // Start 1-second countdown tick
      tickInterval = setInterval(() => {
        get().tickTimer();
      }, 1000);

      // Start periodic 45-second server heartbeat
      if (syncUrl) {
        heartbeatInterval = setInterval(() => {
          get().syncTimerWithServer();
        }, 45000);
      }
    },

    tickTimer: () => {
      const { targetEndTime, isRunning, syncUrl } = get().timer;
      if (!isRunning || !targetEndTime) return;

      const remaining = Math.max(0, Math.floor((targetEndTime - Date.now()) / 1000));
      const mins = Math.floor(remaining / 60);
      const secs = remaining % 60;
      const formatted = `${mins.toString().padStart(2, '0')}:${secs.toString().padStart(2, '0')}`;
      const isExpired = remaining <= 0;

      set((state) => ({
        timer: {
          ...state.timer,
          remainingSeconds: remaining,
          formatted,
          isExpired
        }
      }));

      // Update DOM timer element
      const timerDisplay = document.getElementById('countdown-timer');
      if (timerDisplay) {
        timerDisplay.innerText = formatted;
        if (remaining < 120) {
          timerDisplay.classList.add('text-rose-600', 'animate-pulse');
        } else if (remaining < 300) {
          timerDisplay.classList.add('text-amber-500');
        }
      }

      // Handle expiration
      if (isExpired) {
        get().stopTimer();
        const submitForm = document.getElementById('final-submit-form');
        if (submitForm) {
          alert('Time is up! Your examination is being submitted automatically.');
          submitForm.submit();
        }
      }
    },

    syncTimerWithServer: async () => {
      const { syncUrl, isRunning } = get().timer;
      if (!syncUrl || !isRunning) return;

      try {
        const csrfToken = document.querySelector('meta[name="csrf-token"]')?.content || '';
        const res = await fetch(syncUrl, {
          method: 'POST',
          headers: {
            'X-CSRFToken': csrfToken,
            'Content-Type': 'application/json'
          }
        });
        if (res.ok) {
          const data = await res.json();
          if (data.is_expired) {
            get().stopTimer();
            const submitForm = document.getElementById('final-submit-form');
            if (submitForm) submitForm.submit();
          } else if (data.remaining_seconds !== undefined) {
            // Reconcile target end time with server truth
            const newTargetEndTime = Date.now() + (data.remaining_seconds * 1000);
            set((state) => ({
              timer: {
                ...state.timer,
                remainingSeconds: data.remaining_seconds,
                targetEndTime: newTargetEndTime
              }
            }));
          }
        }
      } catch (e) {
        // Network sync failure, fallback to client clock
      }
    },

    stopTimer: () => {
      if (tickInterval) clearInterval(tickInterval);
      if (heartbeatInterval) clearInterval(heartbeatInterval);
      tickInterval = null;
      heartbeatInterval = null;
      set((state) => ({
        timer: {
          ...state.timer,
          isRunning: false
        }
      }));
    },

    // ----------------------------------------------------
    // 3. SCIENTIFIC CALCULATOR SLICE (GoF Command & Memento Pattern)
    // ----------------------------------------------------
    calc: (() => {
      const saved = loadCalcMemento() || {};
      return {
        isOpen: saved.isOpen || false,
        angleMode: saved.angleMode || 'DEG',
        expression: saved.expression || '',
        result: saved.result || '0',
        lastAns: saved.lastAns || '0',
        memory: typeof saved.memory === 'number' ? saved.memory : 0,
        isEvaluated: saved.isEvaluated || false,
      };
    })(),

    toggleCalc: () => {
      set((state) => ({
        calc: { ...state.calc, isOpen: !state.calc.isOpen }
      }));
      get().renderCalcDOM();
    },

    openCalc: () => {
      set((state) => ({
        calc: { ...state.calc, isOpen: true }
      }));
      get().renderCalcDOM();
    },

    closeCalc: () => {
      set((state) => ({
        calc: { ...state.calc, isOpen: false }
      }));
      get().renderCalcDOM();
    },

    setCalcAngleMode: (mode) => {
      set((state) => ({
        calc: { ...state.calc, angleMode: mode }
      }));
      get().evaluateCalc(false);
      get().renderCalcDOM();
    },

    appendCalc: (token) => {
      const { expression, isEvaluated, lastAns } = get().calc;
      let nextExpr = expression;
      let tok = token;

      if (tok === '(-)') {
        tok = '-';
      }

      const isOperator = ['+', '-', '*', '/', '^', '%'].includes(tok);

      if (isEvaluated) {
        if (isOperator) {
          nextExpr = 'Ans' + tok;
        } else {
          nextExpr = tok;
        }
      } else {
        if (!nextExpr && isOperator && lastAns && lastAns !== '0') {
          nextExpr = 'Ans' + tok;
        } else {
          nextExpr += tok;
        }
      }

      set((state) => ({
        calc: {
          ...state.calc,
          expression: nextExpr,
          isEvaluated: false
        }
      }));

      get().evaluateCalc(false);
      get().renderCalcDOM();
    },

    backspaceCalc: () => {
      const { expression } = get().calc;
      if (!expression) return;

      let nextExpr = expression;
      const funcTokens = [
        'asin(', 'acos(', 'atan(', 'sin(', 'cos(', 'tan(',
        'log(', 'sqrt(', 'cbrt(', 'ln(', '10^(', 'e^('
      ];
      let matched = false;

      for (const tok of funcTokens) {
        if (nextExpr.endsWith(tok)) {
          nextExpr = nextExpr.slice(0, -tok.length);
          matched = true;
          break;
        }
      }

      if (!matched) {
        if (nextExpr.endsWith('Ans')) {
          nextExpr = nextExpr.slice(0, -3);
        } else if (nextExpr.endsWith('EXP')) {
          nextExpr = nextExpr.slice(0, -3);
        } else {
          nextExpr = nextExpr.slice(0, -1);
        }
      }

      set((state) => ({
        calc: { ...state.calc, expression: nextExpr, isEvaluated: false }
      }));

      get().evaluateCalc(false);
      get().renderCalcDOM();
    },

    clearCalc: () => {
      set((state) => ({
        calc: { ...state.calc, expression: '', result: '0', isEvaluated: false }
      }));
      get().renderCalcDOM();
    },

    evaluateCalc: (isFinal = true) => {
      const { expression, angleMode, lastAns } = get().calc;
      if (!expression || !expression.trim()) {
        set((state) => ({
          calc: { ...state.calc, result: '0', isEvaluated: isFinal }
        }));
        if (isFinal) get().renderCalcDOM();
        return;
      }

      const res = safeEvalScientific(expression, angleMode, lastAns);
      set((state) => ({
        calc: {
          ...state.calc,
          result: res,
          lastAns: isFinal && res !== 'Error' ? res : state.calc.lastAns,
          isEvaluated: isFinal && res !== 'Error'
        }
      }));

      if (isFinal) {
        get().renderCalcDOM();
      }
    },

    memoryAdd: () => {
      const { result, memory } = get().calc;
      const num = parseFloat(result);
      if (!isNaN(num)) {
        set((state) => ({
          calc: { ...state.calc, memory: memory + num }
        }));
      }
      get().renderCalcDOM();
    },

    memorySubtract: () => {
      const { result, memory } = get().calc;
      const num = parseFloat(result);
      if (!isNaN(num)) {
        set((state) => ({
          calc: { ...state.calc, memory: memory - num }
        }));
      }
      get().renderCalcDOM();
    },

    memoryRecall: () => {
      const { memory } = get().calc;
      get().appendCalc(memory.toString());
    },

    memoryClear: () => {
      set((state) => ({
        calc: { ...state.calc, memory: 0 }
      }));
      get().renderCalcDOM();
    },

    // ----------------------------------------------------
    // 4. STRICT NAVIGATION HIGHLIGHT SLICE
    // ----------------------------------------------------
    navigation: {
      activeSection: 'core',
      isPending: false,
      pendingTarget: null,
      isInitialized: false,
    },

    startNavTransition: (targetUrl) => {
      set((state) => ({
        navigation: {
          ...state.navigation,
          isPending: true,
          pendingTarget: targetUrl
        }
      }));
      window.dispatchEvent(new CustomEvent('kalmi:nav-pending-start', {
        detail: { targetUrl }
      }));
    },

    finishNavTransition: (newSection, animate = true) => {
      const prevSection = get().navigation.activeSection;
      set((state) => ({
        navigation: {
          ...state.navigation,
          activeSection: newSection,
          isPending: false,
          pendingTarget: null,
          isInitialized: true
        }
      }));
      window.dispatchEvent(new CustomEvent('kalmi:nav-pending-finish', {
        detail: { activeSection: newSection, prevSection, animate }
      }));
    },

    cancelNavTransition: () => {
      set((state) => ({
        navigation: {
          ...state.navigation,
          isPending: false,
          pendingTarget: null
        }
      }));
      window.dispatchEvent(new CustomEvent('kalmi:nav-pending-cancel'));
    },

    renderCalcDOM: () => {
      const widget = document.getElementById('scientific-calculator-modal');
      if (!widget) return;

      const {
        isOpen,
        expression,
        result,
        lastAns,
        angleMode,
        memory
      } = get().calc;

      // Visibility state
      if (isOpen) {
        widget.classList.remove('hidden');
      } else {
        widget.classList.add('hidden');
      }

      const exprEl = document.getElementById('calc-expression-display');
      const resultEl = document.getElementById('calc-result-display');
      const angleBtn = document.getElementById('calc-angle-mode-btn');
      const memIndicator = document.getElementById('calc-memory-indicator');
      const ansIndicator = document.getElementById('calc-ans-indicator');

      // Display text
      if (exprEl) exprEl.innerText = expression || '0';
      if (resultEl) resultEl.innerText = result || '0';
      if (angleBtn) angleBtn.innerText = angleMode;

      // Badges
      if (memIndicator) memIndicator.classList.toggle('hidden', memory === 0);
      if (ansIndicator) ansIndicator.classList.toggle('hidden', !lastAns || lastAns === '0');

      if (window.lucide) lucide.createIcons();

      // Persist to Memento storage
      saveCalcMemento(get().calc);
    }
  }));

  // Export to window
  window.useKalmiStore = useKalmiStore;

  // Reconcile timer when switching tabs or waking device
  document.addEventListener('visibilitychange', () => {
    if (!document.hidden && useKalmiStore.getState().timer.isRunning) {
      useKalmiStore.getState().tickTimer();
      useKalmiStore.getState().syncTimerWithServer();
    }
  });

  // Global keyboard shortcuts and direct calculator numeric typing
  document.addEventListener('keydown', (e) => {
    // If user is actively typing in a form input, textarea, or contentEditable element, skip
    if (['INPUT', 'TEXTAREA', 'SELECT'].includes(e.target.tagName) || e.target.isContentEditable) {
      return;
    }

    const calcState = useKalmiStore.getState().calc;
    const hasCBTOptions = !!document.querySelector('.cbt-option-item');
    const isAltC = (e.key === 'c' || e.key === 'C') && e.altKey;
    const isPlainC = (e.key === 'c' || e.key === 'C') && !e.altKey && !e.ctrlKey && !e.metaKey;

    if (isAltC || (isPlainC && !hasCBTOptions && !calcState.isOpen)) {
      e.preventDefault();
      useKalmiStore.getState().toggleCalc();
      return;
    }

    // Direct Keypad typing when calculator is active & visible
    if (calcState.isOpen) {
      if (e.key === 'Escape') {
        e.preventDefault();
        useKalmiStore.getState().closeCalc();
      } else if (e.key >= '0' && e.key <= '9') {
        e.preventDefault();
        useKalmiStore.getState().appendCalc(e.key);
      } else if (e.key === '.') {
        e.preventDefault();
        useKalmiStore.getState().appendCalc('.');
      } else if (e.key === '+') {
        e.preventDefault();
        useKalmiStore.getState().appendCalc('+');
      } else if (e.key === '-') {
        e.preventDefault();
        useKalmiStore.getState().appendCalc('-');
      } else if (e.key === '*' || e.key === 'x' || e.key === 'X') {
        e.preventDefault();
        useKalmiStore.getState().appendCalc('*');
      } else if (e.key === '/') {
        e.preventDefault();
        useKalmiStore.getState().appendCalc('/');
      } else if (e.key === '(' || e.key === ')') {
        e.preventDefault();
        useKalmiStore.getState().appendCalc(e.key);
      } else if (e.key === '^') {
        e.preventDefault();
        useKalmiStore.getState().appendCalc('^');
      } else if (e.key === '%') {
        e.preventDefault();
        useKalmiStore.getState().appendCalc('%');
      } else if (e.key === 'Enter' || e.key === '=') {
        e.preventDefault();
        useKalmiStore.getState().evaluateCalc(true);
      } else if (e.key === 'Backspace') {
        e.preventDefault();
        useKalmiStore.getState().backspaceCalc();
      } else if (e.key === 'Delete') {
        e.preventDefault();
        useKalmiStore.getState().clearCalc();
      }
    }
  });

  // Self-initializing lifecycle: restore persistent state on direct load, DOMContentLoaded, and HTMX swaps
  function bootstrapCalculator() {
    if (window.useKalmiStore) {
      useKalmiStore.getState().renderCalcDOM();
    }
  }

  bootstrapCalculator();
  document.addEventListener('DOMContentLoaded', bootstrapCalculator);
  document.addEventListener('htmx:load', bootstrapCalculator);

})();
