/**
 * KalmiPrep Scientific Calculator - State Memento
 * 
 * GoF Memento Pattern implementation for state persistence across page refreshes.
 * Strictly enforces that initial state is closed (isOpen: false) upon recovery
 * so students are never interrupted during exam transitions.
 */

(function (global) {
  'use strict';

  const CALC_MEMENTO_KEY = 'kalmiprep_calc_memento';

  const KalmiCalcMemento = {
    load() {
      try {
        if (typeof global !== 'undefined' && global.localStorage) {
          const raw = global.localStorage.getItem(CALC_MEMENTO_KEY);
          if (raw) {
            const data = JSON.parse(raw);
            return {
              isOpen: false, // strictly enforce closed on page load/navigation
              angleMode: data.angleMode || 'DEG',
              expression: data.expression || '',
              result: data.result || '0',
              lastAns: data.lastAns || '0',
              memory: typeof data.memory === 'number' ? data.memory : 0,
              isEvaluated: Boolean(data.isEvaluated),
            };
          }
        }
      } catch (e) {
        // Private browsing or storage quota exceeded
      }
      return null;
    },

    save(state) {
      try {
        if (typeof global !== 'undefined' && global.localStorage && state) {
          const snapshot = {
            isOpen: false, // Never auto-pop open across page refreshes
            angleMode: state.angleMode || 'DEG',
            expression: state.expression || '',
            result: state.result || '0',
            lastAns: state.lastAns || '0',
            memory: typeof state.memory === 'number' ? state.memory : 0,
            isEvaluated: Boolean(state.isEvaluated),
          };
          global.localStorage.setItem(CALC_MEMENTO_KEY, JSON.stringify(snapshot));
        }
      } catch (e) {
        // Storage unavailable
      }
    },

    clear() {
      try {
        if (typeof global !== 'undefined' && global.localStorage) {
          global.localStorage.removeItem(CALC_MEMENTO_KEY);
        }
      } catch (e) {}
    }
  };

  // Export for browser and Node.js
  if (typeof module !== 'undefined' && module.exports) {
    module.exports = { KalmiCalcMemento };
  }
  global.KalmiCalcMemento = KalmiCalcMemento;

})(typeof window !== 'undefined' ? window : globalThis);
