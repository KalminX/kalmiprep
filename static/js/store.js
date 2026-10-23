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

  // --- GoF Memento & Engine Delegates for Calculator ---
  function getCalcEngine() {
    if (typeof window !== 'undefined' && window.KalmiCalcEngine) {
      if (!window.__kalmiCalcEngineInstance) {
        window.__kalmiCalcEngineInstance = new window.KalmiCalcEngine();
      }
      return window.__kalmiCalcEngineInstance;
    }
    return null;
  }

  function loadCalcMemento() {
    if (typeof window !== 'undefined' && window.KalmiCalcMemento) {
      return window.KalmiCalcMemento.load();
    }
    try {
      const saved = localStorage.getItem('kalmiprep_calc_memento');
      if (saved) return JSON.parse(saved);
    } catch (e) {}
    return null;
  }

  function saveCalcMemento(state) {
    if (typeof window !== 'undefined' && window.KalmiCalcMemento) {
      return window.KalmiCalcMemento.save(state);
    }
    try {
      const memento = {
        isOpen: false,
        angleMode: state.angleMode || 'DEG',
        expression: state.expression || '',
        result: state.result || '0',
        lastAns: state.lastAns || '0',
        memory: typeof state.memory === 'number' ? state.memory : 0,
        isEvaluated: Boolean(state.isEvaluated),
      };
      localStorage.setItem('kalmiprep_calc_memento', JSON.stringify(memento));
    } catch (e) {}
  }

  function safeEvalScientific(expr, angleMode = 'DEG', lastAns = 0) {
    const engine = getCalcEngine();
    if (engine) {
      const res = engine.evaluate(expr, angleMode, lastAns);
      return res.success ? res.result : (res.error || 'Error');
    }
    return '0';
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
    // 3. SCIENTIFIC CALCULATOR SLICE (Delegated to GoF KalmiCalc)
    // ----------------------------------------------------
    calc: {
      isOpen: false,
      angleMode: 'DEG',
      expression: '',
      result: '0',
      lastAns: '0',
      memory: 0,
      isEvaluated: false,
      ...loadCalcMemento(),
      isOpen: false // strictly enforce initial closed state on page load
    },

    toggleCalc: () => {
      if (typeof window !== 'undefined' && window.KalmiCalc) { window.KalmiCalc.toggle(); return; }
      if (!document.getElementById('scientific-calculator-modal')) return;
      set((state) => ({ calc: { ...state.calc, isOpen: !state.calc.isOpen } }));
      get().renderCalcDOM();
    },

    openCalc: () => {
      if (typeof window !== 'undefined' && window.KalmiCalc) { window.KalmiCalc.open(); return; }
      if (!document.getElementById('scientific-calculator-modal')) return;
      set((state) => ({ calc: { ...state.calc, isOpen: true } }));
      get().renderCalcDOM();
    },

    closeCalc: () => {
      if (typeof window !== 'undefined' && window.KalmiCalc) { window.KalmiCalc.close(); return; }
      if (!document.getElementById('scientific-calculator-modal')) return;
      set((state) => ({ calc: { ...state.calc, isOpen: false } }));
      get().renderCalcDOM();
    },

    setCalcAngleMode: (mode) => {
      if (typeof window !== 'undefined' && window.KalmiCalc) { window.KalmiCalc.setAngleMode(mode); return; }
      set((state) => ({ calc: { ...state.calc, angleMode: mode } }));
      get().evaluateCalc(false);
      get().renderCalcDOM();
    },

    clearCalc: () => {
      if (typeof window !== 'undefined' && window.KalmiCalc) { window.KalmiCalc.clear(); return; }
      set((state) => ({
        calc: {
          ...state.calc,
          expression: '',
          result: '0',
          isEvaluated: false
        }
      }));
      get().renderCalcDOM();
    },

    backspaceCalc: () => {
      if (typeof window !== 'undefined' && window.KalmiCalc) { window.KalmiCalc.backspace(); return; }
      set((state) => {
        let expr = state.calc.expression;
        if (!expr || state.calc.isEvaluated) {
          return { calc: { ...state.calc, expression: '', result: '0', isEvaluated: false } };
        }
        const fnMatch = expr.match(/(sin|cos|tan|asin|acos|atan|sinh|cosh|tanh|ln|log|sqrt|cbrt)\($/);
        expr = fnMatch ? expr.slice(0, -fnMatch[0].length) : expr.slice(0, -1);
        return { calc: { ...state.calc, expression: expr } };
      });
      get().evaluateCalc(false);
      get().renderCalcDOM();
    },

    appendCalc: (token) => {
      if (typeof window !== 'undefined' && window.KalmiCalc) { window.KalmiCalc.append(token); return; }
      set((state) => {
        let { expression, isEvaluated, lastAns } = state.calc;
        const isOperator = ['+', '-', '−', '*', '/', '×', '÷', '^', '%'].includes(token);

        if (isEvaluated) {
          if (isOperator) {
            expression = (lastAns && lastAns !== 'Error' && lastAns !== 'Math ERROR' ? lastAns : '0') + token;
          } else {
            expression = token;
          }
          isEvaluated = false;
        } else {
          expression = expression + token;
        }

        return {
          calc: {
            ...state.calc,
            expression,
            isEvaluated
          }
        };
      });
      get().evaluateCalc(false);
      get().renderCalcDOM();
    },

    evaluateCalc: (isFinal = true) => {
      if (typeof window !== 'undefined' && window.KalmiCalc) { window.KalmiCalc.evaluate(isFinal); return; }
      const { expression, angleMode, lastAns } = get().calc;
      if (!expression || !expression.trim()) {
        if (isFinal) {
          set((state) => ({ calc: { ...state.calc, result: '0', isEvaluated: false } }));
          get().renderCalcDOM();
        }
        return;
      }

      const res = safeEvalScientific(expression, angleMode, lastAns);
      if (isFinal) {
        const isErr = res === 'Error' || res === 'Math ERROR' || res === 'Syntax ERROR';
        set((state) => ({
          calc: {
            ...state.calc,
            result: res,
            lastAns: isErr ? state.calc.lastAns : res,
            isEvaluated: true
          }
        }));
      } else {
        if (res !== 'Error' && res !== 'Math ERROR' && res !== 'Syntax ERROR') {
          set((state) => ({
            calc: {
              ...state.calc,
              result: res
            }
          }));
        }
      }
      get().renderCalcDOM();
    },

    memoryAdd: () => {
      if (typeof window !== 'undefined' && window.KalmiCalc) { window.KalmiCalc.memoryAdd(); return; }
      const current = parseFloat(get().calc.result) || 0;
      set((state) => ({ calc: { ...state.calc, memory: state.calc.memory + current } }));
      get().renderCalcDOM();
    },

    memorySubtract: () => {
      if (typeof window !== 'undefined' && window.KalmiCalc) { window.KalmiCalc.memorySubtract(); return; }
      const current = parseFloat(get().calc.result) || 0;
      set((state) => ({ calc: { ...state.calc, memory: state.calc.memory - current } }));
      get().renderCalcDOM();
    },

    memoryRecall: () => {
      if (typeof window !== 'undefined' && window.KalmiCalc) { window.KalmiCalc.memoryRecall(); return; }
      get().appendCalc(get().calc.memory.toString());
    },

    memoryClear: () => {
      if (typeof window !== 'undefined' && window.KalmiCalc) { window.KalmiCalc.memoryClear(); return; }
      set((state) => ({ calc: { ...state.calc, memory: 0 } }));
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
      if (typeof window !== 'undefined' && window.KalmiCalc) {
        window.KalmiCalc.render();
        return;
      }
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
      widget.classList.toggle('hidden', !isOpen);
      widget.setAttribute('aria-hidden', isOpen ? 'false' : 'true');

      const exprEl = document.getElementById('calc-expression-display');
      const resultEl = document.getElementById('calc-result-display');
      const angleBtn = document.getElementById('calc-angle-mode-btn');
      const memIndicator = document.getElementById('calc-memory-indicator');
      const ansIndicator = document.getElementById('calc-ans-indicator');

      // Display text
      if (exprEl) exprEl.textContent = expression || '0';
      if (resultEl) resultEl.textContent = result || '0';
      if (angleBtn) angleBtn.textContent = angleMode;

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

  // Calculator keyboard shortcuts and direct calculator numeric typing (fallback if KalmiCalc controller not present)
  if (!window.__kalmiCalcShortcutsBound && !window.KalmiCalc) {
    window.__kalmiCalcShortcutsBound = true;
    document.addEventListener('keydown', (e) => {
      const widget = document.getElementById('scientific-calculator-modal');
      if (!widget) return;

      // If typing in normal inputs or textareas, skip
      if (['INPUT', 'TEXTAREA', 'SELECT'].includes(e.target.tagName) || e.target.isContentEditable) {
        return;
      }

      const isAltC = e.altKey && (e.key === 'c' || e.key === 'C');
      if (isAltC) {
        e.preventDefault();
        window.useKalmiStore.getState().toggleCalc();
        return;
      }

      const calcState = window.useKalmiStore.getState().calc;
      if (calcState && calcState.isOpen) {
        if (e.key === 'Escape') {
          e.preventDefault();
          window.useKalmiStore.getState().closeCalc();
        } else if (e.key >= '0' && e.key <= '9') {
          e.preventDefault();
          window.useKalmiStore.getState().appendCalc(e.key);
        } else if (e.key === '.') {
          e.preventDefault();
          window.useKalmiStore.getState().appendCalc('.');
        } else if (e.key === '+') {
          e.preventDefault();
          window.useKalmiStore.getState().appendCalc('+');
        } else if (e.key === '-' || e.key === '−') {
          e.preventDefault();
          window.useKalmiStore.getState().appendCalc('−');
        } else if (e.key === '*' || e.key === 'x' || e.key === 'X') {
          e.preventDefault();
          window.useKalmiStore.getState().appendCalc('×');
        } else if (e.key === '/') {
          e.preventDefault();
          window.useKalmiStore.getState().appendCalc('÷');
        } else if (e.key === '(' || e.key === ')') {
          e.preventDefault();
          window.useKalmiStore.getState().appendCalc(e.key);
        } else if (e.key === '^') {
          e.preventDefault();
          window.useKalmiStore.getState().appendCalc('^(');
        } else if (e.key === '%') {
          e.preventDefault();
          window.useKalmiStore.getState().appendCalc('%');
        } else if (e.key === 'Enter' || e.key === '=') {
          e.preventDefault();
          window.useKalmiStore.getState().evaluateCalc(true);
        } else if (e.key === 'Backspace') {
          e.preventDefault();
          window.useKalmiStore.getState().backspaceCalc();
        } else if (e.key === 'Delete') {
          e.preventDefault();
          window.useKalmiStore.getState().clearCalc();
        }
      }
    });
  }

  // Ensure the modal is closed (and hidden) whenever a page is initialised or swapped in.
  function bootstrapCalculator() {
    if (window.useKalmiStore) {
      useKalmiStore.setState((state) => ({ calc: { ...state.calc, isOpen: false } }));
      useKalmiStore.getState().renderCalcDOM();
    }
  }

  bootstrapCalculator();
  if (!window.__kalmiCalcBootstrapBound) {
    window.__kalmiCalcBootstrapBound = true;
    document.addEventListener('DOMContentLoaded', bootstrapCalculator);
  }

})();
