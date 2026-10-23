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
    // 3. CALCULATOR MODAL LIFECYCLE SLICE
    // Only visibility lives here. All calculator state (expression, answer,
    // memory, angle mode, history) is owned by KalmiCalcUI / KalmiCalcEngine
    // (static/js/calculator/), so there is a single source of truth.
    // ----------------------------------------------------
    calc: {
      isOpen: false, // always closed on initialisation / navigation
    },

    toggleCalc: () => {
      if (!document.getElementById('scientific-calculator-modal')) return;
      set((state) => ({ calc: { ...state.calc, isOpen: !state.calc.isOpen } }));
      get().renderCalcDOM();
    },

    openCalc: () => {
      if (!document.getElementById('scientific-calculator-modal')) return;
      set((state) => ({ calc: { ...state.calc, isOpen: true } }));
      get().renderCalcDOM();
    },

    closeCalc: () => {
      set((state) => ({ calc: { ...state.calc, isOpen: false } }));
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

      const { isOpen } = get().calc;
      widget.classList.toggle('hidden', !isOpen);
      widget.setAttribute('aria-hidden', isOpen ? 'false' : 'true');

      if (isOpen && window.KalmiCalcUI) {
        window.KalmiCalcUI.onCalcModalOpened();
      }
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

  // Calculator keyboard shortcuts. Registered once (guarded) and inert on pages
  // that do not render the calculator modal. Typing inside the calculator is
  // handled by the MathLive field itself (see calculator/ui.js).
  if (!window.__kalmiCalcShortcutsBound) {
    window.__kalmiCalcShortcutsBound = true;
    document.addEventListener('keydown', (e) => {
      if (!document.getElementById('scientific-calculator-modal')) return;

      const isAltC = e.altKey && (e.key === 'c' || e.key === 'C');
      if (isAltC) {
        e.preventDefault();
        window.useKalmiStore.getState().toggleCalc();
        return;
      }

      if (e.key === 'Escape' && window.useKalmiStore.getState().calc.isOpen) {
        e.preventDefault();
        window.useKalmiStore.getState().closeCalc();
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
